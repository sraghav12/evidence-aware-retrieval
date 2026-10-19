"""Extract only explicit cells in a versioned normalized table representation."""
import hashlib
from .contracts import EvidenceSpan

HEADERS=('metric','unit','period_start','period_end','fiscal_year','accounting_basis','value')
HTML_HEADERS=HEADERS+('row_label','column_header','locator')


def extract_candidates(units,documents):
    spans=[]
    for unit in units:
        d=documents[unit.doc_id]
        if d['text'][unit.start:unit.end]!=unit.text:continue
        headers=None;offset=unit.start
        for raw in unit.text.splitlines(keepends=True):
            line=raw.rstrip('\r\n');cells=tuple(c.strip() for c in line.split('|'))
            if cells in (HEADERS,HTML_HEADERS):headers=cells
            elif headers is None:pass
            elif len(cells)!=len(headers) or cells[0]=='metric':headers=None
            elif cells[0]=='revenue':
                metric,currency,start,end,year,basis,value=cells[:7]
                try:
                    spans.append(EvidenceSpan(f'{unit.doc_id}:{offset}',unit.doc_id,d['accession'],d['sha256'],d['entity_id'],d['disclosed_at'],offset,offset+len(line),line,metric,start,end,int(year),currency,value,basis,headers,d['source_url']))
                except (ValueError,TypeError):pass
            offset+=len(raw)
    return spans
