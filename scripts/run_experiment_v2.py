#!/usr/bin/env python3
"""Run a frozen experiment manifest exactly, then score it. Refuses any drift from the freeze; makes no provider calls."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.evidence_aware.runner import read_jsonl,validate_config
from evaluation.evidence_aware.experiment_runner import run_experiment
from evaluation.evidence_aware.experiment_report import build_experiment_report


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--manifest',default='data/release/v2/experiment_manifest.json');p.add_argument('--references',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    config=json.loads(Path(a.config).read_text());validate_config(config);manifest=json.loads((ROOT/a.manifest).read_text())
    documents={d['doc_id']:d for d in read_jsonl(ROOT/config['documents'])};questions=read_jsonl(ROOT/config['queries'])
    roles=sorted({r for arm in manifest['arms'] if arm['status']=='available' for r in arm['ranker_revisions']})
    rankers={}
    if roles:
        from pipelines.evidence_aware.onnx_rankers import load_rankers
        rankers=load_rankers(roles=tuple(roles))
        if {r:x.revision for r,x in rankers.items()}!={r:v for arm in manifest['arms'] for r,v in arm['ranker_revisions'].items()}:raise SystemExit('ranker revisions differ from freeze')
    out=run_experiment(manifest,config,documents,questions,rankers,ROOT/a.output)
    report=build_experiment_report(out,a.references,manifest)
    print(json.dumps({'output':a.output,'primary':[{k:c[k] for k in ('split','metric','paired_difference','ci95','independent_clusters','inference_status')} for c in report['comparisons'] if c['name']=='primary']},sort_keys=True))


if __name__=='__main__':main()
