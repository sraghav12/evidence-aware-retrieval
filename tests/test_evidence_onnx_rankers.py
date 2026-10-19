import json,shutil,subprocess,sys
from pathlib import Path
import pytest
from pipelines.evidence_aware.contracts import RetrievalUnit
from pipelines.evidence_aware.onnx_rankers import load_rankers,AssetMismatch,ASSETS

ROOT=Path(__file__).resolve().parents[1]
MODELS_PRESENT=all((ROOT/v['local_dir']/'onnx/model.onnx').is_file() for v in json.loads((ROOT/ASSETS).read_text()).values())
needs_models=pytest.mark.skipif(not MODELS_PRESENT,reason='pinned ONNX weights not downloaded (see docs/v2/resource_probe.md)')


def unit(i,text):return RetrievalUnit(i,'d',0,len(text),text,i)


UNITS=[unit('a','SECTION table 3 | Consolidated statements of operations\nrow | Total net sales | 391,035 | 383,285'),
       unit('b','SECTION table 9 | Employee stock plans\nrow | Restricted stock units granted | 1,200'),
       unit('c','SECTION table 12 | Lease liabilities maturity schedule\nrow | 2026 | 1,950')]


def test_asset_hash_mismatch_refuses_to_load(tmp_path):
    assets=json.loads((ROOT/ASSETS).read_text());role=assets['dense']
    fake=tmp_path/'dense';(fake/'onnx').mkdir(parents=True)
    for f in role['files']:(fake/f['file']).parent.mkdir(parents=True,exist_ok=True);(fake/f['file']).write_bytes(b'tampered')
    bad=tmp_path/'assets.json';bad.write_text(json.dumps({'dense':dict(role,local_dir=str(fake)),'reranker':assets['reranker']}))
    with pytest.raises(AssetMismatch):load_rankers(bad,roles=('dense',))


def test_core_imports_do_not_load_onnxruntime():
    code='import sys;import pipelines.evidence_aware.engine,evaluation.evidence_aware.runner;print("onnxruntime" in sys.modules)'
    assert subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()=='False'


PROSE=[unit('p1','Apple reported total net sales of $391 billion for fiscal 2024.'),unit('p2','The company granted restricted stock units to employees.'),unit('p3','Future lease payments are due through 2030.')]


@needs_models
def test_dense_ranker_is_deterministic_and_relevant_on_prose():
    dense=load_rankers(ROOT/ASSETS,roles=('dense',))['dense']
    assert dense.rank("What was Apple's revenue in fiscal 2024?",PROSE)[0]=='p1' and dense.revision.startswith('BAAI/bge-small-en-v1.5@5c38ec7')
    first=dense.rank('What was Apple FY2024 revenue?',UNITS);fresh=load_rankers(ROOT/ASSETS,roles=('dense',))['dense'].rank('What was Apple FY2024 revenue?',list(reversed(UNITS)))
    assert first==fresh and sorted(first)==['a','b','c']


@needs_models
def test_cross_encoder_reranker_prefers_revenue_table():
    rerank=load_rankers(ROOT/ASSETS,roles=('reranker',))['reranker']
    assert rerank.rank('What was Apple FY2024 revenue?',UNITS)[0]=='a' and rerank.revision.startswith('cross-encoder/ms-marco-MiniLM-L6-v2@233902d')


@needs_models
@pytest.mark.parametrize('backend',['dense','hybrid_rrf','hybrid_rrf_rerank'])
def test_runner_builds_model_backends_over_shared_units(tmp_path,backend):
    from evaluation.evidence_aware.runner import run
    out=run({'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','output':str(tmp_path/backend),'backend':backend,'cheap_context_tokens':64})
    traces=[json.loads(l) for l in (out/'traces.jsonl').read_text().splitlines()]
    assert len(traces)==8 and not any(t['answer']['status']=='error' for t in traces)
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['backend']==backend and manifest['ranker_revisions']


def test_revisions_require_verified_assets(tmp_path):
    from pipelines.evidence_aware.onnx_rankers import revisions
    assets=json.loads((ROOT/ASSETS).read_text());bad=tmp_path/'a.json'
    bad.write_text(json.dumps({'dense':dict(assets['dense'],local_dir=str(tmp_path/'missing'))}))
    assert revisions(bad)=={}
    if MODELS_PRESENT:assert set(revisions())=={'dense','reranker'}


@needs_models
def test_runner_reuses_preloaded_rankers_and_reports_usage(tmp_path):
    from evaluation.evidence_aware.runner import run
    rankers=load_rankers(ROOT/ASSETS)
    base={'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','cheap_context_tokens':64}
    first=run(dict(base,output=str(tmp_path/'a'),backend='hybrid_rrf_rerank'),rankers=rankers)
    indexed=rankers['dense'].index_stats['units']
    second=run(dict(base,output=str(tmp_path/'b'),backend='dense'),rankers=rankers)
    assert rankers['dense'].index_stats['units']==indexed
    m=json.loads((second/'manifest.json').read_text())
    assert m['model_inference']['dense']['query_embeddings']>0 and m['indexing']['reused_index'] is True
    assert json.loads((first/'manifest.json').read_text())['model_inference']['reranker']['pairs']>0


def test_runner_rejects_unknown_backend(tmp_path):
    from evaluation.evidence_aware.runner import run
    with pytest.raises(ValueError,match='unknown backend'):run({'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','output':str(tmp_path/'x'),'backend':'oracle'})
