#!/usr/bin/env python3
"""Draft the Release C pilot: question-only file, separate AI-proposed references, split manifest and human annotation packet.
Reads raw inline-XBRL facts only; never runs inference or reads run outputs."""
from collections import Counter
from pathlib import Path
import argparse,csv,gzip,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from prepare_evidence_v2 import v1_filings,write_jsonl
from evaluation.evidence_aware.xbrl_reference import revenue_facts,fiscal_focus
from evaluation.evidence_aware.pilot import draft_pilot,development_lineage
from evaluation.evidence_aware.dataset import build_pilot_manifest

OUT=ROOT/'data/release/v2'


def development_rows(aliases):
    """Release B questions and all 43 published v1 questions are development-only ancestry."""
    release_b=[json.loads(x) for x in (OUT/'real_dev_questions.jsonl').read_text().splitlines()]
    v1=json.loads((ROOT/'data/release/v1/queries.json').read_text())
    with gzip.open(ROOT/'data/release/v1/corpus_150.jsonl.gz','rt',encoding='utf-8') as f:ciks={r['doc_id']:int(r['metadata']['cik']) for r in map(json.loads,f)}
    return development_lineage(release_b,aliases,[{'id':q['id'],'evidence_docs':q['evidence_docs']} for q in v1],ciks)


def write_packet(packet,d):
    """Human annotation sheet: proposals plus raw facts, blank reviewer columns."""
    packet.parent.mkdir(parents=True,exist_ok=True);questions={q['id']:q for q in d['questions']}
    with open(packet,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['query_id','split','question','as_of','proposed_answerable','proposed_value','unit','reference_status','second_review_required','source_facts','reviewer_id','verdict','corrected_value','notes'])
        for r in d['references']:
            q=questions[r['query_id']];second=not r['answerable'] or r['reference_status']!='ok' or int(r['query_id'][1:])%4==0
            facts='; '.join(f"{s['doc_id']} {s['accession']} {s['period_end']} {s['concept']}={s['value']} (scale {s['scale']}, {s['fact_id']})" for s in r['source_facts'])
            w.writerow([r['query_id'],r['split'],q['question'],q['as_of'],r['answerable'],json.dumps(r['value']) if isinstance(r['value'],list) else r['value'] or '',r['unit'],r['reference_status'],second,facts,'','','',''])


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--source-raw-dir',required=True);a=p.parse_args()
    config=json.loads(Path(a.config).read_text());spec=config['pilot_spec']
    summaries=[]
    for f in v1_filings(a.source_raw_dir):
        if f['ticker'] not in spec['names']:continue
        raw=(Path(a.source_raw_dir)/f'{f["doc_id"]}.html').read_bytes()
        summaries.append(dict(f,focus=fiscal_focus(raw),facts=revenue_facts(raw)))
    d=draft_pilot(summaries,dict(names=spec['names'],pairs=[tuple(x) for x in spec['pairs']],paraphrase=spec['paraphrase'],unknown=spec['unknown'],development_tickers=set(spec['development_tickers'])))
    manifest=build_pilot_manifest(development_rows(config['aliases'])+d['lineage'],config['seed'],min_locked_groups=spec['min_locked_groups'])
    split={r['query_id']:r for r in manifest['rows']}
    for r in d['references']:r['component']=split[r['query_id']]['component'];r['split']=split[r['query_id']]['split']
    write_jsonl(OUT/'pilot_questions.jsonl',d['questions']);write_jsonl(OUT/'references/pilot.jsonl',d['references'])
    pilot={q['id'] for q in d['questions']}
    summary={'questions':len(d['questions']),'by_template':dict(sorted(Counter(r['template'] for r in d['references']).items())),
             'answerable':sum(r['answerable'] for r in d['references']),'unanswerable':sum(not r['answerable'] for r in d['references']),
             'by_split':dict(sorted(Counter(split[q]['split'] for q in pilot).items())),'excluded':d['excluded'],'excluded_tickers':spec['excluded_tickers'],
             'human_reviewers':0,'review_status':'ai_proposed_unreviewed'}
    manifest.update(pilot_summary=summary)
    (OUT/'pilot_split_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    write_packet(OUT/'annotation/pilot_packet.csv',d)
    print(json.dumps({k:summary[k] for k in ('questions','answerable','unanswerable','by_split','by_template')},sort_keys=True));print('groups',manifest['effective_groups'],manifest['locked_test'],manifest['inference_status'])


if __name__=='__main__':main()
