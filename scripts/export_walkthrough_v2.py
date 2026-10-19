#!/usr/bin/env python3
"""Export selected saved traces into a portable source-to-answer walkthrough (JSON + Markdown). Reads saved files only."""
from pathlib import Path
import argparse,json

CASES=[('rd02','Early stop: complete evidence after the cheap stage'),('rd05','Escalation: section search recovers the missing company'),
       ('rd13','Principled abstention: reported vs restated revenue'),('rd06','Unresolved failure: BM25 slot competition in a three-company ranking')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',default='results/evidence_v2/real_dev_002');p.add_argument('--segments',default='data/processed/evidence_v2/real_dev_segments.jsonl')
    p.add_argument('--manifest',default='data/release/v2/source_manifest.json');p.add_argument('--output',default='examples/evidence_v2');a=p.parse_args()
    traces={t['query_id']:t for t in map(json.loads,Path(a.results,'traces.jsonl').read_text().splitlines())}
    segments={s['span_id']:s for s in map(json.loads,Path(a.segments).read_text().splitlines())}
    urls={f['doc_id']:f['source_url'] for f in json.loads(Path(a.manifest).read_text())['filings']}
    out=[];md=['# Evidence-aware retrieval: four real-filing traces','',f'Exported from saved run `{Path(a.results).name}` (executor only, 0 provider calls). Every number below is a raw inline-XBRL cell; locators point into the SEC filing.','']
    for qid,title in CASES:
        t=traces[qid];cited={i for ids in (t['answer'].get('citations') or {}).values() for i in ids}
        wanted={(r['entity_id'],r['fiscal_year']) for r in (t['spec'] or {}).get('requirements',[])}
        evidence=[{k:e[k] for k in ('id','doc_id','quote','fiscal_year','value','unit')}|{'cited':e['id'] in cited,'source_url':urls.get(e['doc_id']),
                  'raw_locator':{k:segments[e['id']][k] for k in ('table_index','row_index','cell_index','fact_id','concept','raw_byte_start','raw_byte_end')} if e['id'] in segments else None}
                  for e in t['evidence'] if e['id'] in cited or (t['answer']['status']!='answered' and (e['entity_id'],e['fiscal_year']) in wanted)]
        seen=set();evidence=[e for e in evidence if (e['doc_id'],e['fiscal_year'],e['value']) not in seen and not seen.add((e['doc_id'],e['fiscal_year'],e['value']))]
        case={'query_id':qid,'title':title,'question':t['question'],'as_of':t['as_of'],'requirements':[r['id'] for r in (t['spec'] or {}).get('requirements',[])],
              'stages':[{'stage':s['stage'],'selected_units':len(s['ids']),'inspected_tokens':s['inspected_tokens']} for s in t['selected_units']],
              'coverage':[{k:c[k] for k in ('supported_requirement_ids','missing_requirement_ids','conflicts')} for c in t['coverage_snapshots']],
              'decisions':[d['action'] for d in t['decisions']],'answer':t['answer'],'evidence':evidence[:8]}
        out.append(case)
        md+=[f'## {title}','',f'**Question:** {t["question"]} (as of {t["as_of"]})','',f'**Route:** {" → ".join(case["decisions"])}','']
        for s,c in zip(case['stages'],case['coverage']):md.append(f'- `{s["stage"]}`: {s["selected_units"]} units, {s["inspected_tokens"]} tokens inspected; supported {len(c["supported_requirement_ids"])}, missing {len(c["missing_requirement_ids"])}, conflicts {len(c["conflicts"])}')
        ans=t['answer'];md+=['',f'**Result:** {ans["status"]}'+(f' — `{json.dumps(ans["value"])}` {ans["unit"]}' if ans['status']=='answered' else f' — reason `{ans["reason"]}`'),'']
        for e in case['evidence'][:4]:
            loc=e['raw_locator'];md.append(f'- {"cited " if e["cited"] else ""}`{e["doc_id"]}` FY{e["fiscal_year"]} = {e["value"]} {e["unit"]}'+(f' — table {loc["table_index"]}, row {loc["row_index"]}, fact `{loc["fact_id"][:24]}{"…" if len(loc["fact_id"])>24 else ""}` ([filing]({e["source_url"]}))' if loc else ''))
        md.append('')
    Path(a.output).mkdir(parents=True,exist_ok=True)
    Path(a.output,'walkthrough.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');Path(a.output,'walkthrough.md').write_text('\n'.join(md)+'\n')
    print(Path(a.output,'walkthrough.md'))


if __name__=='__main__':main()
