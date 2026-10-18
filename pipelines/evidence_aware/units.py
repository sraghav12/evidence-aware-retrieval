"""Source sections with original character offsets; keep tables intact."""
import re
from .contracts import RetrievalUnit


def build_units(documents):
    units=[]
    for doc_id,d in sorted(documents.items()):
        text=d['text'];starts=[m.start() for m in re.finditer(r'^SECTION ',text,re.M)] or [0]
        for i,start in enumerate(starts):
            end=starts[i+1] if i+1<len(starts) else len(text)
            body=text[start:end]
            headers=tuple(x.strip() for x in body.splitlines()[1].split('|')) if len(body.splitlines())>1 else ()
            units.append(RetrievalUnit(f'{doc_id}::{i}',doc_id,start,end,body,f'{doc_id}::{i}',headers))
    return units
