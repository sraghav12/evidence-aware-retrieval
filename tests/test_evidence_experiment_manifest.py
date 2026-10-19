import json
import pytest
from evidence_helpers import documents
from evaluation.evidence_aware.dataset import build_pilot_manifest,validate_manifest
from evaluation.evidence_aware.experiment import build_experiment_manifest,validate_experiment
from evaluation.evidence_aware.xbrl_reference import revenue_facts
from pathlib import Path

QUESTIONS=[{'id':'q1','question':'What was Alpha FY2024 revenue?','as_of':'2025-03-01'},{'id':'q2','question':'What was Beta FY2024 revenue?','as_of':'2025-03-01'}]
BASE={'answerer':'decimal_executor','budget_profiles':[{'name':'ctx4096','max_context_tokens':4096},{'name':'ctx8192','max_context_tokens':8192}],'max_output_tokens':512,
      'seed':11,'repeats':1,'primary':{'treatment':'coverage_rule_v1','comparator':'always_maximum_v1','budget':'ctx8192'},'provider_enabled':False,'max_usd':0}


def manifest(**overrides):return build_experiment_manifest(dict(BASE,**overrides),documents(),QUESTIONS,available_rankers={})


def test_all_arms_share_units_and_answerer():
    m=manifest();arms=m['arms']
    assert len({a['units_hash'] for a in arms})==1 and len({a['answerer'] for a in arms})==1
    assert {a['name'] for a in arms if a['track']=='scheduling'}=={'always_cheap_v1','always_maximum_v1','coverage_rule_v1','complexity_rule_v1'}


def test_every_arm_has_identical_limits_gate_and_audit_per_budget():
    m=manifest();validate_experiment(m)
    for profile in ('ctx4096','ctx8192'):
        rows=[a for a in m['arms'] if a['budget']==profile]
        for k in ('max_context_tokens','max_output_tokens','gate','answer_audit','executor','answerer','model_revision','prompt_hash','decoding'):
            assert len({json.dumps(a[k]) for a in rows})==1,k
    assert all(a['max_output_tokens']==512 for a in m['arms'])
    for k,v in (('max_context_tokens',2048),('prompt_hash','d'*64),('gate','none')):
        bad=json.loads(json.dumps(m));bad['arms'][1][k]=v;bad.pop('manifest_sha256')
        with pytest.raises(ValueError,match='gate' if k=='gate' else f'unmatched {k}'):validate_experiment(bad)


def test_unavailable_strategy_arms_are_never_bm25():
    m=manifest();strategy={a['name']:a for a in m['arms'] if a['track']=='strategy' and a['budget']=='ctx8192'}
    assert strategy['bm25']['status']=='available'
    for name in ('dense','hybrid_rrf','hybrid_rrf_rerank'):
        assert strategy[name]['status']=='unavailable' and strategy[name]['reason'] and strategy[name]['backend']!='bm25'


def test_model_revision_and_prompt_required():
    with pytest.raises(ValueError):manifest(answerer='model_qa')
    with pytest.raises(ValueError):manifest(answerer='model_qa',model_revision='m@abc',decoding={'temperature':0})
    with pytest.raises(ValueError):manifest(answerer='model_qa',prompt_hash='a'*64,decoding={'temperature':0})
    with pytest.raises(ValueError):manifest(answerer='model_qa',model_revision='m@abc',prompt_hash='a'*64)
    m=manifest(answerer='model_qa',model_revision='m@abc',prompt_hash='a'*64,decoding={'temperature':0})
    assert m['estimates']['provider_requests']==2*m['estimates']['available_arm_runs_per_question']*1
    assert m['live_execution']=='disabled' and m['estimates']['estimated_usd'] is None


def test_primary_comparison_frozen_and_order_deterministic():
    a=manifest();b=manifest()
    assert a['primary']==BASE['primary'] and a['run_order_sha256']==b['run_order_sha256'] and a['manifest_sha256']==b['manifest_sha256']
    with pytest.raises(ValueError):manifest(primary={'treatment':'coverage_rule_v1','comparator':'dense','budget':'ctx8192'})


