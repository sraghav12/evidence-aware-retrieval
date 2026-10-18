from dataclasses import asdict
from evidence_helpers import documents,spec
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.retrieval import BM25Backend
from pipelines.evidence_aware.contracts import AnswerRecord


def backends(d=None):
    d=documents() if d is None else d
    return {s:BM25Backend(d,s) for s in ['cheap_search','section_search','expanded_search']}


def run(q=None,config=None,bs=None,answerer=None):
    return run_spec(q or spec(),bs or backends(),documents(),config or {},answerer)


def test_complete_answers_after_cheap_only():
    t=run();assert t.answer.status=='answered' and [d['action'] for d in t.decisions]==['cheap_search','answer']


def test_missing_company_triggers_section_search():
    t=run(spec('Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.'),{'cheap_context_tokens':64})
    assert t.answer.status=='answered' and [d['action'] for d in t.decisions]==['cheap_search','section_search','answer']
    assert len(t.coverage_snapshots[0]['missing_requirement_ids'])==2


def test_empty_stages_advance_without_provider_calls():
    t=run(spec('What was Mention FY2024 revenue?'))
    assert [d['action'] for d in t.decisions]==['cheap_search','section_search','expanded_search','abstain']
    assert all(e['provider']=='local' for e in t.usage)


def test_expanded_search_runs_at_most_once():
    t=run(spec('What was Wrong FY2024 revenue?'))
    assert sum(d['action']=='expanded_search' for d in t.decisions)==1


def test_budget_exhaustion_abstains():assert run(config={'deadline_ms':0}).answer.status=='abstained'


def test_packing_loss_reaudits_coverage():
    t=run(config={'max_context_tokens':1})
    assert t.answer.status=='abstained' and not t.packed_ids


def test_cumulative_allowance_blocks_escalation():
    t=run(spec('Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.'),{'cheap_context_tokens':64,'retrieval_tokens_total':64})
    assert t.answer.status=='abstained' and len([d for d in t.decisions if d['action'].endswith('search')])<=3


def test_model_prompt_excludes_executor_result():
    class Answerer:
        def answer(self,q,ss):
            assert set(asdict(q))=={'id','question','as_of','requirements','operation'}
            # A wrong answer is rejected even with plausible source citations.
            return AnswerRecord('answered','999','USD_million',{q.requirements[0].id:[ss[0].id]})
    t=run(config={'provider_enabled':True,'max_usd':1,'generation_reservation_usd':.01},answerer=Answerer())
    assert t.answer.reason=='answer_audit_failed'
