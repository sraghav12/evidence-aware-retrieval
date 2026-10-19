"""Reference-side reader of raw inline-XBRL facts. Deliberately shares no code with inference extraction:
no tables, headers, captions or row labels, only facts and dimensionless contexts."""
import html,re

REVENUE_CONCEPTS={'us-gaap:Revenues','us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax','us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax','us-gaap:SalesRevenueNet'}
CONTEXT=re.compile(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>',re.S)
FACT=re.compile(r'<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>',re.S)
FOCUS=re.compile(r'<ix:nonNumeric([^>]*name="dei:DocumentFiscalYearFocus"[^>]*)>(.*?)</ix:nonNumeric>',re.S)


def attrs(text):return dict(re.findall(r'([\w:-]+)="([^"]*)"',text))


def contexts(text):
    out={}
    for m in CONTEXT.finditer(text):
        body=m.group(2);start=re.search(r'<xbrli:startDate>([^<]+)',body);end=re.search(r'<xbrli:endDate>([^<]+)',body);cik=re.search(r'<xbrli:identifier[^>]*>(\d+)',body)
        if start and end and cik and 'segment' not in body and 'scenario' not in body:out[m.group(1)]=(start.group(1).strip(),end.group(1).strip(),int(cik.group(1)))
    return out


def revenue_facts(raw):
    text=raw.decode('utf-8');ctx=contexts(text);facts=[]
    for m in FACT.finditer(text):
        a=attrs(m.group(1))
        if a.get('name') not in REVENUE_CONCEPTS or a.get('contextRef') not in ctx:continue
        value=re.sub(r'<[^>]+>','',html.unescape(m.group(2))).strip().replace(',','')
        if not re.fullmatch(r'\d+(\.\d+)?',value):continue
        start,end,cik=ctx[a['contextRef']]
        facts.append({'concept':a['name'],'value':('-' if a.get('sign')=='-' else '')+value,'scale':a.get('scale','0'),'decimals':a.get('decimals'),'period_start':start,'period_end':end,'cik':cik,'fact_id':a.get('id'),'context_id':a['contextRef']})
    return facts


def fiscal_focus(raw):
    text=raw.decode('utf-8');m=FOCUS.search(text)
    year=re.sub(r'<[^>]+>','',m.group(2)).strip() if m else ''
    if not re.fullmatch(r'\d{4}',year):return None
    ref=attrs(m.group(1)).get('contextRef');c=contexts(text).get(ref)
    return {'fiscal_year':int(year),'period_start':c[0],'period_end':c[1]} if c else None
