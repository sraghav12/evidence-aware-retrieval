"""Strict public contracts. Evaluation annotations are not inference inputs."""
from dataclasses import dataclass, field, fields, asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json
import re


def iso_date(value):
    if not isinstance(value,str): raise ValueError('date must be ISO string')
    try: date.fromisoformat(value)
    except (ValueError,TypeError) as e: raise ValueError('invalid ISO date') from e
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError('date granularity is a day')
    return value


def decimal_string(value):
    if not isinstance(value,str): raise ValueError('decimal must be a string')
    try: number=Decimal(value)
    except InvalidOperation as e: raise ValueError('invalid decimal') from e
    if not number.is_finite(): raise ValueError('nonfinite decimal')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def manifest_hash(paths):
    return digest([{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths,key=str)])


def strict(cls,record):
    if not isinstance(record,dict) or set(record)!={f.name for f in fields(cls)}:
        raise ValueError(f'{cls.__name__}: missing or unknown fields')
    try: return cls(**record)
    except (TypeError,KeyError) as e: raise ValueError(f'invalid {cls.__name__}') from e


@dataclass(frozen=True)
class QuestionInput:
    id:str
    question:str
    as_of:str

    def __post_init__(self):
        if not all(isinstance(x,str) and x.strip() for x in (self.id,self.question)): raise ValueError('empty question/id')
        iso_date(self.as_of)


@dataclass(frozen=True)
class Requirement:
    id:str
    entity_id:str
    metric:str
    period_start:str
    period_end:str
    fiscal_year:int
    unit:str
    accounting_basis:str

    def __post_init__(self):
        for x in (self.id,self.entity_id,self.metric,self.unit,self.accounting_basis):
            if not isinstance(x,str) or not x: raise ValueError('requirement strings required')
        iso_date(self.period_start);iso_date(self.period_end)
        if self.period_start>self.period_end or type(self.fiscal_year) is not int: raise ValueError('invalid period/year')


@dataclass(frozen=True)
class Operation:
    kind:str
    operands:tuple[str,...]

    def __post_init__(self):
        if self.kind not in {'extract','sum','growth','ranking'}: raise ValueError('unsupported operation')
        if not self.operands or len(set(self.operands))!=len(self.operands): raise ValueError('invalid operands')
        if self.kind=='extract' and len(self.operands)!=1:raise ValueError('extract needs one operand')
        if self.kind=='growth' and len(self.operands)!=2:raise ValueError('growth needs old/new')


@dataclass(frozen=True)
class QuerySpec(QuestionInput):
    requirements:tuple[Requirement,...]
    operation:Operation

    def __post_init__(self):
        super().__post_init__()
        ids=[r.id for r in self.requirements]
        if len(set(ids))!=len(ids) or set(ids)!=set(self.operation.operands): raise ValueError('invalid requirement references')


@dataclass(frozen=True)
class EvidenceSpan:
    id:str
    doc_id:str
    accession:str
    doc_sha256:str
    entity_id:str
    disclosed_at:str
    start:int
    end:int
    quote:str
    metric:str
    period_start:str
    period_end:str
    fiscal_year:int
    unit:str
    value:str
    accounting_basis:str
    table_headers:tuple[str,...]
    source_url:str

    def __post_init__(self):
        iso_date(self.disclosed_at);iso_date(self.period_start);iso_date(self.period_end);decimal_string(self.value)
        if not re.fullmatch('[0-9a-f]{64}',self.doc_sha256): raise ValueError('invalid source hash')
        if type(self.start) is not int or type(self.end) is not int or self.start<0 or self.end<=self.start:raise ValueError('invalid offsets')
        if self.period_start>self.period_end or type(self.fiscal_year) is not int:raise ValueError('invalid evidence period')
        if not all(isinstance(x,str) and x for x in (self.id,self.doc_id,self.accession,self.entity_id,self.metric,self.unit,self.accounting_basis,self.source_url,self.quote)):raise ValueError('invalid evidence strings')
        if not self.table_headers or not all(isinstance(x,str) and x for x in self.table_headers):raise ValueError('invalid table headers')


@dataclass(frozen=True)
class CoverageResult:
    complete:bool
    supported_requirement_ids:tuple[str,...]
    missing_requirement_ids:tuple[str,...]
    conflicts:tuple[str,...]
    audited_span_ids:tuple[str,...]


@dataclass(frozen=True)
class AnswerRecord:
    status:str
    value:object=None
    unit:str=''
    citations:dict=field(default_factory=dict)
    reason:str=''


@dataclass
class BudgetState:
    context_tokens_remaining:int=8192
    output_tokens_remaining:int=512
    calls_remaining:int=1
    max_usd:float=0
    estimated_usd_reserved:float=0
    deadline_ms:int=30000
    retrieval_tokens_remaining:int=24576
    verification_tokens_remaining:int=24576


@dataclass(frozen=True)
class RoutingState:
    stage_index:int=1
    attempted_actions:tuple[str,...]=('cheap_search',)


@dataclass(frozen=True)
class RouteDecision:
    action:str
    reason_codes:tuple[str,...]
    missing_requirement_ids:tuple[str,...]=()


@dataclass(frozen=True)
class RetrievalUnit:
    id:str
    doc_id:str
    start:int
    end:int
    text:str
    section_id:str
    header_context:tuple[str,...]=()


@dataclass
class UsageEvent:
    event_id:str
    query_id:str
    stage:str
    provider:str='local'
    model_revision:str='none'
    input_tokens:int|None=0
    output_tokens:int|None=0
    elapsed_ms:float=0
    attempts:int=1
    status:str='ok'
    estimated_usd:float|None=0
    billed_usd:float|None=None
    price_version:str|None=None
    cache_mode:str='fresh_local'
    peak_memory_bytes:int|None=None
    token_measurement:str='whitespace_estimate'


@dataclass
class RunTrace:
    query_id:str
    question:str
    as_of:str
    input_mode:str
    query_hash:str
    config_hash:str
    corpus_hash:str
    parser_version:str='controlled_v1'
    policy_version:str='coverage_rule_v1'
    spec:dict|None=None
    decisions:list=field(default_factory=list)
    coverage_snapshots:list=field(default_factory=list)
    packed_ids:list=field(default_factory=list)
    packing:list=field(default_factory=list)
    selected_units:list=field(default_factory=list)
    evidence:list=field(default_factory=list)
    answer:AnswerRecord=field(default_factory=lambda:AnswerRecord('error',reason='not_run'))
    usage:list=field(default_factory=list)
    timing_kind:str='fresh_local_executor'


def load_question(record): return strict(QuestionInput,record)


def load_query(record):
    record=dict(record)
    if 'requirements' not in record or 'operation' not in record:raise ValueError('missing contracts')
    record['requirements']=tuple(strict(Requirement,r) for r in record['requirements'])
    op=record['operation']
    if not isinstance(op,dict) or set(op)!={'kind','operands'} or not isinstance(op['operands'],(list,tuple)) or not all(isinstance(x,str) for x in op['operands']):raise ValueError('invalid operation')
    record['operation']=Operation(op['kind'],tuple(op['operands']))
    return strict(QuerySpec,record)


def load_span(record):
    record=dict(record)
    if not isinstance(record.get('table_headers'),(list,tuple)):raise ValueError('invalid headers')
    record['table_headers']=tuple(record['table_headers'])
    return strict(EvidenceSpan,record)
