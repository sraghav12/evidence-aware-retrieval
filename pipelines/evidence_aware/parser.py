"""Deliberately bounded public grammar; unsupported language abstains."""
import re
from .contracts import QuestionInput,QuerySpec,Requirement,Operation,digest


class UnsupportedQuery(ValueError):pass


def parse_query(question,as_of,aliases,fiscal_calendar):
    QuestionInput('parse',question,as_of)
    text=question.strip().rstrip('?.').casefold()
    patterns=[('ranking',r'rank (.+) by fy(\d{4}) revenue growth over fy(\d{4})'),('growth',r'what was (.+) fy(\d{4}) revenue growth over fy(\d{4})'),('sum',r'what was (.+) fy(\d{4}) total revenue'),('extract',r'what was (.+) fy(\d{4}) revenue')]
    for kind,pattern in patterns:
        match=re.fullmatch(pattern,text)
        if match:break
    else:raise UnsupportedQuery('unsupported_query')
    names=re.split(r' and |,\s*',match.group(1))
    if kind in {'growth','extract'} and len(names)!=1:raise UnsupportedQuery('unsupported_query')
    try:entities=[aliases[n.strip()] for n in names]
    except KeyError as e:raise UnsupportedQuery('unknown_entity') from e
    if len(set(entities))!=len(entities):raise UnsupportedQuery('duplicate_entity')
    years=[int(match.group(2))]
    if kind in {'growth','ranking'}:
        old=int(match.group(3));new=years[0]
        if new<=old:raise UnsupportedQuery('invalid_year_order')
        years=[old,new]
    requirements=[]
    for entity in entities:
        for year in years:
            calendar=fiscal_calendar.get((entity,year))
            if calendar is None:raise UnsupportedQuery('unknown_fiscal_calendar')
            start,end=calendar['dates']
            requirements.append(Requirement(f'{entity}:revenue:{year}',entity,'revenue',start,end,year,'USD_million','reported'))
    return QuerySpec(digest([question,as_of])[:16],question,as_of,tuple(requirements),Operation(kind,tuple(r.id for r in requirements)))
