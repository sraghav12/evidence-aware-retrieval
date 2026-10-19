#!/usr/bin/env python3
"""Hash, copy and normalize selected raw SEC HTML. Never reads references, questions or credentials."""
from collections import Counter
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipelines.evidence_aware.html_source import prepare_sources


def v1_filings(raw_dir):
    release=json.loads((ROOT/'data/release/v1/manifest.json').read_text());text_sha={f['doc_id']:f['text_sha256'] for f in release['filings']}
    primary={Path(x['file_path']).stem:x['primary_document'] for x in json.loads((Path(raw_dir)/'filing_manifest.json').read_text())}
    with gzip.open(ROOT/'data/release/v1/corpus_150.jsonl.gz','rt',encoding='utf-8') as f:rows=[json.loads(line) for line in f]
    filings=[]
    for r in rows:
        m=r['metadata'];acc=m['accession_number']
        filings.append(dict(doc_id=r['doc_id'],ticker=m['ticker'],cik=m['cik'],accession_number=acc,filing_date=m['filing_date'],raw_html_bytes=m['raw_html_bytes'],v1_text_sha256=text_sha[r['doc_id']],
                            source_url=f'https://www.sec.gov/Archives/edgar/data/{int(m["cik"])}/{acc.replace("-","")}/{primary[r["doc_id"]]}'))
    return sorted(filings,key=lambda f:f['doc_id'])


def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--source-raw-dir',required=True);p.add_argument('--audit-all',action='store_true');a=p.parse_args()
    config=json.loads(Path(a.config).read_text());selection=config['source_selection']
    filings=v1_filings(a.source_raw_dir)
    if a.audit_all:
        out=prepare_sources(a.source_raw_dir,filings);m=out['manifest']
        audit={'scope':'all 150 frozen v1 filings; extraction counts only','extractor_version':m['extractor_version'],'status_counts':m['status_counts'],'revenue_spans':m['revenue_spans'],'rejected':m['rejected'],
               'filings_with_spans':sum(e.get('revenue_spans',0)>0 for e in m['filings']),'tickers_with_spans':sorted({e['ticker'] for e in m['filings'] if e.get('revenue_spans',0)>0}),
               'tickers_without_spans':sorted({e['ticker'] for e in m['filings']}-{e['ticker'] for e in m['filings'] if e.get('revenue_spans',0)>0}),
               'per_filing':[{k:e.get(k) for k in ('doc_id','status','raw_sha256','fiscal_year_focus','revenue_candidates','revenue_spans','rejected')} for e in m['filings']]}
        target=ROOT/selection['audit_output'];target.write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n');print(target);return
    chosen=[f for f in filings if f['ticker'] in set(selection['tickers'])]
    out=prepare_sources(a.source_raw_dir,chosen,copy_dir=ROOT/selection['raw_copy_dir'])
    docs=ROOT/config['documents'];write_jsonl(docs,out['documents'])
    write_jsonl(ROOT/selection['segments_output'],out['segments']);write_jsonl(ROOT/selection['failures_output'],out['failures'])
    manifest=out['manifest'];lineage={f['doc_id']:f for f in chosen}
    for e in manifest['filings']:e['v1_text_sha256']=lineage[e['doc_id']]['v1_text_sha256'];e['source_url']=lineage[e['doc_id']]['source_url']
    manifest.update(selection=selection,v1_corpus_sha256=hashlib.sha256((ROOT/'data/release/v1/corpus_150.jsonl.gz').read_bytes()).hexdigest(),
                    documents_sha256=hashlib.sha256(docs.read_bytes()).hexdigest(),segments_sha256=hashlib.sha256((ROOT/selection['segments_output']).read_bytes()).hexdigest(),
                    raw_location='raw HTML is untracked; source checkout data/raw/<doc_id>.html, copied into ignored '+selection['raw_copy_dir'])
    target=ROOT/selection['manifest_output'];target.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'manifest':str(target.relative_to(ROOT)),'status_counts':manifest['status_counts'],'revenue_spans':manifest['revenue_spans']},sort_keys=True))


if __name__=='__main__':main()
