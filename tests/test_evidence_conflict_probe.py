import hashlib
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.retrieval import BM25Backend

HDR='metric | unit | period_start | period_end | fiscal_year | accounting_basis | value'
CAL={2023:dict(fiscal_year=2023,period_start='2023-01-01',period_end='2023-12-31'),2024:dict(fiscal_year=2024,period_start='2024-01-01',period_end='2024-12-31')}
V3={'gate':'audit_coverage_v3','probe_units_per_filing':3,'probe_tokens':2048,'cheap_context_tokens':40,'max_packed_sections':1}


def doc(doc_id,entity,rows,disclosed,focus):
    text=f'SECTION income statement\n{HDR}\n'+''.join(f'revenue | USD_million | {y}-01-01 | {y}-12-31 | {y} | reported | {v}\n' for y,v in rows)
    return dict(doc_id=doc_id,entity_id=f'synthetic:{entity}',accession=f'acc-{doc_id}',disclosed_at=disclosed,fiscal_calendar=[CAL[focus]],source_url=f'fixture://{doc_id}',text=text,sha256=hashlib.sha256(text.encode()).hexdigest())


def ask(docs,as_of,config,year=2023,entity='alpha',max_units=1):
    q=parse_query(f'What was {entity} FY{year} revenue?',as_of,{d['entity_id'].split(':')[-1]:d['entity_id'] for d in docs.values()},build_fiscal_calendar(docs,as_of))
    bs={s:BM25Backend(docs,s,max_units=max_units) for s in ('cheap_search','section_search','expanded_search')}
    return run_spec(q,bs,docs,config)


def corpus(old='120',later='100',later_disclosed='2025-02-10'):
    d=[doc('a23','alpha',[(2023,old)],'2024-02-10',2023),doc('a24','alpha',[(2024,'130'),(2023,later)],later_disclosed,2024),doc('b24','beta',[(2023,'999'),(2024,'998')],'2025-02-11',2024)]
    return {x['doc_id']:x for x in d}


def test_probe_finds_restatement_in_later_filing():
    docs=corpus()
    v2=ask(docs,'2025-06-30',{'cheap_context_tokens':40,'max_packed_sections':1})
    assert v2.answer.status=='answered' and v2.answer.value=='120' and v2.packing[-1]['packed_unit_ids']==['a23::0']
    v3=ask(docs,'2025-06-30',V3)
    assert v3.answer.status=='abstained' and v3.answer.reason=='conflicting_evidence'
    assert v3.conflict_probe['status']=='ran' and v3.conflict_probe['probed_doc_ids']==['a24'] and v3.conflict_probe['conflicts']==['synthetic:alpha:revenue:2023']


def test_probe_ignores_filings_after_cutoff_and_other_entities():
    t=ask(corpus(later_disclosed='2025-09-01'),'2025-06-30',V3)
    assert t.answer.status=='answered' and t.answer.value=='120' and t.conflict_probe['status']=='no_later_filings' and t.conflict_probe['probed_doc_ids']==[]


def test_probe_cost_is_bounded_charged_and_skips_visibly():
    t=ask(corpus(),'2025-06-30',V3)
    events=[e for e in t.usage if e['stage']=='conflict_probe']
    assert len(events)==1 and 0<events[0]['input_tokens']<=V3['probe_tokens']==t.conflict_probe['budget_tokens']
    skipped=ask(corpus(),'2025-06-30',dict(V3,probe_tokens=0))
    assert skipped.answer.status=='answered' and skipped.conflict_probe['status']=='skipped_budget'


def test_gate_v3_treats_displayed_precision_differences_as_compatible():
    v3=ask(corpus(old='34124.1',later='34124'),'2025-06-30',V3)
    assert v3.answer.status=='answered' and v3.answer.value=='34124.1' and v3.conflict_probe['conflicts']==[]
    assert ask(corpus(old='34124.1',later='34125'),'2025-06-30',V3).answer.reason=='conflicting_evidence'
    v2=ask(corpus(old='34124.1',later='34124'),'2025-06-30',{'max_packed_sections':12},max_units=12)
    assert v2.answer.reason=='conflicting_evidence'


def test_gate_v2_has_no_probe():
    t=ask(corpus(),'2025-06-30',{'cheap_context_tokens':40,'max_packed_sections':1})
    assert t.conflict_probe is None and not any(e['stage']=='conflict_probe' for e in t.usage)


