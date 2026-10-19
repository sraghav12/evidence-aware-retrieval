from evaluation.evidence_aware.pilot import draft_pilot


def filing(ticker,cik,fy,filed,facts,end=None):
    end=end or f'{fy}-12-31'
    return dict(doc_id=f'{ticker}_{fy}',ticker=ticker,cik=cik,accession_number=f'{cik}-{fy}',filing_date=filed,source_url=f'fixture://{ticker}/{fy}',
                focus={'fiscal_year':fy,'period_start':f'{fy}-01-01','period_end':end},
                facts=[dict(concept=c,value=v,scale='6',period_start=f'{y}-01-01',period_end=f'{y}-12-31',fact_id=f'{ticker}{fy}{y}{c[-3:]}',context_id='c') for y,v,c in facts])


R='us-gaap:Revenues';C='us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
FILINGS=[filing('AAA',1,2023,'2024-02-15',[(2023,'100',R),(2022,'90',R)]),filing('AAA',1,2024,'2025-02-15',[(2024,'120',R),(2023,'100',R)]),filing('AAA',1,2025,'2026-02-15',[(2025,'130',R),(2024,'120',R)]),
         filing('BBB',2,2023,'2024-02-20',[(2023,'200',R)]),filing('BBB',2,2024,'2025-02-20',[(2024,'220',R),(2023,'195',R)]),filing('BBB',2,2025,'2026-02-20',[(2025,'230',R),(2024,'220',R)]),
         filing('CCC',3,2023,'2024-02-10',[(2023,'50',R),(2023,'55',C)]),filing('CCC',3,2024,'2025-02-10',[(2024,'60',R),(2023,'50',R)]),filing('CCC',3,2025,'2026-02-10',[(2025,'70',R)])]
SPEC=dict(names={'AAA':'Alpha Co','BBB':'Beta Co','CCC':'Gamma Co'},pairs=[('AAA','BBB')],paraphrase=['AAA'],unknown=['Zeta Co'],development_tickers=set())


def draft():return draft_pilot(FILINGS,SPEC)


def test_pilot_questions_are_question_only_and_references_separate():
    d=draft()
    assert d['questions'] and all(set(q)=={'id','question','as_of'} for q in d['questions'])
    assert {q['id'] for q in d['questions']}=={r['query_id'] for r in d['references']}=={r['query_id'] for r in d['lineage']}
    assert all(r['review_status']=='ai_proposed_unreviewed' for r in d['references'])


def ref(d,question):
    q=next(q for q in d['questions'] if q['question']==question);return q,next(r for r in d['references'] if r['query_id']==q['id'])


def test_answerable_values_and_requirements():
    d=draft();q,r=ref(d,'What was Alpha Co FY2024 growth?'.replace('growth','revenue growth over FY2023'))
    assert r['answerable'] and r['value']=='20.00' and r['unit']=='percent' and r['requirements']==['cik:1:revenue:2023','cik:1:revenue:2024'] and q['as_of']=='2025-04-01'
    _,r=ref(d,'Rank Alpha Co and Beta Co by FY2024 revenue growth over FY2023.')
    assert r['answerable'] is False and r['reference_status']=='restatement_conflict'
    _,r=ref(d,'What was Alpha Co and Beta Co FY2024 total revenue?')
    assert r['value']=='340' and r['unit']=='USD_million'


def test_late_disclosure_template_is_unanswerable():
    q,r=ref(draft(),'What was Alpha Co FY2025 revenue?')
    assert r['answerable'] is False and r['reference_status']=='not_disclosed' and q['as_of']<'2026-02-15'


def test_restatement_conflict_is_unanswerable_and_definition_conflict_excluded():
    d=draft()
    _,r=ref(d,'What was Beta Co FY2023 revenue?')
    assert r['answerable'] and r['value']=='200'
    assert any(r['reference_status']=='restatement_conflict' and r['requirements']==[] for r in d['references'])
    assert not any('Gamma Co FY2023' in q['question'] for q in d['questions'])
    assert {'ticker':'CCC','template':'extract','fiscal_year':2023,'reason':'definition_conflict'} in d['excluded']


