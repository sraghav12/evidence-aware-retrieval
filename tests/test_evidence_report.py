import pytest
from evaluation.evidence_aware.report import score_answers,summarize,paired_cluster_summary


def trace(id='q',status='error',value=None,arm='rule'):
    return {'query_id':id,'answer':{'status':status,'value':value,'unit':'USD_million','citations':{}},'coverage_snapshots':[],'spec':None,'evidence':[],'usage':[],'input_mode':'raw_question','arm':arm}


def test_errors_stay_in_denominator():
    rows=score_answers([trace()],{'q':{'answerable':True,'status':'answered','value':'120','unit':'USD_million','component':'a'}})
    assert summarize(rows)['queries']==1 and summarize(rows)['errors']==1 and summarize(rows)['supported_success']==0


def test_correct_abstention_not_counted_as_answer_success():
    rows=score_answers([trace(status='abstained')],{'q':{'answerable':False,'status':'abstained','component':'a'}})
    assert rows[0]['correct_decision'] and not rows[0]['supported_correct']


def test_no_correct_answers_has_null_cost_per_correct():assert summarize(score_answers([trace()],{'q':{'answerable':True,'component':'a'}}))['cost_per_correct_usd'] is None


def paired():
    return [dict(query_id='a',arm=arm,component='company',repeat=repeat,supported_correct=value) for repeat in [0,1,2] for arm,value in [('cheap',0),('rule',1)]]


def test_repeats_resample_with_company_component():
    out=paired_cluster_summary(paired(),'component',11)
    assert out['independent_clusters']==1 and out['questions']==1 and out['paired_difference']==1


def test_oracle_excluded_from_deployable_rows():
    assert paired_cluster_summary(paired()+[dict(query_id='a',arm='oracle',component='company',repeat=0,supported_correct=True)],'component',11)['arms']==['cheap','rule']


def test_infeasible_context_has_null_accuracy():
    row=score_answers([trace(status='infeasible')],{'q':{'answerable':True,'component':'a'}})[0]
    assert row['supported_correct'] is None


def test_missing_arm_or_query_prevents_paired_claim():
    with pytest.raises(ValueError):paired_cluster_summary(paired()[:-1],'component',11)


def test_small_cluster_count_limits_claim():assert paired_cluster_summary(paired(),'component',11)['inference_status']=='descriptive_only'


def test_paired_difference_direction_follows_treatment():
    from evaluation.evidence_aware.report import paired_cluster_summary
    rows=[dict(arm=a,query_id=q,repeat=0,component=q,supported_correct=v,correct_decision=not v) for q in ('q1','q2') for a,v in (('zeta',True),('alpha',False))]
    assert paired_cluster_summary(rows,'component',11,treatment='zeta')['paired_difference']==1.0
    assert paired_cluster_summary(rows,'component',11,treatment='alpha')['paired_difference']==-1.0
    assert paired_cluster_summary(rows,'component',11,metric='correct_decision',treatment='alpha')['paired_difference']==1.0
