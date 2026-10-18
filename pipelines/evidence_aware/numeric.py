"""Decimal-only operations and exact numerical/citation audit."""
from decimal import Decimal,ROUND_HALF_EVEN,localcontext
from .contracts import AnswerRecord,CoverageResult
from .coverage import matches,SCALES


def abstain(reason):return AnswerRecord('abstained',reason=reason)


def execute_numeric(spec,coverage,spans):
    if not coverage.complete:return abstain('conflicting_evidence' if coverage.conflicts else 'incomplete_evidence')
    values={};citations={}
    for r in spec.requirements:
        eligible=[s for s in spans if s.id in coverage.audited_span_ids and matches(r,s)]
        converted={Decimal(s.value)*SCALES.get(s.unit,Decimal(1))/SCALES.get(r.unit,Decimal(1)) for s in eligible}
        if len(converted)!=1:return abstain('conflicting_evidence' if converted else 'incomplete_evidence')
        values[r.id]=next(iter(converted));citations[r.id]=sorted({s.id for s in eligible})
    if len({r.unit for r in spec.requirements})!=1:return abstain('incompatible_units')
    def growth(old,new):
        if old<=0:raise ValueError('unsupported_growth_base')
        return (new-old)/old*100
    def display(value):return format(value.quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN),'f')
    with localcontext() as ctx:
        ctx.prec=50
        operands=[values[i] for i in spec.operation.operands];kind=spec.operation.kind
        try:
            if kind=='extract':value=format(operands[0],'f');unit=spec.requirements[0].unit
            elif kind=='sum':value=format(sum(operands,Decimal(0)),'f');unit=spec.requirements[0].unit
            elif kind=='growth':value=display(growth(*operands));unit='percent'
            else:
                groups={}
                for r in spec.requirements:groups.setdefault(r.entity_id,[]).append(r)
                results=[]
                for entity,rr in groups.items():
                    rr=sorted(rr,key=lambda r:r.fiscal_year)
                    if len(rr)!=2:raise ValueError('ranking_requires_two_periods')
                    results.append((growth(values[rr[0].id],values[rr[1].id]),entity))
                results.sort(key=lambda item:(-item[0],item[1]));value=[];last=None;rank=0
                for index,(number,entity) in enumerate(results,1):
                    if last is None or number!=last:
                        rank=index;value.append({'rank':rank,'entities':[entity],'value':display(number)});last=number
                    else:value[-1]['entities'].append(entity)
                unit='percent'
        except ValueError as e:return abstain(str(e))
    return AnswerRecord('answered',value,unit,citations)


def audit_answer(answer,spec,spans):
    if answer.status!='answered':return answer
    ids=set(answer.citations)
    if ids!={r.id for r in spec.requirements}:return abstain('answer_audit_failed')
    by_id={s.id:s for s in spans};selected=[]
    for r in spec.requirements:
        cited=answer.citations.get(r.id,[])
        if not cited or any(s not in by_id or not matches(r,by_id[s]) for s in cited):return abstain('answer_audit_failed')
        selected.extend(by_id[s] for s in cited)
    coverage=CoverageResult(True,tuple(ids),(),(),tuple(s.id for s in selected))
    expected=execute_numeric(spec,coverage,selected)
    if expected.status!='answered' or expected.value!=answer.value or expected.unit!=answer.unit:return abstain('answer_audit_failed')
    return answer
