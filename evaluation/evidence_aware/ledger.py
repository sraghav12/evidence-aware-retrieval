"""Reservations prevent accidental provider calls; unknown prices never become zero."""
import math
from pipelines.evidence_aware.contracts import digest


class BudgetExceeded(ValueError):pass


def reserve_call(event,budget):
    amount=event.estimated_usd
    if budget.max_usd<=0 or amount is None or not math.isfinite(amount) or amount<0 or type(event.attempts) is not int or event.attempts<1:
        raise BudgetExceeded('disabled or unpriced provider call')
    if budget.calls_remaining<event.attempts or budget.estimated_usd_reserved+amount>budget.max_usd:
        raise BudgetExceeded('provider reservation exceeds budget')
    budget.calls_remaining-=event.attempts;budget.estimated_usd_reserved+=amount


def cache_key(parts):
    required={'corpus_hash','policy_hash','query_hash','parser_hash','model_revision','prompt_hash','budget_hash','seed'}
    if not required<=set(parts):raise ValueError('incomplete cache identity')
    return digest(parts)
