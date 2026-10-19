"""Score a frozen-experiment run from saved files: per-arm metrics by split, paired cluster intervals, resource totals."""
from pathlib import Path
import hashlib,html,json
from pipelines.evidence_aware.contracts import digest
from .report import score_answers,paired_cluster_summary
from .runner import read_jsonl,write_json


def percentile(values,q):
    if not values:return None
    v=sorted(values);return v[min(len(v)-1,round(q*(len(v)-1)))]


def arm_metrics(rows,traces):
    answerable=[r for r in rows if r['answerable']];unanswerable=[r for r in rows if not r['answerable']]
    usage=[e for t in traces for e in t['usage']]
    return {'questions':len(rows),'answerable':len(answerable),'unanswerable':len(unanswerable),'supported_success':sum(bool(r['supported_correct']) for r in answerable),
            'supported_success_rate':sum(bool(r['supported_correct']) for r in answerable)/len(answerable) if answerable else None,
            'correct_abstentions':sum(r['correct_decision'] for r in unanswerable),'correct_abstention_rate':sum(r['correct_decision'] for r in unanswerable)/len(unanswerable) if unanswerable else None,
            'answered':sum(r['status']=='answered' for r in rows),'errors':sum(r['status']=='error' for r in rows),'unsupported_answers':sum(r['status']=='answered' and not r['supported_correct'] for r in rows),
            'retrieval_stages':sum(len(t['selected_units']) for t in traces),'inspected_retrieval_tokens':sum(e['input_tokens'] or 0 for e in usage if e['stage']=='retrieval'),
            'verification_tokens':sum(e['input_tokens'] or 0 for e in usage if e['stage']=='verification'),'conflict_probe_tokens':sum(e['input_tokens'] or 0 for e in usage if e['stage']=='conflict_probe'),
            'probe_status':{k:sum((t.get('conflict_probe') or {}).get('status')==k for t in traces) for k in ('ran','ran_truncated','skipped_budget','no_later_filings')},
            'latency':{'p50_ms':percentile([t['wall_ms'] for t in traces],.5),'p95_ms':percentile([t['wall_ms'] for t in traces],.95)}}


def svg(points,title):
    """Standard-library scatter: inspected retrieval tokens per question (x) against answerable supported-success rate (y)."""
    W,H,P=760,420,60;xs=[p[1] for p in points] or [1];xmax=max(xs)*1.45 or 1
    def x(v):return P+(W-2*P)*v/xmax
    def y(v):return H-P-(H-2*P)*v
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="system-ui" font-size="11">',f'<text x="{W/2}" y="20" text-anchor="middle" font-size="13">{html.escape(title)}</text>',
           f'<line x1="{P}" y1="{H-P}" x2="{W-P}" y2="{H-P}" stroke="#333"/><line x1="{P}" y1="{P}" x2="{P}" y2="{H-P}" stroke="#333"/>',
           f'<text x="{W/2}" y="{H-20}" text-anchor="middle">mean inspected retrieval tokens per question (whitespace estimate)</text>',f'<text x="15" y="{H/2}" transform="rotate(-90 15 {H/2})" text-anchor="middle">answerable supported-success rate</text>']
    for t in (0,.25,.5,.75,1):parts.append(f'<text x="{P-6}" y="{y(t)+4}" text-anchor="end">{t:.2f}</text>')
    for label,px,py in points:
        if py is None:continue
        parts.append(f'<circle cx="{x(px):.1f}" cy="{y(py):.1f}" r="4" fill="#2b6cb0"/><text x="{x(px)+6:.1f}" y="{y(py)-6:.1f}">{html.escape(label)}</text>')
    return ''.join(parts)+'</svg>\n'