def test_attached_hashes_are_covered_by_manifest_hash():
    m=build_experiment_manifest(BASE,documents(),QUESTIONS,available_rankers={},attachments={'split_manifest_sha256':'b'*64})
    assert m['split_manifest_sha256']=='b'*64;validate_experiment(json.loads(json.dumps(m)))
    m['split_manifest_sha256']='c'*64
    with pytest.raises(ValueError,match='manifest hash'):validate_experiment(m)


def row(qid,entities,template='extract',sources=(),derivation=(),development_only=False):
    return dict(query_id=qid,entity_ids=list(entities),source_ancestry=list(sources),derivation_ancestry=list(derivation),template=template,development_only=development_only)


def test_split_overlap_rejected():
    m=build_pilot_manifest([row('b1',['cik:1'],development_only=True),row('p1',['cik:1']),row('p2',['cik:2']),row('p3',['cik:3']),row('p4',['cik:4']),row('p5',['cik:5'])],11)
    rows={r['query_id']:r for r in m['rows']}
    assert rows['p1']['split']=='development' and rows['p1']['component']==rows['b1']['component']
    victim=next(r for r in m['rows'] if r['split']=='test');other=next(r for r in m['rows'] if r['split']=='development' and r['query_id']!=victim['query_id'])
    other['entity_ids']=victim['entity_ids']
    with pytest.raises(ValueError,match='forbidden overlap'):validate_manifest(m)


def test_generic_grammar_does_not_connect_unrelated_cases():
    m=build_pilot_manifest([row('a',['cik:1'],'extract'),row('b',['cik:2'],'extract'),row('c',['cik:3'],'extract'),row('d',['cik:4'],'extract')],11)
    assert len({r['component'] for r in m['rows']})==4 and m['grammar_overlap']['extract']==4
    assert m['effective_groups']['total']==4


def test_collapsed_components_are_not_forced_into_test():
    m=build_pilot_manifest([row('a',['cik:1','cik:2'],'sum'),row('b',['cik:2','cik:3'],'sum'),row('c',['cik:3'],development_only=True)],11)
    assert {r['split'] for r in m['rows']}=={'development'} and m['locked_test'].startswith('infeasible')


def test_reference_reader_focus_allows_inner_markup():
    from evaluation.evidence_aware.xbrl_reference import fiscal_focus
    raw=(Path(__file__).parent/'fixtures/evidence_v2/html/date_columns.html').read_bytes().replace(b'id="f-1">2024</ix:nonNumeric>',b'id="f-1"><b style="x">2024</b></ix:nonNumeric>')
    assert fiscal_focus(raw)=={'fiscal_year':2024,'period_start':'2023-10-01','period_end':'2024-09-28'}


def test_reference_reader_ignores_tables_and_dimensions():
    raw=(Path(__file__).parent/'fixtures/evidence_v2/html/date_columns.html').read_bytes()
    facts=revenue_facts(raw)
    assert sorted((f['period_end'],f['value']) for f in facts)==[('2023-09-30','100000'),('2024-09-28','120500')]


def test_locked_test_requires_enough_informative_groups():
    singles=[row(f'p{i}',[f'cik:{i}']) for i in range(1,4)]+[row(f'u{i}',[f'unknown:x{i}'],'unknown_company') for i in range(3)]
    m=build_pilot_manifest(singles,11,min_locked_groups=2)
    assert {r['split'] for r in m['rows']}=={'development'} and m['locked_test'].startswith('infeasible') and m['effective_groups']['informative_eligible']==3
    m=build_pilot_manifest(singles+[row('p4',['cik:4'])],11,min_locked_groups=2)
    assert m['locked_test']=='feasible' and m['effective_groups']['test']>=2


def test_stage_limits_and_per_arm_configs_come_from_config():
    m=manifest(stage_context_tokens=1024,cheap_context_tokens=64)
    assert all(a['stage_limits']['stage_context_tokens']==1024 and a['stage_limits']['cheap_context_tokens']==64 for a in m['arms'])
    from evaluation.evidence_aware.experiment import engine_config
    from pipelines.evidence_aware.contracts import digest
    assert all(a['engine_config_sha256']==digest(engine_config(a)) for a in m['arms'])
    assert len({a['engine_config_sha256'] for a in m['arms'] if a['track']=='scheduling'})==8