def test_paraphrase_shares_derivation_and_unknown_company_has_no_source():
    d=draft();lineage={r['query_id']:r for r in d['lineage']}
    q,r=ref(d,'How much revenue did Alpha Co report in fiscal 2024?');base,_=ref(d,'What was Alpha Co FY2024 revenue?')
    assert r['answerable'] and lineage[q['id']]['derivation_ancestry']==[base['id']]
    q,r=ref(d,'What was Zeta Co FY2024 revenue?')
    assert r['answerable'] is False and lineage[q['id']]['entity_ids']==['unknown:zeta co'] and r['source_facts']==[]


def test_conflicting_fiscal_focus_excludes_company():
    dup=[filing('DDD',4,2024,'2025-02-01',[(2024,'10',R)]),filing('DDD',4,2024,'2025-03-01',[(2024,'10',R)],end='2025-01-31'),filing('DDD',4,2024,'2025-04-01',[(2024,'10',R)])]
    for f,day in zip(dup,('a','b','c')):f['doc_id']+=day
    d=draft_pilot(FILINGS+dup,dict(SPEC,names=dict(SPEC['names'],DDD='Delta Co')))
    assert not any('Delta Co' in q['question'] for q in d['questions']) and {'ticker':'DDD','template':'extract','fiscal_year':2024,'reason':'no_calendar'} in d['excluded']


def test_pilot_generation_is_deterministic():
    assert draft()==draft()


def test_v1_and_release_b_rows_are_development_only():
    from evaluation.evidence_aware.pilot import development_lineage
    rows=development_lineage([{'id':'rd01','question':'What was Alpha Co FY2024 revenue?','as_of':'2025-03-01'},{'id':'rd17','question':'What was Tesla FY2024 revenue?','as_of':'2025-06-30'}],
                             {'alpha co':'cik:1'},[{'id':'q007','evidence_docs':['BBB_2024','CCC_2023']}],{'BBB_2024':2,'CCC_2023':3})
    by={r['query_id']:r for r in rows}
    assert all(r['development_only'] for r in rows) and by['v1:q007']['entity_ids']==['cik:2','cik:3'] and by['rd01']['entity_ids']==['cik:1'] and by['rd17']['entity_ids']==['unknown:tesla']
    assert by['v1:q007']['template']=='v1_published'


def test_precision_only_difference_is_not_restatement():
    lly=[filing('EEE',5,2023,'2024-02-21',[(2023,'34124.1',R)]),filing('EEE',5,2024,'2025-02-19',[(2024,'45042.7',R),(2023,'34124.1',R)]),filing('EEE',5,2025,'2026-02-12',[(2025,'65179',R),(2024,'45043',R),(2023,'34124',R)])]
    for f in lly:
        for x in f['facts']:x['decimals']='-5' if '.' in x['value'] else '-6'
    d=draft_pilot(FILINGS+lly,dict(SPEC,names=dict(SPEC['names'],EEE='Echo Co')))
    probes=[r for r in d['references'] if r['template']=='restatement' and 'cik:5' in str(r['source_facts']) or (r['reference_status']=='restatement_conflict' and any(s['doc_id'].startswith('EEE') for s in r['source_facts']))]
    assert probes==[]
    _,r=ref(d,'What was Echo Co FY2024 revenue growth over FY2023?');assert r['answerable'] and r['value']=='32.00'
    from evaluation.evidence_aware.pilot import Corpus
    assert Corpus(FILINGS+lly).value('EEE',2023,'2026-04-01')[:2]==('ok',__import__('decimal').Decimal('34124.1'))
    assert Corpus(FILINGS).value('BBB',2023,'2026-04-01')[0]=='restatement_conflict'
