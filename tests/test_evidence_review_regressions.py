"""Regressions for the fresh whole-branch review of Tasks 1-7."""
from dataclasses import asdict,replace
import hashlib,json,time
from pathlib import Path
import pytest
from evidence_helpers import documents,spec,spans
from pipelines.evidence_aware import engine
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.contracts import AnswerRecord
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.extraction import extract_candidates
from pipelines.evidence_aware.parser import parse_query
from pipelines.evidence_aware.retrieval import BM25Backend
from pipelines.evidence_aware.units import build_units
from evaluation.evidence_aware.report import score_answers,build_report
from evaluation.evidence_aware.runner import run,read_jsonl

HDR='metric | unit | period_start | period_end | fiscal_year | accounting_basis | value'
CAL=[dict(fiscal_year=2023,period_start='2023-01-01',period_end='2023-12-31'),dict(fiscal_year=2024,period_start='2024-01-01',period_end='2024-12-31')]
FIXTURES=Path(__file__).parent/'fixtures/evidence_v2'
PROVIDER={'provider_enabled':True,'max_usd':1,'generation_reservation_usd':.01}


def doc(doc_id,entity,text,disclosed='2025-02-14'):
    return dict(doc_id=doc_id,entity_id=f'synthetic:{entity}',accession=f'acc-{doc_id}',disclosed_at=disclosed,fiscal_calendar=CAL,source_url=f'fixture://{doc_id}',text=text,sha256=hashlib.sha256(text.encode()).hexdigest())


def store(*docs):return {d['doc_id']:d for d in docs}


def ask(question,docs,as_of='2025-03-01'):
    return parse_query(question,as_of,{d['entity_id'].split(':')[-1]:d['entity_id'] for d in docs.values()},build_fiscal_calendar(docs,as_of))


def backends(docs,**kw):return {s:BM25Backend(docs,s,**kw) for s in ('cheap_search','section_search','expanded_search')}


def row(value,basis='reported',year=2024):return f'revenue | USD_million | {year}-01-01 | {year}-12-31 | {year} | {basis} | {value}'


def test_supported_success_requires_reference_evidence():
    d=documents();t=asdict(run_spec(spec('What was Gamma FY2024 revenue?'),backends(d),d,{}));t['query_id']='complete_extraction'
    refs={r['query_id']:r for r in read_jsonl(FIXTURES/'references.jsonl')}
    assert t['answer']['value']==refs['complete_extraction']['value']
    assert score_answers([t],refs,d)[0]['supported_correct'] is False


def test_supported_success_requires_reference_requirements():
    d=documents();t=asdict(run_spec(spec(),backends(d),d,{}))
    ref={'answerable':True,'value':'120','unit':'USD_million','requirements':['synthetic:gamma:revenue:2024']}
    assert score_answers([t],{t['query_id']:ref},d)[0]['supported_correct'] is False
    ref['requirements']=['synthetic:alpha:revenue:2024']
    assert score_answers([t],{t['query_id']:ref},d)[0]['supported_correct'] is True


def test_header_scope_resets_between_tables():
    d=store(doc('b','alpha',f'SECTION income\n{HDR}\n{row(100,year=2023)}\n\nmetric | unit | period_start | period_end | fiscal_year | accounting_basis | pro_forma_value\n{row(150)}\n'))
    assert [s.value for s in extract_candidates(build_units(d),d)]==['100']


def test_saturated_cheap_stage_does_not_block_escalated_evidence():
    filler='\n'.join(f'note line {i} filler words here' for i in range(30))
    d=store(doc('ov','beta','SECTION overview\nBeta revenue discussion revenue revenue.\n'),doc('ov2','beta','SECTION overview two\nMore Beta revenue narrative revenue.\n'),
            doc('inc','beta',f'SECTION income statement\n{filler}\n{HDR}\n{row(220)}\n'))
    t=run_spec(ask('What was beta FY2024 revenue?',d),backends(d,max_units=2),d,{'max_packed_sections':2,'cheap_context_tokens':30})
    assert t.answer.status=='answered' and t.answer.value=='220'
    assert [p['stage'] for p in t.packing]==['cheap_search','section_search'] and t.packing[0]['omitted_unit_ids']==[]


def test_escalation_excludes_already_inspected_units():
    d=documents();t=run_spec(spec('What was Mention FY2024 revenue?'),backends(d),d,{})
    stages={s['stage']:set(s['ids']) for s in t.selected_units}
    assert not stages['expanded_search'] & (stages['cheap_search']|stages['section_search'])


def test_restated_value_conflicts_with_reported():
    d=store(doc('a24','alpha',f'SECTION income\n{HDR}\n{row(120)}\n','2025-01-10'),doc('a25','alpha',f'SECTION income\n{HDR}\n{row(125,"restated")}\n','2025-02-20'))
    q=ask('What was alpha FY2024 revenue?',d);c=audit_coverage(q,extract_candidates(build_units(d),d),d)
    assert c.conflicts==(q.requirements[0].id,) and not c.complete
    same=store(d['a24'],doc('a25','alpha',f'SECTION income\n{HDR}\n{row(120,"restated")}\n','2025-02-20'))
    assert audit_coverage(q,extract_candidates(build_units(same),same),same).complete