def test_probe_never_exceeds_a_small_cap():
    t=ask(corpus(),'2025-06-30',dict(V3,probe_tokens=5))
    assert t.conflict_probe['status']=='ran_truncated' and t.conflict_probe['inspected_tokens']<=5 and t.answer.status=='answered'


from pipelines.evidence_aware.engine import conflict_probe
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.units import build_units
from pipelines.evidence_aware.extraction import extract_candidates
from pipelines.evidence_aware.contracts import BudgetState


def sections_doc(doc_id,sections,disclosed,focus):
    text=''.join(f'SECTION {name}\n{HDR}\n'+''.join(f'revenue | USD_million | {y}-01-01 | {y}-12-31 | {y} | reported | {v}\n' for y,v in rows) for name,rows in sections)
    return dict(doc_id=doc_id,entity_id='synthetic:alpha',accession='acc-'+doc_id,disclosed_at=disclosed,fiscal_calendar=[CAL[focus]],source_url='x',text=text,sha256=hashlib.sha256(text.encode()).hexdigest())


def probe(docs,packed_unit_ids,gate,as_of='2025-06-30'):
    q=parse_query('What was alpha FY2023 revenue?',as_of,{'alpha':'synthetic:alpha'},build_fiscal_calendar(docs,as_of))
    units={u.id:u for u in build_units(docs)};packed=extract_candidates([units[i] for i in packed_unit_ids],docs)
    mode='pairwise' if gate=='audit_coverage_v4' else 'group'
    cov=audit_coverage(q,packed,docs,precision_aware=mode)
    record,extra=conflict_probe(q,cov,packed,docs,{'gate':gate,'probe_tokens':2048,'probe_units_per_filing':3},BudgetState())
    return record,audit_coverage(q,packed+[s for s in extra if s.id not in {p.id for p in packed}],docs,precision_aware=mode)


HIGHLIGHTS={x['doc_id']:x for x in [sections_doc('a23',[('income',[(2023,'120')])],'2024-02-10',2023),sections_doc('a24',[('highlights',[(2024,'130')]),('income',[(2024,'130'),(2023,'100')])],'2025-02-10',2024)]}


def test_v4_probes_a_filing_whose_other_unit_was_packed():
    v3,_=probe(HIGHLIGHTS,['a23::0','a24::0'],'audit_coverage_v3')
    assert v3['status']=='no_later_filings'
    v4,recheck=probe(HIGHLIGHTS,['a23::0','a24::0'],'audit_coverage_v4')
    assert v4['status']=='ran' and v4['probed_doc_ids']==['a24'] and recheck.conflicts==('synthetic:alpha:revenue:2023',)


def test_v4_probes_the_earlier_original_when_only_the_restated_value_is_packed():
    v4,recheck=probe(HIGHLIGHTS,['a24::1'],'audit_coverage_v4')
    assert v4['probed_doc_ids']==['a23'] and recheck.conflicts==('synthetic:alpha:revenue:2023',)


def test_v4_reports_when_every_other_filing_already_supplied_the_quantity():
    v4,recheck=probe(HIGHLIGHTS,['a23::0','a24::1'],'audit_coverage_v4')
    assert v4['status']=='other_filings_already_packed' and v4['probed_doc_ids']==[] and recheck.conflicts==('synthetic:alpha:revenue:2023',)
    alone={'a23':HIGHLIGHTS['a23']}
    assert probe(alone,['a23::0'],'audit_coverage_v4')[0]['status']=='no_other_filings'


def test_v4_compares_precision_pairwise():
    def values(*vals):
        docs={f'd{i}':sections_doc(f'd{i}',[('income',[(2023,v)])],f'2024-0{i+1}-10',2023) for i,v in enumerate(vals)}
        q=parse_query('What was alpha FY2023 revenue?','2025-06-30',{'alpha':'synthetic:alpha'},build_fiscal_calendar(docs,'2025-06-30'))
        return audit_coverage(q,extract_candidates(build_units(docs),docs),docs,precision_aware='pairwise')
    assert values('34124.1','34124').complete and values('34125.5','34126').complete and values('34124.5','34125').complete
    assert values('100','99.6','100.45').conflicts and values('34124.1','34125').conflicts


def test_v4_end_to_end_abstains_on_restatement_and_keeps_answers():
    v4=dict(V3,gate='audit_coverage_v4')
    assert ask(corpus(),'2025-06-30',v4).answer.reason=='conflicting_evidence'
    ok=ask(corpus(later='120'),'2025-06-30',v4)
    assert ok.answer.status=='answered' and ok.answer.value=='120' and ok.conflict_probe['status'] in ('ran','other_filings_already_packed')
