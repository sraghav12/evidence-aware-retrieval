"""Conservative inline-XBRL table extraction from raw SEC HTML; unsupported layouts fail closed."""
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import hashlib,re
from .extraction import HTML_HEADERS

EXTRACTOR_VERSION='html_ixbrl_tables_v1'
REVENUE_CONCEPTS={'us-gaap:Revenues','us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax','us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax','us-gaap:SalesRevenueNet'}
NUMBER_FORMATS={'ixt:num-dot-decimal','ixt:numdotdecimal'}
UNITS={'0':'USD','3':'USD_thousand','6':'USD_million','9':'USD_billion'}
SCALE_WORDS={'thousands':'3','millions':'6','billions':'9'}
MONTHS={m:i for i,m in enumerate(('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'),1)}
DATE=re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b',re.I)
YEAR=re.compile(r'(?:fiscal\s+(?:year\s+)?)?((?:19|20)\d{2})',re.I)
CAPTION=re.compile(r'\bin (thousands|millions|billions)\b',re.I)
REVENUE_LABEL=re.compile(r'revenue|sales',re.I)
NOT_REVENUE_LABEL=re.compile(r'cost|expense|per share|%|percent',re.I)


def clean(text):return ' '.join(text.replace('|','/').split())


class _Parser(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True)
        self.text=text;self.line_starts=[0]+[m.end() for m in re.finditer('\n',text)]
        self.contexts={};self.context=None;self.field=None;self.focus=None;self.nonnumeric=None
        self.tables=[];self.open=[];self.facts=[];self.outside=[]

    def pos(self):
        line,col=self.getpos();return self.line_starts[line-1]+col

    def cell(self):
        t=self.open[-1] if self.open else None
        return t['rows'][-1][-1] if t and t['rows'] and t['rows'][-1] else None

    def handle_starttag(self,tag,attrs):
        a=dict(attrs);local=tag.split(':')[-1]
        if tag=='table':
            self.open.append({'index':len(self.tables),'rows':[],'rowspan':False,'pre':clean(''.join(self.outside)[-400:])});self.tables.append(self.open[-1])
        elif tag=='tr' and self.open:self.open[-1]['rows'].append([])
        elif tag in ('td','th') and self.open:
            t=self.open[-1]
            if not t['rows']:t['rows'].append([])
            try:span=max(1,int(a.get('colspan') or 1))
            except ValueError:span=1
            if (a.get('rowspan') or '1').strip()!='1':t['rowspan']=True
            t['rows'][-1].append({'text':[],'colspan':span,'facts':[]})
        elif tag=='br':self.handle_data(' ')
        elif tag=='ix:nonfraction':
            self.facts.append({'attrs':a,'start':self.pos(),'text':[],'cell':self.cell(),'table':self.open[-1] if self.open else None})
        elif tag=='ix:nonnumeric' and a.get('name')=='dei:DocumentFiscalYearFocus':self.nonnumeric={'context':a.get('contextref'),'text':[]}
        elif tag=='xbrli:context' or (local=='context' and ':' in tag):self.context={'id':a.get('id'),'identifier':'','dimensional':False,'startdate':'','enddate':'','instant':''}
        elif self.context is not None:
            if local in ('segment','scenario'):self.context['dimensional']=True
            elif local in ('identifier','startdate','enddate','instant'):self.field=local

    def handle_endtag(self,tag):
        local=tag.split(':')[-1]
        if tag=='table' and self.open:self.open.pop()
        elif tag=='ix:nonfraction':
            fact=next((f for f in reversed(self.facts) if 'end' not in f),None)
            if fact:
                start=self.pos();close=self.text.find('>',start)
                fact['end']=close+1 if close>=0 else start
                if fact['cell'] is not None:fact['cell']['facts'].append(fact)
        elif tag=='ix:nonnumeric' and self.nonnumeric is not None:
            self.focus=(clean(''.join(self.nonnumeric['text'])),self.nonnumeric['context']);self.nonnumeric=None
        elif self.context is not None:
            if local=='context':self.contexts[self.context['id']]=self.context;self.context=None
            elif local==self.field:self.field=None

    def handle_data(self,data):
        if self.context is not None and self.field:self.context[self.field]+=data.strip();return
        if self.nonnumeric is not None:self.nonnumeric['text'].append(data)
        for f in self.facts[-3:]:
            if 'end' not in f:f['text'].append(data)
        cell=self.cell()
        if cell is not None:cell['text'].append(data)
        elif not self.open:
            self.outside.append(data)
            if len(self.outside)>200:self.outside=self.outside[-100:]


def header_period(text):
    dates=DATE.findall(text)
    if len(dates)>1:return ('multiple',None)
    if dates:
        month,day,year=dates[0]
        try:return ('date',date(int(year),MONTHS[month[:3].casefold()],int(day)).isoformat())
        except ValueError:return ('multiple',None)
    year=YEAR.fullmatch(text)
    return ('year',int(year.group(1))) if year else None


