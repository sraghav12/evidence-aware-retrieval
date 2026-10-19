"""Offline scoring. References are loaded here, never by inference."""
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal,InvalidOperation
from random import Random
import hashlib,html,json
from pathlib import Path
from pipelines.evidence_aware.contracts import load_query,load_span,digest
from pipelines.evidence_aware.coverage import audit_coverage
from pipelines.evidence_aware.numeric import audit_answer
from pipelines.evidence_aware.contracts import AnswerRecord
from .runner import read_jsonl,write_json


def equal_value(a,b):
    if isinstance(a,str) and isinstance(b,str):
        try:return Decimal(a)==Decimal(b)
        except InvalidOperation:return a==b
    return a==b


def reference_verified(trace,ref):
    """The answer must address the reference requirements and cite its evidence; a matching value alone is not support."""
    requested={r['id'] for r in (trace.get('spec') or {}).get('requirements',[])}
    cited={i for ids in (trace['answer'].get('citations') or {}).values() for i in ids}
    spans={(s['doc_id'],s['start'],s['end']) for s in trace.get('evidence',[]) if s['id'] in cited}
    checks=[]
    if 'requirements' in ref:checks.append(requested==set(ref['requirements']))
    if ref.get('evidence'):checks.append(all((e['doc_id'],e['start'],e['end']) in spans for e in ref['evidence']))
    return bool(checks) and all(checks)


def score_answers(traces,references,documents=None):
    rows=[];seen=set()
    for t in traces:
        key=(t['query_id'],t.get('arm','rule'),t.get('repeat',0))
        if key in seen:raise ValueError('duplicate result')
        seen.add(key)
        if t['query_id'] not in references:raise ValueError('missing reference')
        ref=references[t['query_id']];a=t['answer'];answerable=ref['answerable'];supported=False
        coverage=t.get('coverage_snapshots',[]);complete=bool(coverage and coverage[-1]['complete'])
        source_verified=False;citation_verified=False
        if a['status']=='answered' and t.get('spec'):
            try:
                q=load_query(t['spec']);ss=[load_span(s) for s in t['evidence']]
                source_verified=documents is not None and audit_coverage(q,ss,documents).complete
                citation_verified=audit_answer(AnswerRecord(**a),q,ss).status=='answered'
            except (ValueError,TypeError,KeyError):pass
        answer_correct=a['status']=='answered' and equal_value(a.get('value'),ref.get('value')) and a.get('unit')==ref.get('unit')
        matched=a['status']=='answered' and reference_verified(t,ref)
        supported=bool(answerable and answer_correct and complete and citation_verified and source_verified and matched)
        decision=supported if answerable else a['status']=='abstained'
        prices=[e.get('estimated_usd') for e in t.get('usage',[])];known=all(p is not None for p in prices) and a['status']!='error'
        rows.append(dict(query_id=t['query_id'],arm=t.get('arm','rule'),repeat=t.get('repeat',0),component=ref.get('component',t['query_id']),input_mode=t.get('input_mode','unknown'),answerable=answerable,status=a['status'],reason=a.get('reason',''),supported_correct=None if a['status']=='infeasible' else supported,answer_correct=answer_correct,reference_verified=matched,correct_decision=decision,citation_verified=citation_verified,source_verified=source_verified,gate_complete=complete,gate_false_complete=complete and not source_verified,estimated_api_usd=sum(prices) if known else None,usage_complete=known,review_status=ref.get('review_status','unknown')))
    return rows


def summarize(rows):
    usable=[r for r in rows if r['supported_correct'] is not None];answerable=[r for r in usable if r['answerable']];unanswerable=[r for r in usable if not r['answerable']]
    correct=sum(bool(r['supported_correct']) for r in usable);known=all(r['estimated_api_usd'] is not None for r in rows)
    total=sum(r['estimated_api_usd'] for r in rows) if known else None
    return dict(queries=len(rows),scored_queries=len(usable),answerable=len(answerable),unanswerable=len(unanswerable),supported_success=correct,supported_success_rate=correct/len(answerable) if answerable else None,correct_abstentions=sum(r['correct_decision'] for r in unanswerable),correct_decisions=sum(r['correct_decision'] for r in usable),errors=sum(r['status']=='error' for r in rows),answered=sum(r['status']=='answered' for r in usable),estimated_api_usd=total,compute_cost_usd=None,cost_per_correct_usd=None,cost_per_correct_status='null: local compute is unpriced',annotation_status=sorted({r['review_status'] for r in rows}))


