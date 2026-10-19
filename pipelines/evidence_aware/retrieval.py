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


class BM25Backend:
    def __init__(self,documents,stage='cheap_search',candidate_pool=20,max_units=12):
        self.documents=documents;self.stage=stage;self.candidate_pool=candidate_pool;self.max_units=max_units
        self.units=build_units(documents)
        self.counts={u.id:Counter(tokens(u.text)) for u in self.units}
        self.lengths={u.id:sum(self.counts[u.id].values()) for u in self.units}
        self.avg=sum(self.lengths.values())/max(1,len(self.units))
        self.df=Counter(t for c in self.counts.values() for t in c)
        self.selected=[];self.inspected_tokens=0

    def retrieve(self,spec,missing_ids,token_limit,exclude_unit_ids=()):
        requirements=[r for r in spec.requirements if not missing_ids or r.id in missing_ids]
        entities={r.entity_id for r in requirements}
        terms=set(tokens(spec.question)) | {r.metric for r in requirements}
        # Index statistics are corpus-wide; only cutoff-eligible, not-yet-inspected units are candidates.
        eligible=[u for u in self.units if self.documents[u.doc_id]['entity_id'] in entities and self.documents[u.doc_id]['disclosed_at']<=spec.as_of and u.id not in exclude_unit_ids]
        if self.stage=='section_search':
            eligible=[u for u in eligible if any(x in u.text.splitlines()[0].casefold() for x in ('income','operations','financial','statement'))]
        def score(u):
            c=self.counts[u.id];length=self.lengths[u.id];n=len(self.units)
            return sum(log(1+(n-self.df[t]+.5)/(self.df[t]+.5))*c[t]*2.2/(c[t]+1.2*(.25+.75*length/max(self.avg,1))) for t in terms if c[t])
        ranked=sorted(eligible,key=lambda u:(-score(u),u.id))[:self.candidate_pool]
        self.selected=[];self.inspected_tokens=0
        for u in ranked:
            count=len(u.text.split())
            if len(self.selected)>=self.max_units:break
            if self.inspected_tokens+count>token_limit:continue
            self.selected.append(u);self.inspected_tokens+=count
        return extract_candidates(self.selected,self.documents)
