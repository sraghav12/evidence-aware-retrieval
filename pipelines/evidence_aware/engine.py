"""Provider-independent orchestration with source-unit packing and full traces."""
from dataclasses import asdict
from time import monotonic,perf_counter
from .contracts import BudgetState,RoutingState,RunTrace,UsageEvent,digest,AnswerRecord
from .coverage import audit_coverage,same_quantity
from .units import build_units
from .extraction import extract_candidates
from .numeric import execute_numeric,audit_answer,abstain
from .policy import decide


def contains(unit,span):return span.doc_id==unit.doc_id and unit.start<=span.start and span.end<=unit.end


def pack(spec,units,collected,token_limit,max_sections):
    """Units holding a candidate cell for any requirement pack first, then the rest, each in first-seen order."""
    relevant={u.id for u in units.values() if any(contains(u,s) and any(same_quantity(r,s) for r in spec.requirements) for s in collected.values())}
    ordered=[u for u in units.values() if u.id in relevant]+[u for u in units.values() if u.id not in relevant]
    packed_units=[];omitted=[];count=0
    for u in ordered:
        size=len(u.text.split())
        if len(packed_units)>=max_sections or count+size>token_limit:omitted.append(u.id);continue
        packed_units.append(u);count+=size
    return packed_units,omitted,count


GATES={'audit_coverage_v2','audit_coverage_v3','audit_coverage_v4'}


def conflict_probe(spec,coverage,packed,documents,config,budget):
    """Gate v3: one bounded structured look at later eligible filings of each cited entity for the same quantities.
    Restatements surface as comparative columns in later 10-Ks, which relevance ranking may never retrieve."""
    cap=min(config.get('probe_tokens',2048),budget.retrieval_tokens_remaining,budget.verification_tokens_remaining)
    if config.get('gate')=='audit_coverage_v4':
        # Gate v4: every eligible filing of each cited entity that has not already supplied a same-quantity cell, earlier or later.
        same=[s for s in packed if any(same_quantity(r,s) for r in spec.requirements)];supplied={s.doc_id for s in same}
        entity_docs={d for d,doc in documents.items() if doc['entity_id'] in {s.entity_id for s in same} and doc['disclosed_at']<=spec.as_of}
        later=sorted(entity_docs-supplied,key=lambda d:(documents[d]['disclosed_at'],d))
        empty='other_filings_already_packed' if len(entity_docs)>1 else 'no_other_filings'
    else:
        # Gate v3 as frozen in protocol v3: later filings only, skipping any filing that contributed any packed cell.
        cited=[s for s in packed if s.id in coverage.audited_span_ids];packed_docs={s.doc_id for s in packed}
        later=sorted({d for e in {s.entity_id for s in cited} for d,doc in documents.items() if doc['entity_id']==e and doc['disclosed_at']<=spec.as_of
                      and doc['disclosed_at']>min(s.disclosed_at for s in cited if s.entity_id==e) and d not in packed_docs},key=lambda d:(documents[d]['disclosed_at'],d))
        empty='no_later_filings'
    record={'status':empty if not later else 'ran','probed_doc_ids':[],'inspected_tokens':0,'budget_tokens':cap,'spans':[],'conflicts':[]}
    if not later:return record,[]
    if cap<=0:record['status']='skipped_budget';return record,[]
    found=[]
    for d in later:
        units=[u for u in build_units({d:documents[d]}) if any(same_quantity(r,s) for s in extract_candidates([u],documents) for r in spec.requirements)][:config.get('probe_units_per_filing',3)]
        for u in units:
            size=len(u.text.split())
            if record['inspected_tokens']+size>cap:record['status']='ran_truncated';continue
            record['inspected_tokens']+=size;found.extend(s for s in extract_candidates([u],documents) if any(same_quantity(r,s) for r in spec.requirements))
            if d not in record['probed_doc_ids']:record['probed_doc_ids'].append(d)
    record['spans']=[s.id for s in found]
    return record,found


def run_spec(spec,backends,documents,config,answerer=None):
    budget=BudgetState(context_tokens_remaining=config.get('max_context_tokens',8192),output_tokens_remaining=config.get('max_output_tokens',512),max_usd=config.get('max_usd',0),deadline_ms=config.get('deadline_ms',30000),retrieval_tokens_remaining=config.get('retrieval_tokens_total',24576),verification_tokens_remaining=config.get('verification_tokens_total',24576))
    gate=config.get('gate','audit_coverage_v2')
    if gate not in GATES:raise ValueError(f'unknown gate: {gate}')
    trace=RunTrace(spec.id,spec.question,spec.as_of,config.get('input_mode','raw_question'),digest(asdict(spec)),digest(config),digest(documents),policy_version=config.get('policy','coverage_rule_v1'),spec=asdict(spec),gate=gate)
    try:route(spec,backends,documents,config,answerer,budget,trace)
    except Exception as e:
        # Keep attempted stages and usage; a failed row is never an empty, zero-cost row.
        trace.answer=AnswerRecord('error',reason=type(e).__name__);trace.decisions.append({'action':'error','reason_codes':[type(e).__name__]})
    return trace


