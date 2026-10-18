"""Provider-independent orchestration with source-unit packing and full traces."""
from dataclasses import asdict
from time import monotonic,perf_counter
from .contracts import BudgetState,RoutingState,RunTrace,UsageEvent,digest,AnswerRecord
from .coverage import audit_coverage
from .numeric import execute_numeric,audit_answer,abstain
from .policy import decide_route


def run_spec(spec,backends,documents,config,answerer=None):
    budget=BudgetState(context_tokens_remaining=config.get('max_context_tokens',8192),output_tokens_remaining=config.get('max_output_tokens',512),max_usd=config.get('max_usd',0),deadline_ms=config.get('deadline_ms',30000),retrieval_tokens_remaining=config.get('retrieval_tokens_total',24576),verification_tokens_remaining=config.get('verification_tokens_total',24576))
    trace=RunTrace(spec.id,spec.question,spec.as_of,config.get('input_mode','raw_question'),digest(asdict(spec)),digest(config),digest(documents),spec=asdict(spec))
    started=monotonic();deadline=started+budget.deadline_ms/1000;attempted=[];collected={};units={};action='cheap_search';missing=[]
    while True:
        if monotonic()>=deadline:
            trace.answer=abstain('budget_exhausted');trace.decisions.append({'action':'abstain','reason_codes':['budget_exhausted']});break
        backend=backends[action]
        limit=min(config.get('stage_context_tokens',8192),budget.retrieval_tokens_remaining,budget.verification_tokens_remaining)
        if action=='cheap_search':limit=min(limit,config.get('cheap_context_tokens',8192))
        before=perf_counter();attempted.append(action)
        new=backend.retrieve(spec,missing,max(0,limit));selected=getattr(backend,'selected',[])
        inspected=getattr(backend,'inspected_tokens',sum(len(s.quote.split()) for s in new))
        if inspected>limit:raise ValueError('backend exceeded input reservation')
        budget.retrieval_tokens_remaining-=inspected
        for u in selected:units[u.id]=u
        trace.selected_units.append({'stage':action,'ids':[u.id for u in selected],'inspected_tokens':inspected})
        for s in new:collected[s.id]=s
        packed=[];packed_units=[];count=0
        for u in units.values():
            size=len(u.text.split())
            if len(packed_units)>=config.get('max_packed_sections',12):break
            if count+size>budget.context_tokens_remaining:continue
            packed_units.append(u);count+=size
        if units:
            packed=[s for s in collected.values() if any(s.doc_id==u.doc_id and u.start<=s.start and s.end<=u.end for u in packed_units)]
        else:
            for s in collected.values():
                size=len(s.quote.split())
                if count+size<=budget.context_tokens_remaining:packed.append(s);count+=size
        trace.packed_ids=[s.id for s in packed]
        trace.decisions.append({'action':action,'reason_codes':['initial_retrieval' if len(attempted)==1 else 'missing_operands'],'missing_requirement_ids':list(missing)})
        trace.usage.append(asdict(UsageEvent(f'{spec.id}:{action}',spec.id,'retrieval',input_tokens=inspected,elapsed_ms=(perf_counter()-before)*1000)))
        if count>budget.verification_tokens_remaining:
            trace.answer=abstain('budget_exhausted');trace.decisions.append({'action':'abstain','reason_codes':['verification_budget_exhausted']});break
        budget.verification_tokens_remaining-=count
        before=perf_counter();coverage=audit_coverage(spec,packed,documents)
        trace.usage.append(asdict(UsageEvent(f'{spec.id}:{action}:audit',spec.id,'verification',input_tokens=count,elapsed_ms=(perf_counter()-before)*1000)))
        trace.coverage_snapshots.append(asdict(coverage));trace.evidence=[asdict(s) for s in packed]
        budget.deadline_ms=max(0,int((deadline-monotonic())*1000))
        decision=decide_route(spec,coverage,budget,RoutingState(len(attempted),tuple(attempted)))
        if monotonic()>=deadline:decision=type(decision)('abstain',('budget_exhausted',),coverage.missing_requirement_ids)
        if decision.action=='answer':
            result=execute_numeric(spec,coverage,packed)
            if result.status=='answered' and answerer is not None:
                reserve=config.get('generation_reservation_usd')
                if not config.get('provider_enabled',False) or budget.max_usd<=0 or reserve is None or reserve>budget.max_usd:
                    result=abstain('provider_budget_disabled')
                else:
                    # Contract deliberately excludes the private executor result.
                    result=audit_answer(answerer.answer(spec,packed),spec,packed)
            trace.answer=result;trace.decisions.append({'action':'answer' if result.status=='answered' else 'abstain','reason_codes':[result.reason or 'complete_evidence']});break
        if decision.action=='abstain':
            trace.answer=abstain(decision.reason_codes[0]);trace.decisions.append(asdict(decision));break
        action=decision.action;missing=list(decision.missing_requirement_ids)
    return trace
