from dataclasses import asdict
import pytest
from pipelines.evidence_aware.contracts import load_query, load_question, load_span, manifest_hash


def requirement():
    return dict(id='a24',entity_id='synthetic:alpha',metric='revenue',period_start='2024-01-01',period_end='2024-12-31',fiscal_year=2024,unit='USD_million',accounting_basis='reported')


def query():
    return dict(id='q',question='What was Alpha FY2024 revenue?',as_of='2025-03-01',requirements=[requirement()],operation={'kind':'extract','operands':['a24']})


def span():
    return dict(id='s',doc_id='d',accession='synthetic',doc_sha256='a'*64,entity_id='synthetic:alpha',disclosed_at='2025-02-01',start=0,end=3,quote='120',metric='revenue',period_start='2024-01-01',period_end='2024-12-31',fiscal_year=2024,unit='USD_million',value='120.00',accounting_basis='reported',table_headers=['Revenue','2024','USD million'],source_url='fixture://alpha')


def test_rejects_gold_fields():
    with pytest.raises(ValueError): load_query(query() | {'gold_answer':'120'})


def test_rejects_nested_unknown_fields():
    q=query(); q['requirements'][0]['oracle_action']='answer'
    with pytest.raises(ValueError): load_query(q)


def test_decimal_roundtrip():
    assert asdict(load_span(span()))['value']=='120.00'


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity',120,True])
def test_nonfinite_decimal_rejected(value):
    with pytest.raises(ValueError): load_span(span() | {'value':value})


def test_stable_manifest(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';a.write_text('alpha');b.write_text('beta')
    h=manifest_hash([a,b]);assert h==manifest_hash([b,a]);b.write_text('Beta');assert h!=manifest_hash([a,b])


def test_duplicate_requirement_ids_rejected():
    q=query();q['requirements']*=2
    with pytest.raises(ValueError):load_query(q)


def test_raw_question_rejects_requirements():
    with pytest.raises(ValueError):load_question(query())
    assert load_question({'id':'q','question':'What?','as_of':'2025-03-01'}).id=='q'


@pytest.mark.parametrize('change',[{'as_of':'2025-02-30'},{'operation':{'kind':'eval','operands':['a24']}},{'operation':{'kind':'extract','operands':['missing']}}])
def test_bad_dates_operations_and_references_rejected(change):
    with pytest.raises(ValueError):load_query(query() | change)
