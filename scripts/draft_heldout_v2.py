#!/usr/bin/env python3
"""Draft the held-out locked test from collected filings with the frozen pilot templates. Never runs inference or reads run outputs."""
from collections import Counter
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from prepare_evidence_v2 import write_jsonl
from draft_pilot_v2 import development_rows,write_packet
from evaluation.evidence_aware.xbrl_reference import revenue_facts,fiscal_focus
from evaluation.evidence_aware.pilot import draft_pilot
from evaluation.evidence_aware.dataset import build_heldout_manifest

OUT=ROOT/'data/release/v2'


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args()
    config=json.loads(Path(a.config).read_text());spec=config['heldout_spec'];sel=config['heldout_selection']
    filings=json.loads((ROOT/sel['filings_manifest']).read_text())['filings'];summaries=[]
    for f in filings:
        raw=(ROOT/sel['raw_dir']/f'{f["doc_id"]}.html').read_bytes()
        summaries.append(dict(f,focus=fiscal_focus(raw),facts=revenue_facts(raw)))
    d=draft_pilot(summaries,dict(names=spec['names'],pairs=[tuple(x) for x in spec['pairs']],paraphrase=spec['paraphrase'],unknown=[],development_tickers=set(),late_cutoff=True))
    for q,r,l in zip(d['questions'],d['references'],d['lineage']):
        for x in (q,):x['id']='h'+x['id'][1:]
        r['query_id']=l['query_id']=q['id'];l['derivation_ancestry']=['h'+x[1:] for x in l['derivation_ancestry']]
    pilot_rows=[dict(r,development_only=True) for r in json.loads((OUT/'pilot_split_manifest.json').read_text())['rows']]
    dev=development_rows(json.loads((ROOT/'configs/evidence_v2_experiment.json').read_text())['aliases'])+pilot_rows
    manifest=build_heldout_manifest(d['lineage'],dev);split={r['query_id']:r for r in manifest['rows']}
    for r in d['references']:r['component']=split[r['query_id']]['component'];r['split']='test'
    write_jsonl(OUT/'heldout_questions.jsonl',d['questions']);write_jsonl(OUT/'references/heldout.jsonl',d['references'])
    manifest.update(heldout_summary={'questions':len(d['questions']),'by_template':dict(sorted(Counter(r['template'] for r in d['references']).items())),'answerable':sum(r['answerable'] for r in d['references']),
                                     'unanswerable':sum(not r['answerable'] for r in d['references']),'excluded':d['excluded'],'human_reviewers':0,'review_status':'ai_proposed_unreviewed'})
    (OUT/'heldout_split_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    write_packet(OUT/'annotation/heldout_packet.csv',d)
    s=manifest['heldout_summary'];print(json.dumps({k:s[k] for k in ('questions','answerable','unanswerable','by_template')},sort_keys=True));print(manifest['effective_groups'],manifest['inference_status'],Counter(e['reason'] for e in s['excluded']))


if __name__=='__main__':main()
