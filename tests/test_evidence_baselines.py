from dataclasses import replace
import pytest
from evidence_helpers import documents,spec
from pipelines.evidence_aware.contracts import BudgetState,CoverageResult,RoutingState
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.policy import decide,POLICIES
from pipelines.evidence_aware.retrieval import BM25Backend,HybridBackend,RerankBackend,UnavailableBackend,ArmUnavailable,rrf_scores

STAGES=('cheap_search','section_search','expanded_search')
RANK='Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.'


def backends(d):return {s:BM25Backend(d,s) for s in STAGES}


def actions(question,policy,config=None):
    d=documents();t=run_spec(spec(question),backends(d),d,dict(config or {},policy=policy))
    return [x['action'] for x in t.decisions],t.answer


def test_rrf_rank_one_exact_score():
    s=rrf_scores([['a','b'],['a','c']])
    assert s['a']==2/61 and s['b']==1/62 and s['c']==1/62


def test_always_maximum_attempts_all_three_stages():
    acts,answer=actions('What was Alpha FY2024 revenue?','always_maximum_v1')
    assert acts==[*STAGES,'answer'] and answer.value=='120'


def test_always_cheap_never_escalates():
    acts,answer=actions(RANK,'always_cheap_v1',{'cheap_context_tokens':64})
    assert acts==['cheap_search','abstain'] and answer.reason=='incomplete_evidence'


def test_complexity_control_uses_only_operand_count():
    assert actions('What was Mention FY2024 revenue?','complexity_rule_v1')[0]==['cheap_search','abstain']
    acts,answer=actions(RANK,'complexity_rule_v1',{'cheap_context_tokens':64})
    assert acts==[*STAGES,'answer'] and answer.status=='answered'
    q=spec(RANK);budget=BudgetState();state=RoutingState(1,('cheap_search',))
    complete=CoverageResult(True,tuple(r.id for r in q.requirements),(),(),());incomplete=CoverageResult(False,(),tuple(r.id for r in q.requirements),(),())
    assert decide('complexity_rule_v1',q,complete,budget,state).action==decide('complexity_rule_v1',q,incomplete,budget,state).action=='section_search'


def test_runner_rejects_unknown_policy(tmp_path):
    from evaluation.evidence_aware.runner import run
    with pytest.raises(ValueError,match='unknown policy'):run({'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','output':str(tmp_path/'r'),'policy':'oracle_v1'})


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):decide('oracle_v1',spec(),CoverageResult(True,(),(),(),()),BudgetState(),RoutingState())
    assert POLICIES=={'coverage_rule_v1','always_cheap_v1','always_maximum_v1','complexity_rule_v1'}


@pytest.mark.parametrize('policy',sorted(['coverage_rule_v1','always_cheap_v1','always_maximum_v1','complexity_rule_v1']))
def test_every_arm_has_identical_postpack_gate_and_audit(policy):
    assert actions('What was Conflict FY2024 revenue?',policy)[1].reason=='conflicting_evidence'
    assert actions('What was Wrong FY2024 revenue?',policy)[1].status=='abstained'
    assert actions('What was Alpha FY2024 revenue?',policy)[1].value=='120'


class ReverseRanker:
    """Test-only deterministic ranker; not a model."""
    revision='test-reverse'
    def rank(self,question,units):return [u.id for u in sorted(units,key=lambda u:u.id,reverse=True)]


def test_hybrid_and_rerank_share_bm25_units():
    d=documents();base=BM25Backend(d);hybrid=HybridBackend(base,ReverseRanker());rerank=RerankBackend(hybrid,ReverseRanker(),pool=4)
    assert hybrid.units is base.units and rerank.units is base.units
    for b in (hybrid,rerank):
        out=b.retrieve(spec(),[],8192)
        assert any(s.value=='120' for s in out) and {u.id for u in b.selected}<= {u.id for u in base.units}


def test_missing_backend_is_unavailable_not_bm25():
    b=UnavailableBackend('dense','no pinned local embedding model')
    with pytest.raises(ArmUnavailable):b.retrieve(spec(),[],8192)
    d=documents();t=run_spec(spec(),{s:b for s in STAGES},d,{})
    assert t.answer.status=='error' and t.answer.reason=='ArmUnavailable' and not t.evidence
