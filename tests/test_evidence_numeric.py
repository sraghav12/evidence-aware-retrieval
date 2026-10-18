from dataclasses import replace
from evidence_helpers import documents,spec,spans
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.numeric import execute_numeric,audit_answer
from pipelines.evidence_aware.contracts import AnswerRecord


def calc(q,ss=None):
    ss=spans() if ss is None else ss
    return execute_numeric(q,audit_coverage(q,ss,documents()),ss)


def test_growth_100_to_120_is_20_percent():
    a=calc(spec('What was Gamma FY2024 revenue growth over FY2023?'))
    assert (a.status,a.value,a.unit)==('answered','20.00','percent') and len(a.citations)==2


def test_exact_unit_scale_conversion():
    q=spec();r=replace(q.requirements[0],unit='USD_thousand');q=replace(q,requirements=(r,))
    assert calc(q).value=='120000'


def test_zero_and_negative_base_abstain():
    q=spec('What was Gamma FY2024 revenue growth over FY2023?');ss=[s for s in spans() if s.entity_id=='synthetic:gamma']
    for value in ['0','-10']:
        changed=[replace(s,value=value) if s.fiscal_year==2023 else s for s in ss]
        # Coverage established separately; executor must also reject unsupported arithmetic.
        a=execute_numeric(q,replace(audit_coverage(q,ss,documents()),complete=True),changed)
        assert a.status=='abstained' and a.reason=='unsupported_growth_base'


def test_mixed_currency_abstains():
    assert calc(spec('What was Mixed FY2024 revenue growth over FY2023?')).status=='abstained'


def test_missing_operand_abstains():assert calc(spec(),[]).status=='abstained'


def test_ties_preserve_entities():
    q=spec('Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.');ss=spans()
    ss=[replace(s,value='240') if s.entity_id=='synthetic:rankbeta' and s.fiscal_year==2024 else s for s in ss]
    a=execute_numeric(q,replace(audit_coverage(q,spans(),documents()),complete=True),ss)
    assert a.value==[{'rank':1,'entities':['synthetic:rankalpha','synthetic:rankbeta'],'value':'20.00'}]


def test_rank_uses_unrounded_values():
    q=spec('Rank RankAlpha and RankBeta by FY2024 revenue growth over FY2023.');ss=spans()
    ss=[replace(s,value='240.001') if s.entity_id=='synthetic:rankbeta' and s.fiscal_year==2024 else s for s in ss]
    a=execute_numeric(q,replace(audit_coverage(q,spans(),documents()),complete=True),ss)
    assert a.value[0]['entities']==['synthetic:rankbeta'] and a.value[1]['entities']==['synthetic:rankalpha']


def test_uncited_added_claim_rejected():
    q=spec();assert audit_answer(AnswerRecord('answered','999','USD_million',{}),q,spans()).status=='abstained'
    a=calc(q);assert audit_answer(replace(a,value='121'),q,spans()).status=='abstained'
    assert audit_answer(a,q,spans()).status=='answered'
