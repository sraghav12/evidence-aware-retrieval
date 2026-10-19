#!/usr/bin/env python3
from pathlib import Path
import argparse,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.evidence_aware.report import build_report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--references',default='tests/fixtures/evidence_v2/references.jsonl');a=p.parse_args()
    r=build_report(a.results,a.references);print(json.dumps(r['summary'],sort_keys=True))
