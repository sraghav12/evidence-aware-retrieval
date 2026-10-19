import json
import pytest
from evidence_helpers import documents
from evaluation.evidence_aware.experiment import build_experiment_manifest
from evaluation.evidence_aware.experiment_runner import run_experiment,FreezeMismatch
from evaluation.evidence_aware.experiment_report import build_experiment_report
from evaluation.evidence_aware.runner import read_jsonl

FIX='tests/fixtures/evidence_v2'
CONFIG={'answerer':'decimal_executor','budget_profiles':[{'name':'ctx4096','max_context_tokens':4096},{'name':'ctx8192','max_context_tokens':8192}],'max_output_tokens':512,'seed':11,'repeats':1,
        'primary':{'treatment':'coverage_rule_v1','comparator':'always_maximum_v1','budget':'ctx8192'},'provider_enabled':False,'max_usd':0,'cheap_context_tokens':64,'documents':f'{FIX}/documents.jsonl'}


@pytest.fixture
def frozen():
    questions=read_jsonl(f'{FIX}/queries.jsonl');return build_experiment_manifest(CONFIG,documents(),questions,available_rankers={}),questions


def test_runs_exactly_the_frozen_order(tmp_path,frozen):
    m,questions=frozen;out=run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')
    traces=[json.loads(l) for l in (out/'traces.jsonl').read_text().splitlines()]
    assert len(traces)==m['run_count']==8*4*2 and [t['order_index'] for t in traces]==list(range(m['run_count']))
    assert {t['arm'] for t in traces}=={f'{p}@{b}' for p in ('always_cheap_v1','always_maximum_v1','complexity_rule_v1','coverage_rule_v1') for b in ('ctx4096','ctx8192')}
    status=json.loads((out/'status.json').read_text());assert status['complete'] and status['rows']==m['run_count']
    run=json.loads((out/'manifest.json').read_text());assert run['experiment_manifest_sha256']==m['manifest_sha256'] and run['provider_calls']==0
    with pytest.raises(FileExistsError):run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')


def test_refuses_inputs_that_differ_from_an_intact_freeze(tmp_path,frozen):
    m,questions=frozen;docs=documents();docs.pop(next(iter(docs)))
    with pytest.raises(FreezeMismatch,match='corpus'):run_experiment(m,CONFIG,docs,questions,{},tmp_path/'a')
    with pytest.raises(FreezeMismatch,match='questions'):run_experiment(m,CONFIG,documents(),questions[:-1],{},tmp_path/'b')
    with pytest.raises(FreezeMismatch,match='config'):run_experiment(m,dict(CONFIG,cheap_context_tokens=128),documents(),questions,{},tmp_path/'c')
    reordered=json.loads(json.dumps(m));reordered['seed']=12
    with pytest.raises(FreezeMismatch,match='run order'):run_experiment(reordered,CONFIG,documents(),questions,{},tmp_path/'d')


def test_refuses_edited_manifest(tmp_path,frozen):
    m,questions=frozen;edited=json.loads(json.dumps(m));edited['primary']=dict(m['primary'],budget='ctx4096')
    with pytest.raises(FreezeMismatch,match='manifest hash'):run_experiment(edited,CONFIG,documents(),questions,{},tmp_path/'run')


def test_refuses_changed_source_code(tmp_path,frozen):
    m,questions=frozen;m=json.loads(json.dumps(m));k=next(iter(m['source_sha256']));m['source_sha256'][k]='0'*64
    with pytest.raises(FreezeMismatch,match='source'):run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')


def test_refuses_unavailable_arm_run(tmp_path,frozen):
    m,questions=frozen;m=json.loads(json.dumps(m));arm=next(a for a in m['arms'] if a['name']=='dense')
    assert arm['status']=='unavailable'
    run=run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')
    assert not any(json.loads(l)['arm'].startswith('dense') for l in (run/'traces.jsonl').read_text().splitlines())


def test_report_separates_answerable_unanswerable_and_pairs_primary(tmp_path,frozen):
    m,questions=frozen;out=run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')
    r=build_experiment_report(out,f'{FIX}/references.jsonl',m)
    arm=r['arms']['coverage_rule_v1@ctx8192']['all']
    assert arm['answerable']==3 and arm['unanswerable']==5 and arm['supported_success']==3 and arm['correct_abstentions']==5
    assert 'p50_ms' in arm['latency'] and arm['inspected_retrieval_tokens']>0
    primary={(c['split'],c['metric']):c for c in r['comparisons'] if c['name']=='primary'}
    assert set(primary)=={('all','supported_correct'),('all','correct_abstention')}
    assert all(c['inference_status']=='descriptive_only' for c in primary.values())
    assert r['timing_kind']=='fresh_local' and r['costs']['compute_cost_usd'] is None
    assert (out/'experiment_report.json').is_file() and (out/'quality_resource.svg').read_text().startswith('<svg')


def test_report_adds_preregistered_arm_sensitive_subset(tmp_path):
    from evaluation.evidence_aware.experiment import arm_sensitivity
    questions=read_jsonl(f'{FIX}/queries.jsonl');refs={r['query_id']:r for r in read_jsonl(f'{FIX}/references.jsonl')}
    d=documents();aliases={x['entity_id'].split(':')[-1].casefold():x['entity_id'] for x in d.values()}
    m=build_experiment_manifest(CONFIG,d,questions,available_rankers={},attachments={'arm_sensitivity':arm_sensitivity(questions,d,aliases,refs)})
    r=build_experiment_report(run_experiment(m,CONFIG,d,questions,{},tmp_path/'run'),f'{FIX}/references.jsonl',m)
    sub=r['arms']['coverage_rule_v1@ctx8192']['arm_sensitive']
    assert sub['questions']==6 and r['arms']['coverage_rule_v1@ctx8192']['all']['questions']==8
    assert {(c['split'],c['metric']) for c in r['comparisons'] if c['name']=='primary'}>={('arm_sensitive','supported_correct')}


def test_report_with_a_single_named_split(tmp_path,frozen):
    m,questions=frozen;out=run_experiment(m,CONFIG,documents(),questions,{},tmp_path/'run')
    refs=tmp_path/'refs.jsonl';refs.write_text(''.join(json.dumps(dict(r,split='development'))+'\n' for r in read_jsonl(f'{FIX}/references.jsonl')))
    r=build_experiment_report(out,str(refs),m)
    assert set(r['arms']['coverage_rule_v1@ctx8192'])=={'development'} and 'development' in (out/'quality_resource.svg').read_text()