def test_retrieval_excludes_documents_after_cutoff():
    d=store(doc('ok','alpha',f'SECTION income\n{HDR}\n{row(120)}\n'),doc('future','alpha',f'SECTION income\n{HDR}\n{row(130)}\n','2025-06-01'))
    seen=[]
    class Recorder:
        def answer(self,q,ss):
            seen.extend(s.doc_id for s in ss);return AnswerRecord('answered','120','USD_million',{q.requirements[0].id:[ss[0].id]})
    t=run_spec(ask('What was alpha FY2024 revenue?',d),backends(d),d,PROVIDER,Recorder())
    assert seen==['ok'] and all(i.startswith('ok') for s in t.selected_units for i in s['ids'])


def test_answer_audit_rejects_span_the_gate_did_not_audit():
    d=documents();real=next(s for s in spans() if s.entity_id=='synthetic:alpha');forged=replace(real,id='forged',value='999')
    class Forged:
        def retrieve(self,spec,missing,limit,exclude_unit_ids=()):self.selected=[];self.inspected_tokens=0;return [real,forged]
    class Cites:
        def answer(self,q,ss):return AnswerRecord('answered','999','USD_million',{q.requirements[0].id:['forged']})
    t=run_spec(spec(),{s:Forged() for s in ('cheap_search','section_search','expanded_search')},d,PROVIDER,Cites())
    assert t.answer.status=='abstained' and t.answer.reason=='answer_audit_failed'


def test_answer_after_deadline_abstains():
    d=documents()
    class Slow:
        def answer(self,q,ss):
            time.sleep(.2);return AnswerRecord('answered','120','USD_million',{q.requirements[0].id:[ss[0].id]})
    t=run_spec(spec(),backends(d),d,dict(PROVIDER,deadline_ms=100),Slow())
    assert t.answer.status=='abstained' and t.answer.reason=='deadline_exceeded'


def test_stage_exception_retains_partial_trace():
    d=documents();bs=backends(d)
    class Broken:
        def retrieve(self,*a,**k):raise RuntimeError('backend down')
    bs['section_search']=Broken();t=run_spec(spec('What was Mention FY2024 revenue?'),bs,d,{})
    assert t.answer.status=='error' and t.answer.reason=='RuntimeError'
    assert [x['action'] for x in t.decisions][:1]==['cheap_search'] and t.usage and t.selected_units


def test_coverage_rejects_span_disclosed_after_cutoff():
    assert not audit_coverage(replace(spec(),as_of='2025-01-01'),spans(),documents()).complete


def test_deadline_after_audit_abstains(monkeypatch):
    clock=iter([0,0]+[1000]*20);monkeypatch.setattr(engine,'monotonic',lambda:next(clock))
    d=documents();t=run_spec(spec(),backends(d),d,{})
    assert t.answer.status=='abstained' and t.answer.reason=='budget_exhausted'


def test_verification_allowance_is_charged():
    d=documents();q=spec('What was Mention FY2024 revenue?');first=run_spec(q,backends(d),d,{})
    used=next(e['input_tokens'] for e in first.usage if e['stage']=='verification')
    t=run_spec(q,backends(d),d,{'verification_tokens_total':used})
    assert [x['action'] for x in t.decisions]==['cheap_search','abstain'] and t.answer.reason=='budget_exhausted'


@pytest.fixture
def offline_run(tmp_path):
    return run({'documents':str(FIXTURES/'documents.jsonl'),'queries':str(FIXTURES/'queries.jsonl'),'output':str(tmp_path/'run'),'provider_enabled':False,'max_usd':0,'cheap_context_tokens':64})


REFS=str(FIXTURES/'references.jsonl')


def test_report_rejects_tampered_traces(offline_run):
    p=offline_run/'traces.jsonl';p.write_text(p.read_text().replace('answered','abstained',1))
    with pytest.raises(ValueError,match='trace checksum'):build_report(offline_run,REFS)


def test_report_rejects_missing_rows(offline_run):
    p=offline_run/'traces.jsonl';lines=p.read_bytes().splitlines(keepends=True)[1:];p.write_bytes(b''.join(lines))
    m=json.loads((offline_run/'manifest.json').read_text());m['traces_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(offline_run/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='missing query rows'):build_report(offline_run,REFS)


def test_report_rejects_config_drift(offline_run):
    c=json.loads((offline_run/'config.json').read_text());c['max_context_tokens']=4096;(offline_run/'config.json').write_text(json.dumps(c))
    with pytest.raises(ValueError,match='config hash'):build_report(offline_run,REFS)


def test_report_rejects_corpus_drift(offline_run,tmp_path):
    docs=[d for d in read_jsonl(FIXTURES/'documents.jsonl') if d['doc_id']!='gamma_income'];path=tmp_path/'docs.jsonl'
    path.write_text(''.join(json.dumps(d)+'\n' for d in docs))
    c=json.loads((offline_run/'config.json').read_text());c['documents']=str(path);(offline_run/'config.json').write_text(json.dumps(c))
    m=json.loads((offline_run/'manifest.json').read_text());m['config_hash']=engine.digest(c);(offline_run/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='corpus hash'):build_report(offline_run,REFS)


def test_report_rejects_incomplete_run(offline_run):
    (offline_run/'status.json').write_text(json.dumps({'complete':False}))
    with pytest.raises(ValueError,match='incomplete run'):build_report(offline_run,REFS)


def test_report_requires_reference_for_every_question(offline_run,tmp_path):
    refs=read_jsonl(REFS)+[{'query_id':'extra','answerable':True,'value':'1','unit':'USD_million'}];path=tmp_path/'refs.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in refs))
    with pytest.raises(ValueError,match='question set'):build_report(offline_run,str(path))


def test_unpriced_compute_has_null_cost_per_correct(offline_run):
    s=build_report(offline_run,REFS)['summary']
    assert s['supported_success']>0 and s['cost_per_correct_usd'] is None
