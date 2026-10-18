from dataclasses import replace
from copy import deepcopy
import pytest
from evidence_helpers import documents,spec,spans
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.retrieval import BM25Backend


def test_mention_is_not_evidence():
    d=documents();q=spec('What was Mention FY2024 revenue?');assert not audit_coverage(q,spans(),d).complete


def test_wrong_table_column_fails():
    d=documents();s=next(s for s in spans() if s.doc_id.startswith('wrong'))
    assert not audit_coverage(spec('What was Wrong FY2024 revenue?'),[replace(s,period_start='2024-01-01',period_end='2024-12-31',fiscal_year=2024)],d).complete


def test_tampered_quote_fails():
    d=documents();s=next(s for s in spans() if s.entity_id=='synthetic:alpha')
    assert not audit_coverage(spec(),[replace(s,quote='Revenue: 999')],d).complete


def test_headers_survive_packing():
    d=documents();b=BM25Backend(d);out=b.retrieve(spec(),[],8192)
    assert out and all(s.table_headers and 'unit' in s.table_headers for s in out)


def test_period_is_not_filing_year():
    assert not audit_coverage(spec('What was Wrong FY2024 revenue?'),spans(),documents()).complete


def test_retrieval_uses_source_units_without_references():
    b=BM25Backend(documents());s=b.retrieve(spec(),[],8192)
    assert any(x.value=='120' for x in s)
    assert all(x.doc_id in documents() for x in s)


def test_conflicting_values_fail_closed():
    c=audit_coverage(spec('What was Conflict FY2024 revenue?'),spans(),documents())
    assert c.conflicts and not c.complete


def test_duplicate_equal_values_are_not_conflicts():
    s=[s for s in spans() if s.entity_id=='synthetic:alpha'];c=audit_coverage(spec(),s+s,documents())
    assert c.complete and not c.conflicts
