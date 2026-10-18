"""Cutoff-aware public fiscal dates, never answer-key requirements."""
from .contracts import iso_date


def build_fiscal_calendar(documents,as_of):
    result={};conflicts=set();iso_date(as_of)
    for d in documents.values():
        if iso_date(d['disclosed_at'])>as_of:continue
        for entry in d.get('fiscal_calendar',[]):
            key=(d['entity_id'],entry['fiscal_year'])
            value=(iso_date(entry['period_start']),iso_date(entry['period_end']))
            if key in result and result[key]['dates']!=value:conflicts.add(key)
            result[key]={'dates':value,'accession':d['accession'],'doc_sha256':d['sha256']}
    return {k:v for k,v in result.items() if k not in conflicts}
