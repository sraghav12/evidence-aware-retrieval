from evidence_helpers import ROOT
from pipelines.base import PipelineResult
from pipelines.evidence_aware.pipeline import EvidenceAwarePipeline


def test_adapter_returns_pipeline_result():
    p=EvidenceAwarePipeline(as_of='2025-03-01');p.load_corpus(str(ROOT/'documents.jsonl'))
    result=p.query('What was Alpha FY2024 revenue?')
    assert isinstance(result,PipelineResult) and '120' in result.answer and result.trace['answer']['status']=='answered'
