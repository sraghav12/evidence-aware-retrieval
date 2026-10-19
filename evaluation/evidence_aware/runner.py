"""Question-only inference runner. Reference files belong exclusively to reporting."""
from dataclasses import asdict,replace
from pathlib import Path
import hashlib,json,platform,resource,subprocess,sys
from pipelines.evidence_aware.contracts import load_question,load_query,digest,RunTrace,AnswerRecord
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query,UnsupportedQuery
from pipelines.evidence_aware.retrieval import BM25Backend,DenseBackend,HybridBackend,RerankBackend
from pipelines.evidence_aware.engine import run_spec
from pipelines.evidence_aware.policy import POLICIES


def read_jsonl(path):
    with open(path,encoding='utf-8') as f:return [json.loads(line) for line in f if line.strip()]


def write_json(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')


BACKENDS={'bm25':(),'dense':('dense',),'hybrid_rrf':('dense',),'hybrid_rrf_rerank':('dense','reranker')}


def build_backends(config,documents,preloaded=None):
    """Every backend wraps the same per-stage BM25 units, eligibility and selection; model arms add only a ranking."""
    name=config.get('backend','bm25');rankers={}
    if BACKENDS[name]:
        if preloaded:rankers={r:preloaded[r] for r in BACKENDS[name]}
        else:
            from pipelines.evidence_aware.onnx_rankers import load_rankers
            rankers=load_rankers(roles=BACKENDS[name])
    stages={}
    for s in ('cheap_search','section_search','expanded_search'):
        b=BM25Backend(documents,s,candidate_pool=20 if s=='cheap_search' else 60,max_units=config.get('max_packed_sections',12))
        if name=='dense':b=DenseBackend(b,rankers['dense'])
        elif name!='bm25':
            b=HybridBackend(b,rankers['dense'])
            if name=='hybrid_rrf_rerank':b=RerankBackend(b,rankers['reranker'],pool=60)
        stages[s]=b
    indexing=None
    if 'dense' in rankers:
        before=dict(rankers['dense'].index_stats);rankers['dense'].index(stages['cheap_search'].units)
        indexing=dict(rankers['dense'].index_stats,reused_index=rankers['dense'].index_stats==before,peak_memory_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),scope='process_high_water_after_index')
    return stages,{r:x.revision for r,x in rankers.items()},indexing,rankers


def validate_config(config):
    if any('gold' in k or 'reference' in k or 'oracle' in k for k in config):raise ValueError('evaluation configuration forbidden in inference')
    if config.get('provider_enabled',False) or config.get('max_usd',0)!=0:raise ValueError('live provider arm unavailable; zero-budget offline mode only')
    if config.get('input_mode','raw_question') not in {'raw_question','diagnostic_spec'}:raise ValueError('invalid input mode')
    if config.get('policy','coverage_rule_v1') not in POLICIES:raise ValueError('unknown policy')
    if config.get('backend','bm25') not in BACKENDS:raise ValueError('unknown backend')
    for k in ('max_context_tokens','max_output_tokens','cheap_context_tokens','stage_context_tokens','retrieval_tokens_total','verification_tokens_total','deadline_ms','max_packed_sections'):
        if k in config and (type(config[k]) is not int or config[k]<0):raise ValueError(f'invalid budget: {k}')


def run(config,queries=None,rankers=None):
    validate_config(config)
    docs_list=read_jsonl(config['documents']);documents={d['doc_id']:d for d in docs_list}
    if len(documents)!=len(docs_list):raise ValueError('duplicate document ID')
    for d in docs_list:
        if hashlib.sha256(d['text'].encode()).hexdigest()!=d['sha256']:raise ValueError('source hash mismatch')
    raw=read_jsonl(config['queries']) if queries is None else queries
    mode=config.get('input_mode','raw_question')
    questions=[(load_question(r) if mode=='raw_question' else load_query(r)) if isinstance(r,dict) else r for r in raw]
    if len({q.id for q in questions})!=len(questions):raise ValueError('duplicate query ID')
    output=Path(config['output']);output.mkdir(parents=True,exist_ok=False)
    write_json(output/'config.json',config)
    aliases=config.get('aliases') or {d['entity_id'].split(':')[-1].casefold():d['entity_id'] for d in documents.values()}
    backends,ranker_revisions,indexing,rankers=build_backends(config,documents,rankers)
    usage_before={r:x.usage() for r,x in rankers.items()}
    traces=[]
    with open(output/'traces.jsonl','w',encoding='utf-8') as sink:
        for question in questions:
            try:
                if mode=='raw_question':
                    spec=parse_query(question.question,question.as_of,aliases,build_fiscal_calendar(documents,question.as_of));spec=replace(spec,id=question.id)
                else:spec=question
                trace=run_spec(spec,backends,documents,config,None)
            except UnsupportedQuery as e:
                trace=RunTrace(question.id,question.question,question.as_of,mode,digest(asdict(question)),digest(config),digest(documents),answer=AnswerRecord('abstained',reason=str(e)))
            except Exception as e:
                trace=RunTrace(question.id,question.question,question.as_of,mode,digest(asdict(question)),digest(config),digest(documents),answer=AnswerRecord('error',reason=type(e).__name__))
            for event in trace.usage:event['peak_memory_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            row=asdict(trace);traces.append(row);sink.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');sink.flush()
    sha=hashlib.sha256((output/'traces.jsonl').read_bytes()).hexdigest()
    root=Path(__file__).resolve().parents[2]
    manifest={'schema_version':2,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'python':platform.python_version(),'platform':platform.platform(),'machine':platform.machine(),'peak_memory_scope':'process_high_water','tokenizer':'whitespace_estimate','compute':'python_cpu','backend':config.get('backend','bm25'),'ranker_revisions':ranker_revisions,'indexing':indexing,'model_inference':{r:{k:v-usage_before[r][k] for k,v in x.usage().items()} for r,x in rankers.items()},'seed':config.get('seed',11),'model_revision':'none_executor','prompt_hash':None,'config_hash':digest(config),'corpus_hash':digest(documents),'questions_hash':digest([asdict(q) for q in questions]),'traces_sha256':sha,'dependency_lock_sha256':hashlib.sha256((root/'requirements-evidence-v2-compat.lock').read_bytes()).hexdigest(),'question_count':len(questions),'provider_calls':0,'api_cost_usd':0,'compute_cost_usd':None,'input_mode':mode}
    sources=sorted((root/'pipelines/evidence_aware').glob('*.py'))+sorted((root/'evaluation/evidence_aware').glob('*.py'))+[root/'scripts/run_evidence_v2.py']
    manifest['source_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    manifest['git_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
    write_json(output/'manifest.json',manifest)
    write_json(output/'status.json',{'complete':True,'rows':len(traces),'errors':sum(t['answer']['status']=='error' for t in traces)})
    with open(output/'usage.jsonl','w') as f:
        for t in traces:
            for e in t['usage']:f.write(json.dumps(e,sort_keys=True)+'\n')
    return output
