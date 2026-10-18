from dataclasses import replace
import json,subprocess,sys
from pathlib import Path
import pytest
from pipelines.evidence_aware.contracts import load_query
from evaluation.evidence_aware.dataset import build_split_manifest,validate_manifest,eligible


def q(id,entities):
    req=[dict(id=f'{id}_{e}',entity_id=e,metric='revenue',period_start='2024-01-01',period_end='2024-12-31',fiscal_year=2024,unit='USD_million',accounting_basis='reported') for e in entities]
    return load_query(dict(id=id,question='fixture',as_of='2025-03-01',requirements=req,operation={'kind':'sum','operands':[r['id'] for r in req]}))


def test_cross_company_bridge_stays_together():
    m=build_split_manifest([q('a',['alpha','beta']),q('b',['beta','gamma']),q('c',['delta'])],[],11)
    rows={r['query_id']:r for r in m['rows']}
    assert rows['a']['component']==rows['b']['component'];validate_manifest(m)
    rows['b']['split']='test' if rows['a']['split']!='test' else 'train'
    with pytest.raises(ValueError):validate_manifest(m)


@pytest.mark.parametrize('key',['source_ancestry','derivation_ancestry'])
def test_derived_template_and_source_overlap_rejected(key):
    m=build_split_manifest([q('a',['alpha']),q('b',['beta'])],[],11,lineage={'a':{key:['shared']},'b':{key:['shared']}})
    m['rows'][0]['split']='train';m['rows'][1]['split']='test'
    with pytest.raises(ValueError):validate_manifest(m)


def test_v1_descendants_development_only():
    m=build_split_manifest([q('a',['alpha'])],[],11,lineage={'a':{'v1_descendant':True}})
    assert m['rows'][0]['split']=='development';m['rows'][0]['split']='test'
    with pytest.raises(ValueError):validate_manifest(m)


def test_future_disclosure_ineligible():
    assert not eligible('2025-03-02','2025-03-01');assert eligible('2025-03-01','2025-03-01')


def test_fixture_quote_slices_match():
    root=Path('tests/fixtures/evidence_v2')
    docs={d['doc_id']:d for d in map(json.loads,(root/'documents.jsonl').read_text().splitlines())}
    refs=list(map(json.loads,(root/'references.jsonl').read_text().splitlines()))
    assert len(refs)==8
    for r in refs:
        for e in r['evidence']:
            assert docs[e['doc_id']]['text'][e['start']:e['end']]==e['quote']


def test_v2_import_does_not_import_legacy_evaluator():
    subprocess.run([sys.executable,'-c',"import evaluation.evidence_aware.dataset; import sys; assert 'evaluation.metrics' not in sys.modules"],check=True)


def test_legacy_exports_still_resolve():
    from evaluation import compute_match_metrics,run_pipeline
    assert callable(compute_match_metrics) and callable(run_pipeline)
