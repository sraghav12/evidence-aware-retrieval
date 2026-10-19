"""Frozen experiment definition: matched arms, budgets, run order and estimates. Never executes a provider call."""
from pathlib import Path
from random import Random
import hashlib,re
from pipelines.evidence_aware.contracts import digest
from pipelines.evidence_aware.units import build_units
from pipelines.evidence_aware.policy import POLICIES
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query,UnsupportedQuery
from pipelines.evidence_aware.extraction import extract_candidates

ROOT=Path(__file__).resolve().parents[2]
SHARED={'gate':'audit_coverage_v2','answer_audit':'audit_answer_v2','executor':'decimal_executor_v1'}
STAGE_DEFAULTS={'stage_context_tokens':8192,'cheap_context_tokens':8192,'retrieval_tokens_total':24576,'verification_tokens_total':24576,'deadline_ms':30000,'max_packed_sections':12}
POOLS={'cheap_pool':20,'escalated_pool':60}
SCRIPTS=('scripts/run_evidence_v2.py','scripts/report_evidence_v2.py','scripts/prepare_evidence_v2.py','scripts/draft_pilot_v2.py','scripts/freeze_experiment_v2.py','scripts/run_experiment_v2.py','requirements-evidence-v2-compat.lock')
STRATEGY={'bm25':(),'dense':('dense',),'hybrid_rrf':('dense',),'hybrid_rrf_rerank':('dense','reranker')}
GATES={'audit_coverage_v2','audit_coverage_v3','audit_coverage_v4'}
PROBE_DEFAULTS={'probe_units_per_filing':3,'probe_tokens':2048}
MATCHED=('max_context_tokens','max_output_tokens','answer_audit','executor','answerer','model_revision','prompt_hash','decoding','units_hash','stage_limits')


def answerer_identity(config):
    kind=config.get('answerer','decimal_executor')
    if kind=='decimal_executor':return kind,'none_executor',None,None
    if kind!='model_qa':raise ValueError(f'unknown answerer: {kind}')
    revision,prompt,decoding=config.get('model_revision'),config.get('prompt_hash'),config.get('decoding')
    if not revision or not isinstance(prompt,str) or not re.fullmatch('[0-9a-f]{64}',prompt) or not isinstance(decoding,dict):
        raise ValueError('model answerer requires pinned model_revision, 64-hex prompt_hash and decoding')
    return kind,revision,prompt,decoding


def source_hashes():
    files=sorted((ROOT/'pipelines/evidence_aware').glob('*.py'))+sorted((ROOT/'evaluation/evidence_aware').glob('*.py'))+[ROOT/f for f in SCRIPTS if (ROOT/f).is_file()]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def arm_sensitivity(questions,documents,aliases,references):
    """Rows no arm can change: deterministic parse failures and companies with no extracted cell. Uses no retrieval or answers."""
    cells={s.entity_id for s in extract_candidates(build_units(documents),documents)};parse={};zero={};sensitive=[]
    for q in questions:
        try:spec=parse_query(q['question'],q['as_of'],aliases,build_fiscal_calendar(documents,q['as_of']))
        except UnsupportedQuery as e:parse[str(e)]=parse.get(str(e),0)+1;continue
        if any(r.entity_id not in cells for r in spec.requirements):
            k='answerable' if references[q['id']]['answerable'] else 'unanswerable';zero[k]=zero.get(k,0)+1;continue
        sensitive.append(q['id'])
    answerable=sum(references[i]['answerable'] for i in sensitive)
    return {'parse_invariant':parse,'zero_cell_invariant':zero,'arm_sensitive':len(sensitive),'arm_sensitive_answerable':answerable,'arm_sensitive_unanswerable':len(sensitive)-answerable,
            'arm_sensitive_groups':len({references[i].get('component',i) for i in sensitive}),'arm_sensitive_ids':sensitive}


def engine_config(arm):
    """The exact engine configuration an arm runs with; its hash is frozen per arm."""
    return dict(arm['stage_limits'],input_mode='raw_question',provider_enabled=False,max_usd=0,policy=arm['policy'],gate=arm['gate'],max_context_tokens=arm['max_context_tokens'],max_output_tokens=arm['max_output_tokens'])


def planned_runs(questions,arms,repeats,seed):
    """Paired fresh runs of every available, non-duplicate arm, in one seeded random order."""
    runs=[(q['id'],a['name'],a['budget'],r) for q in questions for a in arms if a['status']=='available' and not a['same_run_as'] for r in range(repeats)]
    Random(seed).shuffle(runs);return runs


