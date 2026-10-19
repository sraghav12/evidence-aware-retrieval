"""Draft pilot questions and AI-proposed references from raw inline-XBRL fact summaries. Evaluation side only."""
from datetime import date,timedelta
from decimal import Decimal,ROUND_HALF_EVEN

YEAR=2024


def shift(day,days):return (date.fromisoformat(day)+timedelta(days=days)).isoformat()


def millions(fact):return Decimal(fact['value'])*Decimal(10)**int(fact['scale'])/Decimal(10)**6


def text(value):return format(value.normalize(),'f') if value==value.to_integral() else format(value,'f')


class Corpus:
    def __init__(self,filings):
        self.filings=sorted(filings,key=lambda f:(f['ticker'],f['filing_date']));self.calendar={}
        for f in self.filings:
            if f['focus']:
                key=(f['ticker'],f['focus']['fiscal_year'])
                entry=(f['focus']['period_start'],f['focus']['period_end'],f['filing_date']);prior=self.calendar.get(key,())
                if prior is None:continue
                # Conflicting declared dates for one fiscal year make that year unusable.
                self.calendar[key]=None if prior and prior[:2]!=entry[:2] else min(prior or entry,entry,key=lambda e:e[2])

    def filed(self,ticker,fy):
        c=self.calendar.get((ticker,fy));return c[2] if c else None

    def value(self,ticker,fy,as_of):
        """Status plus a single USD-million value when every eligible filing agrees on one figure."""
        c=self.calendar.get((ticker,fy))
        if c is None:return 'no_calendar',None,[]
        if c[2]>as_of:return 'not_disclosed',None,[]
        per_doc={};sources=[]
        for f in self.filings:
            if f['ticker']!=ticker or f['filing_date']>as_of:continue
            for x in f['facts']:
                if (x['period_start'],x['period_end'])==c[:2]:
                    per_doc.setdefault(f['doc_id'],set()).add(millions(x))
                    sources.append(dict(doc_id=f['doc_id'],accession=f['accession_number'],source_url=f['source_url'],period_end=x['period_end'],concept=x['concept'],value=x['value'],scale=x['scale'],fact_id=x['fact_id']))
        if not per_doc:return 'no_fact',None,[]
        if any(len(v)>1 for v in per_doc.values()):return 'definition_conflict',None,sources
        values=set().union(*per_doc.values())
        if len(values)>1:return 'restatement_conflict',None,sources
        seen=set();unique=[s for s in sources if (s['doc_id'],s['value']) not in seen and not seen.add((s['doc_id'],s['value']))]
        return 'ok',values.pop(),unique


def growth(old,new):return ((new-old)/old*100).quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN)


