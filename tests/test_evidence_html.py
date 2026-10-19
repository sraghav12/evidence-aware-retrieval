import builtins,hashlib,json
from pathlib import Path
import pytest
from pipelines.evidence_aware.html_source import normalize_filing,prepare_sources,EXTRACTOR_VERSION
from pipelines.evidence_aware.units import build_units
from pipelines.evidence_aware.extraction import extract_candidates
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.retrieval import BM25Backend

HTML=Path(__file__).parent/'fixtures/evidence_v2/html'
DEVICES=dict(doc_id='DEV_10K_2024',ticker='DEV',cik='101',accession_number='0000000101-24-000001',filing_date='2024-11-01',source_url='fixture://devices-2024')
RETAIL=dict(doc_id='RTL_10K_2025',ticker='RTL',cik='202',accession_number='0000000202-25-000001',filing_date='2025-03-20',source_url='fixture://retail-2025')


def raw(name):return (HTML/name).read_bytes()


def spans_of(result):
    d=result['document'];docs={d['doc_id']:d};return extract_candidates(build_units(docs),docs)


def by_fact(result):return {s['fact_id']:s for s in result['segments']}


def test_html_cell_links_row_period_and_units():
    data=raw('date_columns.html');result=normalize_filing(data,DEVICES);d=result['document']
    assert d['entity_id']=='cik:101' and d['raw_sha256']==hashlib.sha256(data).hexdigest() and d['extractor_version']==EXTRACTOR_VERSION
    assert d['fiscal_calendar']==[{'fiscal_year':2024,'period_start':'2023-10-01','period_end':'2024-09-28'}]
    spans={s.value:s for s in spans_of(result)}
    assert set(spans)=={'120500','100000'}
    s=spans['120500']
    assert (s.unit,s.period_start,s.period_end,s.fiscal_year,s.metric)==('USD_million','2023-10-01','2024-09-28',2024,'revenue')
    assert d['text'][s.start:s.end]==s.quote and 'Total net sales' in s.quote and 'September 28, 2024' in s.quote
    seg=by_fact(result)['f-11']
    assert seg['span_id']==s.id and seg['table_index']==0 and seg['row_index']==3 and seg['concept']=='us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    assert data[seg['raw_byte_start']:seg['raw_byte_end']].decode().endswith('120,500</ix:nonFraction>')
    docs={d['doc_id']:d};req=parse_query('What was Devices FY2024 revenue?','2025-01-01',{'devices':'cik:101'},build_fiscal_calendar(docs,'2025-01-01'))
    assert audit_coverage(req,list(spans.values()),docs).complete
    swapped=data.replace(b'September 28,<br/>2024',b'@A@').replace(b'September 30,<br/>2023',b'September 28,<br/>2024').replace(b'@A@',b'September 30,<br/>2023')
    bad=normalize_filing(swapped,DEVICES);bd=bad['document']
    assert spans_of(bad)==[] and {f['reason'] for f in bad['failures']}=={'period_header_mismatch'}
    assert not audit_coverage(req,[s],{bd['doc_id']:bd}).complete


def test_year_header_uses_fiscal_year_label_and_inside_caption_scale():
    result=normalize_filing(raw('year_columns.html'),RETAIL);s={x.value:x for x in spans_of(result)}
    assert set(s)=={'5250','5000'} and s['5250'].fiscal_year==2025 and s['5000'].fiscal_year==2024 and s['5250'].unit=='USD_thousand'
    assert s['5250'].period_end=='2025-01-31'


def test_ambiguous_merged_header_abstains():
    data=raw('year_columns.html').replace(b'<td colspan="3">2025</td><td colspan="3">2024</td>',b'<td colspan="6">2025</td>')
    result=normalize_filing(data,RETAIL)
    assert spans_of(result)==[] and {f['reason'] for f in result['failures']}=={'ambiguous_period_header'}


def test_unit_caption_must_agree_with_scale():
    result=normalize_filing(raw('year_columns.html').replace(b'in thousands',b'in millions'),RETAIL)
    assert spans_of(result)==[] and {f['reason'] for f in result['failures']}=={'unit_header_mismatch'}