def build_experiment_manifest(config,documents,questions,available_rankers,attachments=None):
    if config.get('provider_enabled') or config.get('max_usd',0)!=0:raise ValueError('experiment freeze keeps live execution disabled')
    if config.get('max_output_tokens')!=512:raise ValueError('final output stays 512 tokens')
    kind,revision,prompt,decoding=answerer_identity(config)
    units_hash=digest([[u.id,u.doc_id,u.start,u.end] for u in build_units(documents)])
    gate=config.get('gate','audit_coverage_v2')
    if gate not in GATES:raise ValueError(f'unknown gate: {gate}')
    profiles=config['budget_profiles'];limits=dict({k:config.get(k,v) for k,v in {**STAGE_DEFAULTS,**PROBE_DEFAULTS}.items()},**POOLS)
    if 'cheap_context_tokens' not in config:limits['cheap_context_tokens']=limits['stage_context_tokens']
    if len({p['name'] for p in profiles})!=len(profiles):raise ValueError('duplicate budget profile')
    arms=[]
    for p in profiles:
        common=dict(budget=p['name'],max_context_tokens=p['max_context_tokens'],max_output_tokens=512,answerer=kind,model_revision=revision,prompt_hash=prompt,decoding=decoding,units_hash=units_hash,stage_limits=limits,**dict(SHARED,gate=gate))
        policies=config.get('scheduling_arms',sorted(POLICIES))
        for name in config.get('strategy_arms',list(STRATEGY)):
            needs=STRATEGY[name];missing=[n for n in needs if n not in available_rankers]
            arms.append(dict(common,name=name,track='strategy',policy='coverage_rule_v1',backend=name,status='unavailable' if missing else 'available',
                             reason=f'no hash-verified pinned local {" and ".join(missing)} model' if missing else '',
                             ranker_revisions={n:available_rankers[n] for n in needs if n in available_rankers},same_run_as='coverage_rule_v1' if name=='bm25' and 'coverage_rule_v1' in policies else None))
        for policy in policies:
            if policy not in POLICIES:raise ValueError(f'unknown policy: {policy}')
            arms.append(dict(common,name=policy,track='scheduling',policy=policy,backend='bm25',status='available',reason='',ranker_revisions={},same_run_as=None))
        for g in config.get('gate_ablation',[]):
            if g['gate'] not in GATES or g['policy'] not in POLICIES:raise ValueError('invalid gate ablation arm')
            needs=STRATEGY[g['backend']];missing=[n for n in needs if n not in available_rankers]
            arms.append(dict(common,gate=g['gate'],name=g['name'],track='gate_ablation',policy=g['policy'],backend=g['backend'],status='unavailable' if missing else 'available',
                             reason=f'no hash-verified pinned local {" and ".join(missing)} model' if missing else '',ranker_revisions={n:available_rankers[n] for n in needs if n in available_rankers},same_run_as=None))
    for a in arms:a['engine_config_sha256']=digest(engine_config(a))
    primary=config['primary'];names={a['name'] for a in arms if a['track']=='scheduling'}
    if primary['treatment'] not in names or primary['comparator'] not in names or primary['budget'] not in {p['name'] for p in profiles}:
        raise ValueError('primary comparison must use available scheduling arms and a declared budget')
    every={(a['name'],a['budget']) for a in arms if a['status']=='available'}
    for c in config.get('secondary',[]):
        if (c['treatment'],c['budget']) not in every or (c['comparator'],c['budget']) not in every:raise ValueError(f'secondary comparison references unavailable arms: {c["name"]}')
    runs=planned_runs(questions,arms,config.get('repeats',1),config['seed'])
    per_question=sum(a['status']=='available' and not a['same_run_as'] for a in arms)
    model=kind=='model_qa'
    m={'schema_version':2,'status':'frozen_not_executed','live_execution':'disabled','arms':arms,'primary':primary,'secondary':config.get('secondary',[]),'budget_profiles':profiles,'repeats':config.get('repeats',1),'seed':config['seed'],
       'failure_policy':'errors and timeouts stay in denominators; unavailable arms are reported, never substituted; no rerun on outcome',
       'analysis':'paired component-cluster bootstrap (2000 resamples, seed fixed); answerable supported success and unanswerable correct abstention reported separately; fewer than 12 independent test groups is descriptive only',
       'run_order_sha256':digest(runs),'run_count':len(runs),'corpus_hash':digest(documents),'questions_hash':digest(questions),'units_hash':units_hash,'source_sha256':source_hashes(),
       'config_hash':digest({k:v for k,v in config.items() if k!='output'}),
       'estimates':{'available_arm_runs_per_question':per_question,'provider_requests':len(questions)*per_question*config.get('repeats',1) if model else 0,
                    'max_input_tokens_per_request':max(p['max_context_tokens'] for p in profiles) if model else 0,'max_output_tokens_per_request':512 if model else 0,
                    'estimated_usd':None,'price_status':'no provider selected or priced; live execution disabled'}}
    m.update(attachments or {});m['manifest_sha256']=digest(m);validate_experiment(m);return m


def validate_experiment(manifest):
    body={k:v for k,v in manifest.items() if k!='manifest_sha256'}
    if manifest.get('live_execution')!='disabled':raise ValueError('live execution must stay disabled')
    for p in manifest['budget_profiles']:
        rows=[a for a in manifest['arms'] if a['budget']==p['name']]
        for k in MATCHED:
            if len({digest(a[k]) for a in rows})!=1:raise ValueError(f'unmatched {k} in {p["name"]}')
    if len({a['gate'] for a in manifest['arms'] if a['track']!='gate_ablation'})!=1:raise ValueError('scheduling and strategy arms must share one gate')
    for a in manifest['arms']:
        if a['gate'] not in GATES:raise ValueError('unknown gate')
        if a['max_output_tokens']!=512:raise ValueError('final output stays 512 tokens')
        if a['status']=='unavailable' and not a['reason']:raise ValueError('unavailable arm needs a reason')
    if digest(body)!=manifest.get('manifest_sha256'):raise ValueError('manifest hash missing or mismatched')