def test_manifest_hash_required_and_freeze_covers_scripts_and_lock():
    m=manifest();bad=dict(m);bad.pop('manifest_sha256')
    with pytest.raises(ValueError,match='manifest hash'):validate_experiment(bad)
    assert {'scripts/run_evidence_v2.py','scripts/freeze_experiment_v2.py','scripts/run_experiment_v2.py','requirements-evidence-v2-compat.lock'}<=set(m['source_sha256'])


def test_arm_sensitivity_counts_parse_and_zero_cell_invariant_rows():
    from evaluation.evidence_aware.experiment import arm_sensitivity
    from evaluation.evidence_aware.runner import read_jsonl
    fix='tests/fixtures/evidence_v2';d=documents();qs=read_jsonl(f'{fix}/queries.jsonl');refs={r['query_id']:r for r in read_jsonl(f'{fix}/references.jsonl')}
    aliases={x['entity_id'].split(':')[-1].casefold():x['entity_id'] for x in d.values()}
    s=arm_sensitivity(qs,d,aliases,refs)
    assert s['parse_invariant']=={'unknown_fiscal_calendar':1} and s['zero_cell_invariant']=={'unanswerable':1}
    assert s['arm_sensitive']==6 and s['arm_sensitive_answerable']==3 and s['arm_sensitive_groups']==6


V3=dict(BASE,gate='audit_coverage_v3',probe_units_per_filing=3,probe_tokens=2048,budget_profiles=[{'name':'ctx8192','max_context_tokens':8192}],strategy_arms=['bm25','hybrid_rrf'],
        gate_ablation=[{'name':'coverage_rule_v1_gate_v2','policy':'coverage_rule_v1','backend':'bm25','gate':'audit_coverage_v2'}],
        secondary=[{'name':'gate_v3_vs_v2','treatment':'coverage_rule_v1','comparator':'coverage_rule_v1_gate_v2','budget':'ctx8192'}])


def test_gate_ablation_arm_differs_only_by_gate():
    from evaluation.evidence_aware.experiment import engine_config
    m=build_experiment_manifest(V3,documents(),QUESTIONS,available_rankers={'dense':'d@1'})
    arms={a['name']:a for a in m['arms']}
    assert {a['gate'] for a in m['arms'] if a['track']!='gate_ablation'}=={'audit_coverage_v3'} and arms['coverage_rule_v1_gate_v2']['gate']=='audit_coverage_v2'
    assert set(arms)=={'bm25','hybrid_rrf','always_cheap_v1','always_maximum_v1','complexity_rule_v1','coverage_rule_v1','coverage_rule_v1_gate_v2'}
    a,b=engine_config(arms['coverage_rule_v1']),engine_config(arms['coverage_rule_v1_gate_v2'])
    assert {k for k in a if a[k]!=b.get(k)}=={'gate'} and a['probe_tokens']==2048
    assert m['secondary']==V3['secondary'];validate_experiment(m)
    bad=json.loads(json.dumps(m));bad.pop('manifest_sha256');next(x for x in bad['arms'] if x['name']=='always_cheap_v1')['gate']='audit_coverage_v2'
    with pytest.raises(ValueError,match='gate'):validate_experiment(bad)
    with pytest.raises(ValueError):build_experiment_manifest(dict(V3,secondary=[{'name':'x','treatment':'coverage_rule_v1','comparator':'nope','budget':'ctx8192'}]),documents(),QUESTIONS,available_rankers={})


def test_heldout_manifest_is_all_locked_test_and_disjoint_from_development():
    from evaluation.evidence_aware.dataset import build_heldout_manifest
    dev=[row('rd1',['cik:1'],development_only=True),row('v1:q1',['cik:2'],development_only=True)]
    held=[row(f'h{i}',[f'cik:{10+i}']) for i in range(12)]+[row('hs',['cik:10','cik:11'],'sum')]
    m=build_heldout_manifest(held,dev)
    assert {r['split'] for r in m['rows']}=={'test'} and m['effective_groups']['test']==11 and m['inference_status']=='descriptive_only'
    assert build_heldout_manifest([row(f'h{i}',[f'cik:{10+i}']) for i in range(12)],dev)['inference_status']=='pilot_interval_not_confirmatory'
    with pytest.raises(ValueError,match='overlap'):build_heldout_manifest(held+[row('bad',['cik:2'])],dev)