def annual_year(focus_year,focus_end,start,end):
    if not 350<=(end-start).days<=380:return None,'non_annual_period'
    gap=(focus_end-end).days;k=round(gap/365.25)
    if k<0 or k>4 or abs(gap-k*365.25)>20:return None,'unaligned_fiscal_period'
    return focus_year-k,None


def ctx_period(c):
    return (c['startdate'],c['enddate']) if c['startdate'] and c['enddate'] else (c['instant'],c['instant'])


def normalize_filing(raw,meta):
    text=raw.decode('utf-8');p=_Parser(text);p.feed(text);p.close()
    doc_id=meta['doc_id'];cik=int(meta['cik']);failures=[];stats=Counter()
    calendar=[];focus_year=focus_end=None
    focus=p.focus;fc=p.contexts.get(focus[1]) if focus else None
    if focus and fc and re.fullmatch(r'\d{4}',focus[0]) and fc['startdate'] and fc['enddate'] and 350<=(date.fromisoformat(fc['enddate'])-date.fromisoformat(fc['startdate'])).days<=380:
        focus_year=int(focus[0]);focus_end=date.fromisoformat(fc['enddate'])
        calendar=[{'fiscal_year':focus_year,'period_start':fc['startdate'],'period_end':fc['enddate']}]
    else:failures.append({'doc_id':doc_id,'fact_id':None,'table_index':None,'row_index':None,'reason':'missing_fiscal_year_focus'})
    parts=[];segments=[];offset=0
    def emit(line):
        nonlocal offset
        parts.append(line+'\n');start=offset;offset+=len(line)+1;return start
    for table in p.tables:
        rows=[];data_start=None
        for ri,row in enumerate(table['rows']):
            col=0;cells=[]
            for ci,c in enumerate(row):
                cells.append({'index':ci,'lo':col,'hi':col+c['colspan'],'text':clean(''.join(c['text'])),'facts':c['facts']});col+=c['colspan']
            rows.append(cells)
            if data_start is None and any(c['facts'] for c in cells):data_start=ri
        if data_start is None:continue
        headers=[]
        for row in rows[:data_start]:
            for c in row:
                period=header_period(c['text'])
                if period:headers.append(dict(c,period=period,covers=set()))
        for row in rows[data_start:]:
            for c in row:
                for f in c['facts']:
                    ctx=p.contexts.get(f['attrs'].get('contextref'))
                    if ctx is None:continue
                    for h in headers:
                        if h['lo']<c['hi'] and c['lo']<h['hi']:h['covers'].add(ctx_period(ctx))
        header_text=clean(' '.join(c['text'] for row in rows[:data_start] for c in row))
        caption_match=CAPTION.search(header_text) or CAPTION.search(table['pre'][-200:])
        caption=clean(table['pre'][-160:]+' '+header_text[:200])
        accepted=[]
        for ri,row in enumerate(rows[data_start:],data_start):
            for c in row:
                for f in c['facts']:
                    a=f['attrs']
                    if a.get('name') not in REVENUE_CONCEPTS:continue
                    ctx=p.contexts.get(a.get('contextref'))
                    if ctx is not None and ctx['dimensional']:stats['dimensional_skipped']+=1;continue
                    stats['revenue_candidates']+=1
                    value=clean(''.join(f['text'])).replace(',','')
                    def fail(reason):failures.append({'doc_id':doc_id,'fact_id':a.get('id'),'table_index':table['index'],'row_index':ri,'reason':reason})
                    if ctx is None:fail('unknown_context');continue
                    if focus_year is None:fail('missing_fiscal_year_focus');continue
                    if not re.fullmatch(r'\d+',ctx['identifier']) or int(ctx['identifier'])!=cik:fail('entity_mismatch');continue
                    if (a.get('unitref') or '').casefold()!='usd':fail('unsupported_unit');continue
                    if a.get('format') not in NUMBER_FORMATS or not re.fullmatch(r'\d+(\.\d+)?',value):fail('unsupported_number_format');continue
                    scale=a.get('scale') or '0'
                    if scale not in UNITS:fail('unsupported_scale');continue
                    if not (ctx['startdate'] and ctx['enddate']):fail('non_annual_period');continue
                    year,reason=annual_year(focus_year,focus_end,date.fromisoformat(ctx['startdate']),date.fromisoformat(ctx['enddate']))
                    if reason:fail(reason);continue
                    if table['rowspan']:fail('unsupported_rowspan');continue
                    label=next((x['text'] for x in row if x['hi']<=c['lo'] and x['text'] and x['text']!='$'),'')
                    if not REVENUE_LABEL.search(label) or NOT_REVENUE_LABEL.search(label):fail('row_label_not_revenue');continue
                    covering=[h for h in headers if h['lo']<c['hi'] and c['lo']<h['hi']]
                    if not covering:fail('missing_period_header');continue
                    if len({h['period'] for h in covering})>1 or any(h['period'][0]=='multiple' or len(h['covers'])>1 for h in covering):fail('ambiguous_period_header');continue
                    kind,expected=covering[0]['period']
                    if (kind=='date' and expected!=ctx['enddate']) or (kind=='year' and expected!=year):fail('period_header_mismatch');continue
                    if not caption_match:fail('missing_unit_header');continue
                    if SCALE_WORDS[caption_match.group(1).casefold()]!=scale:fail('unit_header_mismatch');continue
                    if a.get('sign')=='-':value='-'+value
                    accepted.append((ri,c,f,ctx,year,value,UNITS[scale],label,covering[0]['text']))
        emit(f'SECTION table {table["index"]} | {caption}')
        emit(' | '.join(HTML_HEADERS))
        for ri,c,f,ctx,year,value,unit,label,column in accepted:
            line=' | '.join(['revenue',unit,ctx['startdate'],ctx['enddate'],str(year),'reported',value,label,column,f't{table["index"]}.r{ri}.c{c["index"]}'])
            start=emit(line);a=f['attrs']
            segments.append({'span_id':f'{doc_id}:{start}','doc_id':doc_id,'normalized_start':start,'normalized_end':start+len(line),'table_index':table['index'],'row_index':ri,'cell_index':c['index'],'grid_column':c['lo'],
                             'fact_id':a.get('id'),'context_id':a.get('contextref'),'concept':a.get('name'),'scale':a.get('scale') or '0','raw_value_text':clean(''.join(f['text'])),'row_label':label,'column_header':column,
                             'raw_char_start':f['start'],'raw_char_end':f['end'],'raw_byte_start':len(text[:f['start']].encode()),'raw_byte_end':len(text[:f['end']].encode())})
        for row in rows:
            display=' | '.join(c['text'] for c in row if c['text'])
            if display:emit('row | '+display)
        stats['tables_with_facts']+=1
    normalized=''.join(parts)
    document={'doc_id':doc_id,'accession':meta['accession_number'],'cik':str(cik),'ticker':meta.get('ticker'),'entity_id':f'cik:{cik}','disclosed_at':meta['filing_date'],'fiscal_calendar':calendar,
              'source_url':meta['source_url'],'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),'extractor_version':EXTRACTOR_VERSION,'sha256':hashlib.sha256(normalized.encode()).hexdigest(),'text':normalized}
    stats['revenue_spans']=len(segments)
    return {'document':document,'segments':segments,'failures':failures,'stats':dict(stats)}


def prepare_sources(raw_dir,filings,copy_dir=None):
    documents=[];segments=[];failures=[];entries=[]
    for f in filings:
        path=Path(raw_dir)/f'{f["doc_id"]}.html'
        entry={k:f.get(k) for k in ('doc_id','ticker','cik','accession_number','filing_date')};entry['raw_file']=path.name;entries.append(entry)
        if not path.is_file():entry['status']='missing:raw_html_missing';continue
        data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();entry.update(raw_bytes=len(data),raw_sha256=sha)
        if len(data)!=f['raw_html_bytes']:entry['status']='excluded:raw_size_mismatch';continue
        if f.get('raw_sha256') not in (None,sha):entry['status']='excluded:raw_hash_mismatch';continue
        try:result=normalize_filing(data,f)
        except UnicodeDecodeError:entry['status']='excluded:undecodable_html';continue
        if copy_dir is not None:
            target=Path(copy_dir)/path.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            if hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('copied raw HTML hash mismatch')
        d=result['document']
        entry.update(status='prepared',normalized_sha256=d['sha256'],extractor_version=EXTRACTOR_VERSION,fiscal_year_focus=d['fiscal_calendar'][0]['fiscal_year'] if d['fiscal_calendar'] else None,
                     tables_with_facts=result['stats'].get('tables_with_facts',0),revenue_candidates=result['stats'].get('revenue_candidates',0),revenue_spans=result['stats']['revenue_spans'],
                     dimensional_skipped=result['stats'].get('dimensional_skipped',0),rejected=dict(sorted(Counter(x['reason'] for x in result['failures']).items())))
        documents.append(d);segments.extend(result['segments']);failures.extend(result['failures'])
    counts=Counter(e['status'] for e in entries)
    manifest={'schema_version':2,'extractor_version':EXTRACTOR_VERSION,'parser':'python_stdlib_html.parser','filings':entries,'status_counts':dict(sorted(counts.items())),
              'revenue_spans':sum(e.get('revenue_spans',0) for e in entries),'rejected':dict(sorted(Counter(x['reason'] for x in failures).items()))}
    return {'documents':documents,'segments':segments,'failures':failures,'manifest':manifest}
