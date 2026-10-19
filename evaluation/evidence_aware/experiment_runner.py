"""Execute a frozen experiment manifest exactly: same corpus, questions, code, config and run order, or refuse."""
from dataclasses import asdict,replace
from pathlib import Path
from time import perf_counter
import json,platform,resource,subprocess,sys
from pipelines.evidence_aware.contracts import digest,load_question,RunTrace,AnswerRecord
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query,UnsupportedQuery
from pipelines.evidence_aware.engine import run_spec
from .experiment import planned_runs,source_hashes,validate_experiment,engine_config,ROOT
from .runner import build_backends,write_json


class FreezeMismatch(ValueError):pass


def check_freeze(manifest,config,documents,questions):
    if digest(documents)!=manifest['corpus_hash']:raise FreezeMismatch('corpus differs from freeze')
    if digest(questions)!=manifest['questions_hash']:raise FreezeMismatch('questions differ from freeze')
    if source_hashes()!=manifest['source_sha256']:raise FreezeMismatch('source code differs from freeze')
    if digest({k:v for k,v in config.items() if k!='output'})!=manifest['config_hash']:raise FreezeMismatch('config differs from freeze')
    if digest(planned_runs(questions,manifest['arms'],manifest['repeats'],manifest['seed']))!=manifest['run_order_sha256']:raise FreezeMismatch('run order differs from freeze')
    try:validate_experiment(manifest)
    except ValueError as e:raise FreezeMismatch(str(e)) from e


def peak_memory():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)


def run_experiment(manifest,config,documents,questions,rankers,output):
    check_freeze(manifest,config,documents,questions)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_json(output/'config.json',config);write_json(output/'experiment_manifest.json',manifest)
    arms={(a['name'],a['budget']):a for a in manifest['arms']}
    backends={};indexing=None
    for a in manifest['arms']:
        if a['status']=='available' and not a['same_run_as'] and a['backend'] not in backends:
            backends[a['backend']],_,stats,_=build_backends(dict(config,backend=a['backend']),documents,rankers)
            indexing=indexing or stats
    usage_before={r:x.usage() for r,x in rankers.items()}
    aliases=config.get('aliases') or {d['entity_id'].split(':')[-1].casefold():d['entity_id'] for d in documents.values()}
    by_id={q['id']:load_question(q) for q in questions};calendars={};rows=0;errors=0
    with open(output/'traces.jsonl','w',encoding='utf-8') as sink:
        for index,(qid,name,budget,repeat) in enumerate(planned_runs(questions,manifest['arms'],manifest['repeats'],manifest['seed'])):
            arm=arms[(name,budget)];q=by_id[qid];cfg=engine_config(arm);start=perf_counter()
            if digest(cfg)!=arm['engine_config_sha256']:raise FreezeMismatch('arm engine config differs from freeze')
            calendar=calendars.setdefault(q.as_of,build_fiscal_calendar(documents,q.as_of))
            try:trace=run_spec(replace(parse_query(q.question,q.as_of,aliases,calendar),id=qid),backends[arm['backend']],documents,cfg,None)
            except UnsupportedQuery as e:trace=RunTrace(qid,q.question,q.as_of,'raw_question',digest(asdict(q)),digest(cfg),manifest['corpus_hash'],policy_version=arm['policy'],answer=AnswerRecord('abstained',reason=str(e)))
            row=asdict(trace);row.update(arm=f'{name}@{budget}',budget=budget,repeat=repeat,order_index=index,wall_ms=(perf_counter()-start)*1000,peak_memory_bytes=peak_memory())
            errors+=row['answer']['status']=='error';rows+=1
            sink.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');sink.flush()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    write_json(output/'manifest.json',{'schema_version':2,'experiment_manifest_sha256':manifest['manifest_sha256'],'git_commit':commit,'git_dirty':dirty,'python':platform.python_version(),'platform':platform.platform(),
        'timing_kind':'fresh_local','provider_calls':0,'api_cost_usd':0,'compute_cost_usd':None,'run_count':rows,'indexing':indexing,'peak_memory_bytes':peak_memory(),'peak_memory_scope':'process_high_water',
        'model_inference':{r:{k:v-usage_before[r][k] for k,v in x.usage().items()} for r,x in rankers.items()},'ranker_revisions':{r:x.revision for r,x in rankers.items()},
        'traces_sha256':__import__('hashlib').sha256((output/'traces.jsonl').read_bytes()).hexdigest()})
    write_json(output/'status.json',{'complete':rows==manifest['run_count'],'rows':rows,'errors':errors})
    return output
