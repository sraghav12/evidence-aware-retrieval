import pytest
from evidence_helpers import documents,spec,aliases
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query,UnsupportedQuery


def test_unsupported_query_abstains():
    with pytest.raises(UnsupportedQuery):spec('Should I invest in Alpha?')


def test_fiscal_calendar_uses_only_cutoff_eligible_sources():
    assert ('synthetic:late',2024) not in build_fiscal_calendar(documents(),'2025-03-01')


def test_unknown_calendar_abstains():
    with pytest.raises(UnsupportedQuery,match='unknown_fiscal_calendar'):spec('What was Late FY2024 revenue?')


def test_growth_has_four_operands_for_two_companies():
    q=spec('Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.')
    assert len(q.requirements)==4 and q.operation.kind=='ranking'


def test_non_calendar_fiscal_dates_come_from_public_source():
    d=documents();d['alpha_income']['fiscal_calendar']=[dict(fiscal_year=2024,period_start='2023-10-01',period_end='2024-09-28')]
    q=parse_query('What was Alpha FY2024 revenue?','2025-03-01',aliases(d),build_fiscal_calendar(d,'2025-03-01'))
    assert q.requirements[0].period_end=='2024-09-28'
