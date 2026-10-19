import json
from dataclasses import replace
from pathlib import Path
import pytest
from pipelines.evidence_aware.contracts import BudgetState,UsageEvent
from evaluation.evidence_aware.ledger import reserve_call,BudgetExceeded,cache_key
from evaluation.evidence_aware.runner import run


def config(tmp_path):
    return {'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','output':str(tmp_path/'run'),'provider_enabled':False,'max_usd':0,'cheap_context_tokens':64}


def test_zero_budget_never_calls_provider():
    with pytest.raises(BudgetExceeded):reserve_call(UsageEvent('e','q','generation',provider='remote',estimated_usd=.01),BudgetState())


def test_retry_attempts_are_charged():
    b=BudgetState(max_usd=1,calls_remaining=3)
    reserve_call(UsageEvent('a','q','generation',provider='remote',attempts=2,estimated_usd=.4),b)
    assert b.calls_remaining==1 and b.estimated_usd_reserved==.4
    with pytest.raises(BudgetExceeded):reserve_call(UsageEvent('b','q','generation',provider='remote',estimated_usd=.7),b)


def test_unknown_price_is_null():
    e=UsageEvent('e','q','generation',provider='remote',estimated_usd=None,input_tokens=None)
    assert e.estimated_usd is None
    with pytest.raises(BudgetExceeded):reserve_call(e,BudgetState(max_usd=1))


def test_timeout_retains_query_row(tmp_path):
    c=config(tmp_path)|{'deadline_ms':0};out=run(c)
    rows=[json.loads(x) for x in (out/'traces.jsonl').read_text().splitlines()]
    assert len(rows)==8 and all(r['answer']['status']=='abstained' for r in rows)


def test_cache_key_changes_with_policy_or_corpus():
    x={'corpus_hash':'a','policy_hash':'b','query_hash':'c','parser_hash':'d','model_revision':'none','prompt_hash':'none','budget_hash':'e','seed':11}
    assert cache_key(x)!=cache_key(x|{'policy_hash':'other'})
    assert cache_key(x)!=cache_key(x|{'corpus_hash':'other'})


def test_replay_latency_is_not_provider_latency(tmp_path):
    out=run(config(tmp_path));rows=[json.loads(x) for x in (out/'traces.jsonl').read_text().splitlines()]
    assert all(r['timing_kind']=='fresh_local_executor' for r in rows)
    assert all(e['provider']=='local' for r in rows for e in r['usage'])


def test_existing_output_not_overwritten(tmp_path):
    c=config(tmp_path);run(c)
    with pytest.raises(FileExistsError):run(c)


def test_generation_attempt_has_usage_record():
    from evidence_helpers import documents,spec
    from pipelines.evidence_aware.engine import run_spec
    from pipelines.evidence_aware.retrieval import BM25Backend
    from pipelines.evidence_aware.contracts import AnswerRecord
    class FailingAnswerer:
        def answer(self,*a):raise TimeoutError('test timeout')
    docs=documents();bs={s:BM25Backend(docs,s) for s in ('cheap_search','section_search','expanded_search')}
    trace=run_spec(spec(),bs,docs,{'provider_enabled':True,'max_usd':1,'generation_reservation_usd':.1},FailingAnswerer())
    assert trace.answer.status=='error'
    event=next(e for e in trace.usage if e['stage']=='generation')
    assert event['status']=='TimeoutError' and event['billed_usd'] is None and event['input_tokens'] is None