def route(spec,backends,documents,config,answerer,budget,trace):
    started=monotonic();deadline=started+budget.deadline_ms/1000;attempted=[];collected={};units={};action='cheap_search';missing=[]
    while True:
        if monotonic()>=deadline:
            trace.answer=abstain('budget_exhausted');trace.decisions.append({'action':'abstain','reason_codes':['budget_exhausted']});return
        backend=backends[action]
        limit=min(config.get('stage_context_tokens',8192),budget.retrieval_tokens_remaining,budget.verification_tokens_remaining)
        if action=='cheap_search':limit=min(limit,config.get('cheap_context_tokens',8192))
        before=perf_counter();attempted.append(action)
        new=backend.retrieve(spec,missing,max(0,limit),exclude_unit_ids=frozenset(units));selected=getattr(backend,'selected',[])
        inspected=getattr(backend,'inspected_tokens',sum(len(s.quote.split()) for s in new))
        if inspected>limit:raise ValueError('backend exceeded input reservation')
        budget.retrieval_tokens_remaining-=inspected
        for u in selected:units[u.id]=u
        trace.selected_units.append({'stage':action,'ids':[u.id for u in selected],'inspected_tokens':inspected})
        for s in new:collected[s.id]=s
        if units:
            packed_units,omitted,count=pack(spec,units,collected,budget.context_tokens_remaining,config.get('max_packed_sections',12))
            packed=[s for s in collected.values() if any(contains(u,s) for u in packed_units)]
        else:
            packed=[];omitted=[];count=0
            for s in collected.values():
                size=len(s.quote.split())
                if count+size<=budget.context_tokens_remaining:packed.append(s);count+=size
                else:omitted.append(s.id)
            packed_units=[]
        trace.packed_ids=[s.id for s in packed]
        trace.packing.append({'stage':action,'packed_unit_ids':[u.id for u in packed_units],'omitted_unit_ids':omitted,'packed_tokens':count})
        trace.decisions.append({'action':action,'reason_codes':['initial_retrieval' if len(attempted)==1 else 'missing_operands'],'missing_requirement_ids':list(missing)})
        trace.usage.append(asdict(UsageEvent(f'{spec.id}:{action}',spec.id,'retrieval',input_tokens=inspected,elapsed_ms=(perf_counter()-before)*1000)))
        if count>budget.verification_tokens_remaining:
            trace.answer=abstain('budget_exhausted');trace.decisions.append({'action':'abstain','reason_codes':['verification_budget_exhausted']});return
        budget.verification_tokens_remaining-=count
        precise={'audit_coverage_v3':'group','audit_coverage_v4':'pairwise'}.get(config.get('gate'),False)
        before=perf_counter();coverage=audit_coverage(spec,packed,documents,precision_aware=precise)
        trace.usage.append(asdict(UsageEvent(f'{spec.id}:{action}:audit',spec.id,'verification',input_tokens=count,elapsed_ms=(perf_counter()-before)*1000)))
        trace.coverage_snapshots.append(asdict(coverage));trace.evidence=[asdict(s) for s in packed]
        budget.deadline_ms=max(0,int((deadline-monotonic())*1000))
        decision=decide(config.get('policy','coverage_rule_v1'),spec,coverage,budget,RoutingState(len(attempted),tuple(attempted)))
        if monotonic()>=deadline:decision=type(decision)('abstain',('budget_exhausted',),coverage.missing_requirement_ids)
        if decision.action=='answer' and precise:
            before=perf_counter();probe,extra=conflict_probe(spec,coverage,packed,documents,config,budget)
            budget.retrieval_tokens_remaining-=probe['inspected_tokens'];budget.verification_tokens_remaining-=probe['inspected_tokens']
            if probe['status'] in ('ran','ran_truncated'):
                trace.usage.append(asdict(UsageEvent(f'{spec.id}:conflict_probe',spec.id,'conflict_probe',input_tokens=probe['inspected_tokens'],elapsed_ms=(perf_counter()-before)*1000)))
                recheck=audit_coverage(spec,packed+[s for s in extra if s.id not in {p.id for p in packed}],documents,precision_aware=precise)
                probe['conflicts']=list(recheck.conflicts)
                if recheck.conflicts:decision=type(decision)('abstain',('conflicting_evidence',),recheck.missing_requirement_ids)
            trace.conflict_probe=probe
        if decision.action=='answer':
            result=execute_numeric(spec,coverage,packed)
            if result.status=='answered' and answerer is not None:result=generate(spec,packed,coverage,config,answerer,budget,trace,deadline)
            trace.answer=result;trace.decisions.append({'action':'answer' if result.status=='answered' else 'abstain','reason_codes':[result.reason or 'complete_evidence']});return
        if decision.action=='abstain':
            trace.answer=abstain(decision.reason_codes[0]);trace.decisions.append(asdict(decision));return
        action=decision.action;missing=list(decision.missing_requirement_ids)


def generate(spec,packed,coverage,config,answerer,budget,trace,deadline):
    reserve=config.get('generation_reservation_usd')
    if not config.get('provider_enabled',False) or budget.max_usd<=0 or reserve is None or reserve>budget.max_usd:return abstain('provider_budget_disabled')
    from evaluation.evidence_aware.ledger import reserve_call
    event=UsageEvent(f'{spec.id}:generation',spec.id,'generation',provider='injected_answerer',model_revision=config.get('model_revision','unknown'),input_tokens=None,output_tokens=None,estimated_usd=reserve)
    reserve_call(event,budget)
    before=perf_counter()
    try:
        # Contract deliberately excludes the private executor result; citations must be spans the gate audited.
        result=audit_answer(answerer.answer(spec,packed),spec,[s for s in packed if s.id in coverage.audited_span_ids])
        if result.status=='answered' and monotonic()>=deadline:result=abstain('deadline_exceeded')
    except Exception as e:
        event.status=type(e).__name__;result=AnswerRecord('error',reason=event.status)
    event.elapsed_ms=(perf_counter()-before)*1000
    trace.usage.append(asdict(event))
    return result
