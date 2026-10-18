"""Finite retrieval state machine: resource counts never stand in for history."""
from .contracts import RouteDecision


def decide_route(spec,coverage,budget,state):
    if coverage.conflicts:return RouteDecision('abstain',('conflicting_evidence',),coverage.missing_requirement_ids)
    if coverage.complete:return RouteDecision('answer',('complete_evidence',))
    if budget.deadline_ms<=0 or budget.retrieval_tokens_remaining<=0 or budget.verification_tokens_remaining<=0:
        return RouteDecision('abstain',('budget_exhausted',),coverage.missing_requirement_ids)
    for action in ('section_search','expanded_search'):
        if action not in state.attempted_actions:return RouteDecision(action,('missing_operands',),coverage.missing_requirement_ids)
    return RouteDecision('abstain',('incomplete_evidence',),coverage.missing_requirement_ids)
