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
    groups=[]
    for r in sorted(rows,key=lambda r:r['query_id']):
        keys={f'{k}:{x}' for k in ('entity_ids','source_ancestry','derivation_ancestry') for x in r[k]}
        hits=[g for g in groups if keys & g['keys']]
        group={'keys':keys,'rows':[r]}
        for g in hits:group['keys']|=g['keys'];group['rows']+=g['rows'];groups.remove(g)
        groups.append(group)
    rng=Random(seed)
    for g in sorted(groups,key=lambda g:min(r['query_id'] for r in g['rows'])):
        split='development' if any(r['v1_descendant'] for r in g['rows']) else rng.choices(['train','development','test'],[.6,.2,.2])[0]
        component=digest(sorted(r['query_id'] for r in g['rows']))[:12]
        for r in g['rows']:r.update(split=split,component=component)
    m={'schema_version':2,'seed':seed,'rows':rows};validate_manifest(m);return m


def validate_manifest(manifest):
    seen={};ids=set()
    for r in manifest['rows']:
        if r['query_id'] in ids:raise ValueError('duplicate query')
        ids.add(r['query_id'])
        if r['split'] not in {'train','development','test','smoke'}:raise ValueError('invalid split')
        if r.get('v1_descendant') and r['split']!='development':raise ValueError('v1 descendant is development only')
        for k in ('entity_ids','source_ancestry','derivation_ancestry','component'):
            values=[r[k]] if k=='component' else r.get(k,[])
            for x in values:
                key=(k,x)
                if key in seen and seen[key]!=r['split']:raise ValueError(f'forbidden overlap: {k}')
                seen[key]=r['split']
