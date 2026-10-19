#!/usr/bin/env python3
"""Run provider-free v2 inference; live arms fail explicitly until implemented."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.evidence_aware.runner import run,validate_config


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--mode',choices=['offline','live'],default='offline');p.add_argument('--output');p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    config=json.loads(Path(args.config).read_text())
    if args.output:config['output']=args.output
    try:
        if args.mode=='live':raise ValueError('live provider arm unavailable; no call submitted')
        validate_config(config)
        if args.dry_run:print(json.dumps({'valid':True,'provider_calls':0,'config':config},sort_keys=True));return
        out=run(config);print(out)
    except (ValueError,FileExistsError) as e:p.exit(2,str(e)+'\n')

if __name__=='__main__':main()
