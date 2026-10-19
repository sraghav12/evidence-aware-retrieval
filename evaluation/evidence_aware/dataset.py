"""Conservative split grouping; this module never supplies inference features."""
from dataclasses import asdict
from random import Random
from pipelines.evidence_aware.contracts import iso_date,digest


def eligible(disclosed_at,as_of): return iso_date(disclosed_at)<=iso_date(as_of)


def build_split_manifest(queries,documents,seed,lineage=None):
    lineage=lineage or {}
    rows=[]
    for q in queries:
        meta=lineage.get(q.id,{})
        entities=sorted({r.entity_id for r in q.requirements})
        sources=set(meta.get('source_ancestry',[]))
        for d in documents:
            if d.get('entity_id') in entities:sources.add(d['doc_id'])
        rows.append(dict(query_id=q.id,entity_ids=entities,source_ancestry=sorted(sources),derivation_ancestry=meta.get('derivation_ancestry',[]),v1_descendant=bool(meta.get('v1_descendant',False))))
    if len({r['query_id'] for r in rows})!=len(rows):raise ValueError('duplicate question')
    rng=Random(seed)
    for g in components(rows):
        split='development' if any(r['v1_descendant'] for r in g['rows']) else rng.choices(['train','development','test'],[.6,.2,.2])[0]
        component=digest(sorted(r['query_id'] for r in g['rows']))[:12]
        for r in g['rows']:r.update(split=split,component=component)
    m={'schema_version':2,'seed':seed,'rows':rows};validate_manifest(m);return m


def components(rows):
    """Connect rows sharing an entity, source or derivation ancestor. Public grammar templates never connect rows."""
    groups=[]
    for r in sorted(rows,key=lambda r:r['query_id']):
        keys={f'{k}:{x}' for k in ('entity_ids','source_ancestry','derivation_ancestry') for x in r[k]}
        hits=[g for g in groups if keys & g['keys']]
        group={'keys':keys,'rows':[r]}
        for g in hits:group['keys']|=g['keys'];group['rows']+=g['rows'];groups.remove(g)
        groups.append(group)
    return sorted(groups,key=lambda g:min(r['query_id'] for r in g['rows']))


def build_pilot_manifest(rows,seed):
    """Development vs locked-test split by independent component; never forced when components collapse."""
    rows=[dict(r) for r in rows]
    if len({r['query_id'] for r in rows})!=len(rows):raise ValueError('duplicate question')
    groups=components(rows);locked=[g for g in groups if not any(r['development_only'] for r in g['rows'])]
    order=list(range(len(locked)));Random(seed).shuffle(order);test={id(locked[i]) for i in order[:len(locked)//2]} if len(locked)>=2 else set()
    for g in groups:
        component=digest(sorted(r['query_id'] for r in g['rows']))[:12]
        for r in g['rows']:r.update(split='test' if id(g) in test else 'development',component=component)
    count=lambda s:len({r['component'] for r in rows if r['split']==s})
    templates={}
    for r in rows:templates[r['template']]=templates.get(r['template'],0)+1
    m={'schema_version':2,'seed':seed,'rows':sorted(rows,key=lambda r:r['query_id']),'effective_groups':{'total':len(groups),'development':count('development'),'test':count('test')},
       'grammar_overlap':templates,'locked_test':'feasible' if test else 'infeasible: fewer than 2 eligible independent groups',
       'inference_status':'descriptive_only' if count('test')<12 else 'pilot_interval_not_confirmatory'}
    validate_manifest(m);return m


def validate_manifest(manifest):
    seen={};ids=set()
    for r in manifest['rows']:
        if r['query_id'] in ids:raise ValueError('duplicate query')
        ids.add(r['query_id'])
        if r['split'] not in {'train','development','test','smoke'}:raise ValueError('invalid split')
        if r.get('v1_descendant') and r['split']!='development':raise ValueError('v1 descendant is development only')
        if r.get('development_only') and r['split']!='development':raise ValueError('development-only ancestry outside development')
        for k in ('entity_ids','source_ancestry','derivation_ancestry','component'):
            values=[r[k]] if k=='component' else r.get(k,[])
            for x in values:
                key=(k,x)
                if key in seen and seen[key]!=r['split']:raise ValueError(f'forbidden overlap: {k}')
                seen[key]=r['split']
