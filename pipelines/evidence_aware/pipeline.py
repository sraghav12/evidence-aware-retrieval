"""Explicit legacy adapter; provider-free core does not import this module."""
from dataclasses import asdict,replace
import json
from pipelines.base import BasePipeline,PipelineResult
from .calendar import build_fiscal_calendar
from .parser import parse_query,UnsupportedQuery
from .retrieval import BM25Backend
from .engine import run_spec


class EvidenceAwarePipeline(BasePipeline):
    name='evidence_aware_v2'
    model='decimal_executor'

    def __init__(self,as_of,documents=None,backends=None,config=None,answerer=None):
        self.as_of=as_of;self.documents=documents or {};self.backends=backends;self.config=config or {};self.answerer=answerer

    def load_corpus(self,corpus_path):
        with open(corpus_path) as f:self.documents={d['doc_id']:d for d in map(json.loads,f) if d}

    def run_spec(self,spec):
        bs=self.backends or {s:BM25Backend(self.documents,s) for s in ('cheap_search','section_search','expanded_search')}
        return run_spec(spec,bs,self.documents,self.config,self.answerer)

    def query(self,question):
        aliases={d['entity_id'].split(':')[-1].casefold():d['entity_id'] for d in self.documents.values()}
        try:
            q=parse_query(question,self.as_of,aliases,build_fiscal_calendar(self.documents,self.as_of));trace=self.run_spec(q)
            return PipelineResult(json.dumps(asdict(trace.answer),sort_keys=True),trace=asdict(trace))
        except UnsupportedQuery as e:
            return PipelineResult(json.dumps({'status':'abstained','reason':str(e)}),trace={'answer':{'status':'abstained','reason':str(e)}})