def build_experiment_report(result_dir,reference_path,manifest):
    root=Path(result_dir);run=json.loads((root/'manifest.json').read_text());status=json.loads((root/'status.json').read_text())
    raw=(root/'traces.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=run['traces_sha256']:raise ValueError('trace checksum mismatch')
    if not status['complete'] or run['run_count']!=manifest['run_count']:raise ValueError('incomplete run')
    if run['experiment_manifest_sha256']!=manifest['manifest_sha256']:raise ValueError('run belongs to a different freeze')
    traces=[json.loads(x) for x in raw.splitlines()];config=json.loads((root/'config.json').read_text())
    documents={d['doc_id']:d for d in read_jsonl(Path(config['documents']) if Path(config['documents']).is_absolute() else Path.cwd()/config['documents'])}
    if digest(documents)!=manifest['corpus_hash']:raise ValueError('corpus hash mismatch')
    references={r['query_id']:r for r in read_jsonl(reference_path)}
    if {t['query_id'] for t in traces}!=set(references):raise ValueError('question set differs from references')
    rows=score_answers(traces,references,documents);trace_by={(t['query_id'],t['arm'],t['repeat']):t for t in traces}
    for r in rows:r['split']=references[r['query_id']].get('split','all')
    splits=sorted({r['split'] for r in rows});splits=splits+(['all'] if len(splits)>1 else [])
    sensitive=set((manifest.get('arm_sensitivity') or {}).get('arm_sensitive_ids',[]))
    if sensitive:splits.append('arm_sensitive')
    def in_split(r,s):return s=='all' or (r['query_id'] in sensitive if s=='arm_sensitive' else r['split']==s)
    arms={a:{s:arm_metrics([r for r in rows if r['arm']==a and in_split(r,s)],[trace_by[(r['query_id'],r['arm'],r['repeat'])] for r in rows if r['arm']==a and in_split(r,s)]) for s in splits} for a in sorted({r['arm'] for r in rows})}
    p=manifest['primary'];treatment=f"{p['treatment']}@{p['budget']}";comparator=f"{p['comparator']}@{p['budget']}"
    pairs=[('primary',treatment,comparator)]+[('secondary',f"{c['treatment']}@{c['budget']}",f"{c['comparator']}@{c['budget']}") for c in manifest.get('secondary',[])]
    for a in arms:
        name,budget=a.split('@')
        if a not in (treatment,comparator) and budget==p['budget'] and not any(a==t for k,t,_ in pairs if k=='secondary'):pairs.append(('exploratory',a,comparator if name!='bm25' else treatment))
    comparisons=[]
    for kind,t,c in pairs:
        if t not in arms or c not in arms:continue
        for s in splits:
            for metric,answerable in (('supported_correct',True),('correct_abstention',False)):
                subset=[r for r in rows if r['arm'] in (t,c) and in_split(r,s) and r['answerable']==answerable]
                if not subset:continue
                field='supported_correct' if answerable else 'correct_decision'
                comparisons.append(dict(paired_cluster_summary(subset,'component',manifest['seed'],metric=field,treatment=t),name=kind,split=s,metric=metric))
    focus='test' if 'test' in splits else 'all' if 'all' in splits else splits[0]
    points=[(a.split('@')[0],v[focus]['inspected_retrieval_tokens']/max(1,v[focus]['questions']),v[focus]['supported_success_rate']) for a,v in arms.items() if a.endswith('@'+p['budget'])]
    report={'run_id':root.name,'input_mode':'raw_question','timing_kind':run['timing_kind'],'scope':'feasibility pilot; AI-proposed unreviewed references; descriptive intervals only when fewer than 12 independent groups',
            'experiment_manifest_sha256':manifest['manifest_sha256'],'primary':p,'arms':arms,'comparisons':comparisons,'rows':rows,
            'costs':{'estimated_api_usd':0,'compute_cost_usd':None,'indexing':run['indexing'],'model_inference':run['model_inference'],'peak_memory_bytes':run['peak_memory_bytes']},
            'references_sha256':hashlib.sha256(Path(reference_path).read_bytes()).hexdigest()}
    write_json(root/'experiment_report.json',report)
    (root/'quality_resource.svg').write_text(svg(points,f'Quality vs inspected retrieval tokens ({focus} split, {p["budget"]}, {root.name})'))
    return report