def draft_pilot(filings,spec):
    corpus=Corpus(filings);names=spec['names'];cik={f['ticker']:int(f['cik']) for f in filings}
    questions=[];references=[];lineage=[];excluded=[]
    def add(template,question,as_of,tickers,fy,kind,derivation=()):
        """kind: extract, sum, growth or ranking. Records the question or an exclusion with its reason."""
        years=[fy-1,fy] if kind in ('growth','ranking') else [fy]
        found={(t,y):corpus.value(t,y,as_of) for t in tickers for y in years}
        statuses={s for s,_,_ in found.values()}
        sources=[s for _,_,ss in found.values() for s in ss]
        for bad in ('definition_conflict','no_fact','no_calendar'):
            if bad in statuses:excluded.append({'ticker':'+'.join(tickers),'template':template,'fiscal_year':fy,'reason':bad});return None
        status='restatement_conflict' if 'restatement_conflict' in statuses else 'not_disclosed' if 'not_disclosed' in statuses else 'ok'
        value=None;unit=''
        if status=='ok':
            v={k:x for k,(_,x,_) in found.items()}
            if kind=='extract':value,unit=text(v[(tickers[0],fy)]),'USD_million'
            elif kind=='sum':value,unit=text(sum(v[(t,fy)] for t in tickers)),'USD_million'
            else:
                if any(v[(t,fy-1)]<=0 for t in tickers):excluded.append({'ticker':'+'.join(tickers),'template':template,'fiscal_year':fy,'reason':'nonpositive_growth_base'});return None
                rates=sorted(((growth(v[(t,fy-1)],v[(t,fy)]),t) for t in tickers),key=lambda x:(-x[0],f'cik:{cik[x[1]]}'))
                if kind=='growth':value,unit=format(rates[0][0],'f'),'percent'
                else:
                    value=[];last=None
                    for i,(rate,t) in enumerate(rates,1):
                        if rate==last:value[-1]['entities'].append(f'cik:{cik[t]}')
                        else:value.append({'rank':i,'entities':[f'cik:{cik[t]}'],'value':format(rate,'f')});last=rate
                    unit='percent'
        qid=f'p{len(questions)+1:03d}'
        questions.append({'id':qid,'question':question,'as_of':as_of})
        references.append({'query_id':qid,'answerable':status=='ok','value':value,'unit':unit,'requirements':sorted(f'cik:{cik[t]}:revenue:{y}' for t in tickers for y in years) if status=='ok' else [],
                           'reference_status':status,'template':template,'review_status':'ai_proposed_unreviewed','source_facts':sources})
        lineage.append({'query_id':qid,'entity_ids':sorted(f'cik:{cik[t]}' for t in tickers),'source_ancestry':[],'derivation_ancestry':list(derivation),'template':template,
                        'development_only':bool(set(tickers)&spec['development_tickers'])})
        return qid
    base={}
    for t in sorted(names):
        n=names[t];prev,cur,late=corpus.filed(t,YEAR-1),corpus.filed(t,YEAR),corpus.filed(t,YEAR+1)
        if prev:add('extract',f'What was {n} FY{YEAR-1} revenue?',shift(prev,45),[t],YEAR-1,'extract')
        else:excluded.append({'ticker':t,'template':'extract','fiscal_year':YEAR-1,'reason':'no_calendar'})
        if cur:
            base[t]=add('extract',f'What was {n} FY{YEAR} revenue?',shift(cur,45),[t],YEAR,'extract')
            add('growth',f'What was {n} FY{YEAR} revenue growth over FY{YEAR-1}?',shift(cur,45),[t],YEAR,'growth')
        else:excluded.append({'ticker':t,'template':'extract','fiscal_year':YEAR,'reason':'no_calendar'})
        if late and cur:add('late_disclosure',f'What was {n} FY{YEAR+1} revenue?',shift(late,-15),[t],YEAR+1,'extract')
        if late:
            for fy in (YEAR-2,YEAR-1):
                if corpus.value(t,fy,shift(late,45))[0]=='restatement_conflict':add('restatement',f'What was {n} FY{fy} revenue?',shift(late,45),[t],fy,'extract')
    for t in spec['paraphrase']:
        if base.get(t):add('paraphrase',f'How much revenue did {names[t]} report in fiscal {YEAR}?',shift(corpus.filed(t,YEAR),45),[t],YEAR,'extract',[base[t]])
    for a,b in spec['pairs']:
        filed=[corpus.filed(t,YEAR) for t in (a,b)]
        if None in filed:excluded.append({'ticker':f'{a}+{b}','template':'pair','fiscal_year':YEAR,'reason':'no_calendar'});continue
        as_of=shift(max(filed),45)
        add('sum',f'What was {names[a]} and {names[b]} FY{YEAR} total revenue?',as_of,[a,b],YEAR,'sum')
        add('ranking',f'Rank {names[a]} and {names[b]} by FY{YEAR} revenue growth over FY{YEAR-1}.',as_of,[a,b],YEAR,'ranking')
    for n in spec['unknown']:
        qid=f'p{len(questions)+1:03d}';questions.append({'id':qid,'question':f'What was {n} FY{YEAR} revenue?','as_of':f'{YEAR+1}-06-30'})
        references.append({'query_id':qid,'answerable':False,'value':None,'unit':'','requirements':[],'reference_status':'not_in_corpus','template':'unknown_company','review_status':'ai_proposed_unreviewed','source_facts':[]})
        lineage.append({'query_id':qid,'entity_ids':[f'unknown:{n.casefold()}'],'source_ancestry':[],'derivation_ancestry':[],'template':'unknown_company','development_only':False})
    return {'questions':questions,'references':references,'lineage':lineage,'excluded':excluded}
