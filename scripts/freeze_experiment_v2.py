#!/usr/bin/env python3
"""Freeze the Release C experiment definition. Executes nothing; --dry-run prints without writing."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.evidence_aware.experiment import build_experiment_manifest
from evaluation.evidence_aware.runner import read_jsonl,validate_config
from pipelines.evidence_aware.onnx_rankers import revisions


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',default='data/release/v2/experiment_manifest.json');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    config=json.loads(Path(a.config).read_text());validate_config(config)
    documents={d['doc_id']:d for d in read_jsonl(ROOT/config['documents'])};questions=read_jsonl(ROOT/config['queries'])
    split=hashlib.sha256((ROOT/'data/release/v2/pilot_split_manifest.json').read_bytes()).hexdigest()
    m=build_experiment_manifest(config,documents,questions,available_rankers=revisions(),attachments={'split_manifest_sha256':split})
    summary={'arms':len(m['arms']),'available':sum(x['status']=='available' for x in m['arms']),'unavailable':sorted({x['name'] for x in m['arms'] if x['status']=='unavailable'}),
             'run_count':m['run_count'],'provider_requests':m['estimates']['provider_requests'],'primary':m['primary'],'manifest_sha256':m['manifest_sha256']}
    if not a.dry_run:(ROOT/a.output).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(summary,written=None if a.dry_run else a.output),sort_keys=True))


if __name__=='__main__':main()
