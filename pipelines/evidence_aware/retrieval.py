"""Local BM25 over source units; extraction happens only after selection."""
from collections import Counter
from math import log
import re
from typing import Protocol
from .units import build_units
from .extraction import extract_candidates


def tokens(text):return re.findall(r'\w+',text.casefold())


class RetrievalBackend(Protocol):
    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):...


class UnitRanker(Protocol):
    """Injected dense model or cross-encoder: returns unit IDs best first. Must expose a pinned `revision`."""
    revision:str
    def rank(self,question,units):...


class ArmUnavailable(RuntimeError):pass


def rrf_scores(rankings,k=60):
    """Reciprocal rank fusion, sum(1/(k+rank)) with ranks starting at 1."""
    scores={}
    for ranking in rankings:
        for rank,item in enumerate(ranking,1):scores[item]=scores.get(item,0)+1/(k+rank)
    return scores


class BM25Backend:
    def __init__(self,documents,stage='cheap_search',candidate_pool=20,max_units=12):
        self.documents=documents;self.stage=stage;self.candidate_pool=candidate_pool;self.max_units=max_units
        self.units=build_units(documents)
        self.counts={u.id:Counter(tokens(u.text)) for u in self.units}
        self.lengths={u.id:sum(self.counts[u.id].values()) for u in self.units}
        self.avg=sum(self.lengths.values())/max(1,len(self.units))
        self.df=Counter(t for c in self.counts.values() for t in c)
        self.selected=[];self.inspected_tokens=0

    def eligible(self,spec,missing_ids,exclude_unit_ids=()):
        requirements=[r for r in spec.requirements if not missing_ids or r.id in missing_ids]
        entities={r.entity_id for r in requirements}
        # Index statistics are corpus-wide; only cutoff-eligible, not-yet-inspected units are candidates.
        units=[u for u in self.units if self.documents[u.doc_id]['entity_id'] in entities and self.documents[u.doc_id]['disclosed_at']<=spec.as_of and u.id not in exclude_unit_ids]
        if self.stage=='section_search':
            units=[u for u in units if any(x in u.text.splitlines()[0].casefold() for x in ('income','operations','financial','statement'))]
        return units,requirements

    def rank(self,spec,missing_ids,exclude_unit_ids=()):
        units,requirements=self.eligible(spec,missing_ids,exclude_unit_ids)
        terms=set(tokens(spec.question)) | {r.metric for r in requirements};n=len(self.units)
        def score(u):
            c=self.counts[u.id];length=self.lengths[u.id]
            return sum(log(1+(n-self.df[t]+.5)/(self.df[t]+.5))*c[t]*2.2/(c[t]+1.2*(.25+.75*length/max(self.avg,1))) for t in terms if c[t])
        return sorted(units,key=lambda u:(-score(u),u.id))

    def select(self,ranked,token_limit):
        self.selected=[];self.inspected_tokens=0
        for u in ranked[:self.candidate_pool]:
            count=len(u.text.split())
            if len(self.selected)>=self.max_units:break
            if self.inspected_tokens+count>token_limit:continue
            self.selected.append(u);self.inspected_tokens+=count
        return extract_candidates(self.selected,self.documents)

    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):
        return self.select(self.rank(spec,missing_ids,exclude_unit_ids),token_limit)


class HybridBackend:
    """RRF of BM25 and an injected dense ranking over the same eligible units, then the same selection rule."""
    def __init__(self,bm25,dense,k=60):self.bm25=bm25;self.dense=dense;self.k=k;self.units=bm25.units

    def rank(self,spec,missing_ids,exclude_unit_ids=()):
        lexical=self.bm25.rank(spec,missing_ids,exclude_unit_ids);by_id={u.id:u for u in lexical}
        dense=[i for i in self.dense.rank(spec.question,lexical) if i in by_id]
        scores=rrf_scores([[u.id for u in lexical],dense],self.k)
        return [by_id[i] for i in sorted(scores,key=lambda i:(-scores[i],i))]

    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):return self.bm25.select(self.rank(spec,missing_ids,exclude_unit_ids),token_limit)

    @property
    def selected(self):return self.bm25.selected

    @property
    def inspected_tokens(self):return self.bm25.inspected_tokens


class DenseBackend(HybridBackend):
    """Injected dense ranking alone, over the same cutoff/entity/section-eligible units as BM25."""
    def rank(self,spec,missing_ids,exclude_unit_ids=()):
        units,_=self.bm25.eligible(spec,missing_ids,exclude_unit_ids);by_id={u.id:u for u in units}
        return [by_id[i] for i in self.dense.rank(spec.question,units) if i in by_id]


class RerankBackend:
    """Injected cross-encoder reorders only the first `pool` candidates of a base ranking."""
    def __init__(self,base,reranker,pool=60):self.base=base;self.reranker=reranker;self.pool=pool;self.units=base.units
    def _bm25(self):return self.base.bm25 if isinstance(self.base,HybridBackend) else self.base

    def rank(self,spec,missing_ids,exclude_unit_ids=()):
        ranked=self.base.rank(spec,missing_ids,exclude_unit_ids);head=ranked[:self.pool];by_id={u.id:u for u in head}
        order=[by_id[i] for i in self.reranker.rank(spec.question,head) if i in by_id]
        return order+[u for u in head if u not in order]+ranked[self.pool:]

    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):return self._bm25().select(self.rank(spec,missing_ids,exclude_unit_ids),token_limit)

    @property
    def selected(self):return self._bm25().selected

    @property
    def inspected_tokens(self):return self._bm25().inspected_tokens


class UnavailableBackend:
    """An arm whose model is not installed. It never falls back to another backend."""
    def __init__(self,arm,reason):self.arm=arm;self.reason=reason;self.selected=[];self.inspected_tokens=0
    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):raise ArmUnavailable(f'{self.arm}: {self.reason}')