def test_html_missing_fails_closed(tmp_path):
    data=raw('date_columns.html');(tmp_path/'DEV_10K_2024.html').write_bytes(data);(tmp_path/'RTL_10K_2025.html').write_bytes(raw('year_columns.html'))
    filings=[dict(DEVICES,raw_html_bytes=len(data)),dict(RETAIL,raw_html_bytes=1),dict(DEVICES,doc_id='DEV_10K_2023',raw_html_bytes=10)]
    out=prepare_sources(tmp_path,filings)
    status={m['doc_id']:m['status'] for m in out['manifest']['filings']}
    assert status=={'DEV_10K_2024':'prepared','RTL_10K_2025':'excluded:raw_size_mismatch','DEV_10K_2023':'missing:raw_html_missing'}
    assert [d['doc_id'] for d in out['documents']]==['DEV_10K_2024']
    nofocus=normalize_filing(data.replace(b'dei:DocumentFiscalYearFocus',b'dei:Other'),DEVICES)
    assert nofocus['document']['fiscal_calendar']==[] and spans_of(nofocus)==[] and 'missing_fiscal_year_focus' in {f['reason'] for f in nofocus['failures']}


def test_raw_to_normalized_lineage(tmp_path):
    data=raw('date_columns.html');a=normalize_filing(data,DEVICES);b=normalize_filing(data,DEVICES)
    assert a==b and a['document']['sha256']==hashlib.sha256(a['document']['text'].encode()).hexdigest()
    ids={s.id:s for s in spans_of(a)}
    assert {s['span_id'] for s in a['segments']}==set(ids)
    text=data.decode()
    for seg in a['segments']:
        s=ids[seg['span_id']]
        assert (seg['normalized_start'],seg['normalized_end'])==(s.start,s.end)
        assert text[seg['raw_char_start']:seg['raw_char_end']].encode()==data[seg['raw_byte_start']:seg['raw_byte_end']]
        assert f'id="{seg["fact_id"]}"' in text[seg['raw_char_start']:seg['raw_char_end']]
    (tmp_path/'DEV_10K_2024.html').write_bytes(data)
    out=prepare_sources(tmp_path,[dict(DEVICES,raw_html_bytes=len(data))],copy_dir=tmp_path/'copy')
    entry=out['manifest']['filings'][0]
    assert entry['raw_sha256']==hashlib.sha256(data).hexdigest() and entry['normalized_sha256']==a['document']['sha256']
    assert (tmp_path/'copy/DEV_10K_2024.html').read_bytes()==data and str(tmp_path) not in json.dumps(out['manifest'])


def earlier_devices_filing():
    data=raw('date_columns.html').decode();period='<xbrli:startDate>{}</xbrli:startDate><xbrli:endDate>{}</xbrli:endDate>'
    shifts=((period.format('2023-10-01','2024-09-28'),period.format('2022-09-25','2023-09-30')),(period.format('2022-09-25','2023-09-30'),period.format('2021-09-26','2022-09-24')),
            ('September 28,<br/>2024','September 30,<br/>2023'),('September 30,<br/>2023','September 24,<br/>2022'),('>2024</ix:nonNumeric>','>2023</ix:nonNumeric>'),('>120,500<','>98,000<'))
    for i,(old,_) in enumerate(shifts):data=data.replace(old,f'@{i}@')
    for i,(_,new) in enumerate(shifts):data=data.replace(f'@{i}@',new)
    return data.encode()


def test_reported_restated_conflict():
    old=normalize_filing(earlier_devices_filing(),dict(DEVICES,doc_id='DEV_10K_2023',accession_number='0000000101-23-000001',filing_date='2023-11-03'))
    assert {(s.fiscal_year,s.value) for s in spans_of(old)}=={(2023,'98000'),(2022,'100000')}
    new=normalize_filing(raw('date_columns.html'),DEVICES)
    docs={x['document']['doc_id']:x['document'] for x in (old,new)}
    bs={s:BM25Backend(docs,s) for s in ('cheap_search','section_search','expanded_search')}
    def ask(as_of):
        q=parse_query('What was Devices FY2023 revenue?',as_of,{'devices':'cik:101'},build_fiscal_calendar(docs,as_of))
        return run_spec(q,bs,docs,{})
    before=ask('2024-06-30');after=ask('2025-01-01')
    assert before.answer.status=='answered' and before.answer.value=='98000'
    assert after.answer.status=='abstained' and after.answer.reason=='conflicting_evidence'


def test_no_reference_needed_for_extraction(tmp_path,monkeypatch):
    data=raw('date_columns.html');(tmp_path/'DEV_10K_2024.html').write_bytes(data)
    original=builtins.open
    def guarded(file,*args,**kwargs):
        if any(x in str(file) for x in ('references','gold_answers','queries')):raise AssertionError('reference access')
        return original(file,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',guarded)
    out=prepare_sources(tmp_path,[dict(DEVICES,raw_html_bytes=len(data))])
    assert out['manifest']['filings'][0]['revenue_spans']==2
