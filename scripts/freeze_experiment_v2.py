#!/usr/bin/env python3
"""Freeze the Release C experiment definition. Executes nothing; --dry-run prints without writing."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.evidence_aware.experiment import build_experiment_manifest
from evaluation.evidence_aware.runner import read_jsonl,validate_config
from pipelines.evidence_aware.onnx_rankers import revisions
from evaluation.evidence_aware.experiment import arm_sensitivity


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',default='data/release/v2/experiment_manifest.json');p.add_argument('--dry-run',action='store_true');p.add_argument('--references',default='data/release/v2/references/pilot.jsonl');p.add_argument('--split-manifest',default='data/release/v2/pilot_split_manifest.json');a=p.parse_args()
    config=json.loads(Path(a.config).read_text());validate_config(config)
    documents={d['doc_id']:d for d in read_jsonl(ROOT/config['documents'])};questions=read_jsonl(ROOT/config['queries'])
    split=hashlib.sha256((ROOT/a.split_manifest).read_bytes()).hexdigest()
    refs_path=ROOT/a.references;references={r['query_id']:r for r in read_jsonl(refs_path)}
    split_manifest=json.loads((ROOT/a.split_manifest).read_text())
    sensitivity=arm_sensitivity(questions,documents,config['aliases'],references)
    attachments={'split_manifest_sha256':split,'references_sha256_at_freeze':hashlib.sha256(refs_path.read_bytes()).hexdigest(),'arm_sensitivity':sensitivity,
                 'locked_test':split_manifest['locked_test'],'effective_groups':split_manifest['effective_groups'],
                 'evaluation_scope':'development-only descriptive pilot' if split_manifest['effective_groups']['test']==0 else 'locked test' if split_manifest['effective_groups']['development']==0 else 'development plus locked test','inference_status':split_manifest['inference_status']}
    m=build_experiment_manifest(config,documents,questions,available_rankers=revisions(),attachments=attachments)
    summary={'arms':len(m['arms']),'available':sum(x['status']=='available' for x in m['arms']),'unavailable':sorted({x['name'] for x in m['arms'] if x['status']=='unavailable'}),
             'run_count':m['run_count'],'scope':m['evaluation_scope'],'arm_sensitive':{k:v for k,v in m['arm_sensitivity'].items() if k!='arm_sensitive_ids'},'provider_requests':m['estimates']['provider_requests'],'primary':m['primary'],'manifest_sha256':m['manifest_sha256']}
    if not a.dry_run:(ROOT/a.output).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(summary,written=None if a.dry_run else a.output),sort_keys=True))


if __name__=='__main__':main()
