"""Finite retrieval state machine: resource counts never stand in for history."""
from .contracts import RouteDecision

STAGES=('cheap_search','section_search','expanded_search')
POLICIES={'coverage_rule_v1','always_cheap_v1','always_maximum_v1','complexity_rule_v1'}
# Author-selected and frozen before evaluation: <=2 operands is cheap-only, more runs every bounded stage.
COMPLEXITY_CHEAP_MAX_OPERANDS=2


def exhausted(budget):return budget.deadline_ms<=0 or budget.retrieval_tokens_remaining<=0 or budget.verification_tokens_remaining<=0


def decide_route(spec,coverage,budget,state):
    if coverage.conflicts:return RouteDecision('abstain',('conflicting_evidence',),coverage.missing_requirement_ids)
    if coverage.complete:return RouteDecision('answer',('complete_evidence',))
    if exhausted(budget):return RouteDecision('abstain',('budget_exhausted',),coverage.missing_requirement_ids)
    for action in ('section_search','expanded_search'):
        if action not in state.attempted_actions:return RouteDecision(action,('missing_operands',),coverage.missing_requirement_ids)
    return RouteDecision('abstain',('incomplete_evidence',),coverage.missing_requirement_ids)


def gate(coverage,reason):
    """The shared post-packing gate every scheduling arm ends with."""
    if coverage.conflicts:return RouteDecision('abstain',('conflicting_evidence',),coverage.missing_requirement_ids)
    if coverage.complete:return RouteDecision('answer',('complete_evidence',))
    return RouteDecision('abstain',(reason,),coverage.missing_requirement_ids)


def decide(policy,spec,coverage,budget,state):
    if policy not in POLICIES:raise ValueError(f'unknown policy: {policy}')
    if policy=='coverage_rule_v1':return decide_route(spec,coverage,budget,state)
    if policy=='complexity_rule_v1':
        policy='always_cheap_v1' if len(spec.operation.operands)<=COMPLEXITY_CHEAP_MAX_OPERANDS else 'always_maximum_v1'
    if policy=='always_cheap_v1':return gate(coverage,'incomplete_evidence')
    remaining=[a for a in STAGES if a not in state.attempted_actions]
    if remaining and not exhausted(budget):return RouteDecision(remaining[0],('scheduled_stage',),coverage.missing_requirement_ids)
    return gate(coverage,'budget_exhausted' if remaining else 'incomplete_evidence')
