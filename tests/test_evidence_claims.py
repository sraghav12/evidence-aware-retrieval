import pytest
from evaluation.evidence_aware.claims import validate_claims

REPORT={'run_id':'pilot_001','input_mode':'raw_question','timing_kind':'fresh_local','costs':{'estimated_api_usd':0,'compute_cost_usd':None},
        'arms':{'coverage_rule_v1@ctx8192':{'test':{'supported_success':10,'answerable':25,'inspected_retrieval_tokens':900}}},
        'comparisons':[{'name':'primary','split':'test','metric':'supported_correct','treatment':'coverage_rule_v1@ctx8192','comparator':'always_maximum_v1@ctx8192',
                        'paired_difference':0.0,'ci95':[-0.08,0.08],'independent_clusters':8,'inference_status':'descriptive_only'}]}
REPLAY=dict(REPORT,run_id='replay_001',timing_kind='replay')
DIAG=dict(REPORT,run_id='diag_001',input_mode='diagnostic_spec')
REPORTS={r['run_id']:r for r in (REPORT,REPLAY,DIAG)}


def metric(**kw):return dict(dict(kind='metric',run_id='pilot_001',arm='coverage_rule_v1@ctx8192',split='test',metric='supported_success',value=10,input_mode='raw_question'),**kw)


def test_claims_reference_run_and_metric():
    validate_claims([metric()],REPORTS)
    for bad in (metric(run_id='nope'),metric(metric='accuracy'),metric(value=11),metric(arm='dense@ctx8192')):
        with pytest.raises(ValueError):validate_claims([bad],REPORTS)


def test_replay_not_measured_latency():
    validate_claims([dict(kind='latency',run_id='pilot_001',input_mode='raw_question')],REPORTS)
    with pytest.raises(ValueError,match='replay'):validate_claims([dict(kind='latency',run_id='replay_001',input_mode='raw_question')],REPORTS)


def test_unknown_cost_blocks_savings_claim():
    with pytest.raises(ValueError,match='unknown cost'):validate_claims([dict(kind='savings',run_id='pilot_001',input_mode='raw_question')],REPORTS)
    priced=dict(REPORT,run_id='priced',costs={'estimated_api_usd':1.0,'compute_cost_usd':0.5})
    validate_claims([dict(kind='savings',run_id='priced',input_mode='raw_question')],{'priced':priced})


def test_noninferiority_requires_interval():
    claim=dict(kind='noninferiority',run_id='pilot_001',comparison='primary',margin=0.02,input_mode='raw_question')
    with pytest.raises(ValueError,match='descriptive'):validate_claims([claim],REPORTS)
    confirm=dict(REPORT,run_id='c',comparisons=[dict(REPORT['comparisons'][0],inference_status='pilot_interval_not_confirmatory',ci95=[-0.01,0.03])])
    validate_claims([dict(claim,run_id='c')],{'c':confirm})
    no_interval=dict(confirm,comparisons=[dict(confirm['comparisons'][0],ci95=None)])
    with pytest.raises(ValueError,match='interval'):validate_claims([dict(claim,run_id='c')],{'c':no_interval})
    wide=dict(confirm,comparisons=[dict(confirm['comparisons'][0],ci95=[-0.05,0.03])])
    with pytest.raises(ValueError,match='margin'):validate_claims([dict(claim,run_id='c')],{'c':wide})


def test_raw_question_results_separate_from_diagnostics():
    with pytest.raises(ValueError,match='input mode'):validate_claims([metric(run_id='diag_001')],REPORTS)
    validate_claims([metric(run_id='diag_001',input_mode='diagnostic_spec')],REPORTS)