def paired_cluster_summary(rows,cluster_key,seed):
    rows=[r for r in rows if r['arm']!='oracle'];arms=sorted({r['arm'] for r in rows})
    if len(arms)!=2:raise ValueError('exactly two deployable arms required')
    indexed={};components={}
    for r in rows:
        key=(r['arm'],r['query_id'],r.get('repeat',0))
        if key in indexed:raise ValueError('duplicate paired row')
        if r['supported_correct'] is None:raise ValueError('infeasible arm is not scored')
        indexed[key]=r['supported_correct']
        if r['query_id'] in components and components[r['query_id']]!=r[cluster_key]:raise ValueError('inconsistent component')
        components[r['query_id']]=r[cluster_key]
    keys=[{(q,repeat) for a,q,repeat in indexed if a==arm} for arm in arms]
    if keys[0]!=keys[1] or not keys[0]:raise ValueError('unmatched paired rows')
    per_query=defaultdict(list)
    for q,repeat in keys[0]:per_query[q].append(float(indexed[arms[1],q,repeat])-float(indexed[arms[0],q,repeat]))
    clustered=defaultdict(list)
    for q,values in per_query.items():clustered[components[q]].append(sum(values)/len(values))
    clusters=sorted(clustered);rng=Random(seed);boot=[]
    for _ in range(2000):
        values=[x for c in rng.choices(clusters,k=len(clusters)) for x in clustered[c]];boot.append(sum(values)/len(values))
    boot.sort();values=[x for c in clusters for x in clustered[c]]
    return dict(arms=arms,questions=len(per_query),independent_clusters=len(clusters),paired_difference=sum(values)/len(values),ci95=[boot[50],boot[1949]],inference_status='descriptive_only' if len(clusters)<12 else 'pilot_interval_not_confirmatory',resampling_unit=cluster_key,seed=seed)


def build_report(result_dir,reference_path):
    root=Path(result_dir);manifest=json.loads((root/'manifest.json').read_text());raw=(root/'traces.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['traces_sha256']:raise ValueError('trace checksum mismatch')
    traces=[json.loads(x) for x in raw.splitlines()]
    if len(traces)!=manifest['question_count']:raise ValueError('missing query rows')
    if not json.loads((root/'status.json').read_text()).get('complete'):raise ValueError('incomplete run')
    config=json.loads((root/'config.json').read_text())
    if digest(config)!=manifest['config_hash']:raise ValueError('config hash mismatch')
    documents={d['doc_id']:d for d in read_jsonl(config['documents'])}
    if digest(documents)!=manifest['corpus_hash']:raise ValueError('corpus hash mismatch')
    references_list=read_jsonl(reference_path);references={r['query_id']:r for r in references_list}
    if len(references)!=len(references_list):raise ValueError('duplicate reference')
    if {t['query_id'] for t in traces}!=set(references):raise ValueError('question set differs from references')
    rows=score_answers(traces,references,documents)
    report={'scope':'engineering pilot; not independent human validation','manifest':manifest,'summary':summarize(rows),'rows':rows,'limitations':['Synthetic fixtures are functional checks, not evidence of accuracy or savings.','Real development data, when used, are not a locked test.','Whitespace token estimates are not billed provider tokens.','Local compute is unpriced.','No independent human certification.'],'references_sha256':hashlib.sha256(Path(reference_path).read_bytes()).hexdigest()}
    write_json(root/'report.json',report)
    blocks=[]
    for t in traces:
        blocks.append('<details><summary>'+html.escape(t['query_id']+' — '+t['answer']['status'])+'</summary><pre>'+html.escape(json.dumps(t,indent=2,sort_keys=True))+'</pre></details>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Evidence-aware retrieval report</title><style>body{max-width:1000px;margin:40px auto;font:16px system-ui;padding:0 20px}pre{white-space:pre-wrap;background:#f3f5f8;padding:16px}summary{padding:12px;cursor:pointer}details{border-bottom:1px solid #ddd}</style><h1>Project 2: evidence-aware retrieval</h1><p>Engineering evidence. No independently validated accuracy or savings claim.</p><h2>Summary</h2><pre>'+html.escape(json.dumps(report['summary'],indent=2))+'</pre><h2>Trace inspection</h2>'+''.join(blocks)+'</html>'
    (root/'report.html').write_text(page)
    return report
