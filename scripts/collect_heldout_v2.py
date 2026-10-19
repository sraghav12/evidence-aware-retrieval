#!/usr/bin/env python3
"""Collect held-out 10-K filings from SEC EDGAR. Requires SEC_EDGAR_USER_AGENT ("Name email") in the environment; it is never written to disk."""
from pathlib import Path
import argparse,gzip,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.evidence_aware.sec_collect import Client,collect,collect_frozen


def development_tickers():
    with gzip.open(ROOT/'data/release/v1/corpus_150.jsonl.gz','rt',encoding='utf-8') as f:return {json.loads(l)['metadata']['ticker'] for l in f}


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True)
    p.add_argument('--select-latest',metavar='NEW_MANIFEST',help='select the latest filings now and write a NEW manifest (never the tracked one); default reproduces the recorded collection');a=p.parse_args()
    config=json.loads(Path(a.config).read_text());sel=config['heldout_selection']
    overlap=set(sel['tickers'])&(development_tickers()|set(sel['development_named_tickers']))
    if overlap:raise SystemExit(f'held-out tickers overlap development ancestry: {sorted(overlap)}')
    client=Client(os.environ.get('SEC_EDGAR_USER_AGENT',''));tracked=ROOT/sel['filings_manifest']
    if not a.select_latest:
        m=collect_frozen(client,json.loads(tracked.read_text()),ROOT/sel['raw_dir'])
        print(json.dumps({'mode':'frozen','verified':len(m['filings']),'requests':m['requests']},sort_keys=True));return
    target=Path(a.select_latest)
    if target.resolve()==tracked.resolve() or target.exists():raise SystemExit('refusing to overwrite an existing manifest')
    m=collect(client,sel['tickers'],ROOT/sel['raw_dir'],annual=sel['annual_filings'])
    m['raw_location']=f"ignored {sel['raw_dir']} (not tracked)"
    target.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'mode':'select_latest','filings':len(m['filings']),'missing':m['missing'],'requests':m['requests']},sort_keys=True))


if __name__=='__main__':main()
