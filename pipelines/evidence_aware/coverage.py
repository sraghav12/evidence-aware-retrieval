"""Coverage is an exact source/provenance check, not a confidence score."""
from decimal import Decimal
import hashlib
from .contracts import CoverageResult
from .units import build_units
from .extraction import extract_candidates

SCALES={'USD':Decimal(1),'USD_thousand':Decimal(1000),'USD_million':Decimal(1000000),'USD_billion':Decimal(1000000000)}


def same_quantity(requirement,span):
    return all(getattr(requirement,k)==getattr(span,k) for k in ('entity_id','metric','period_start','period_end','fiscal_year')) and (requirement.unit==span.unit or requirement.unit in SCALES and span.unit in SCALES)


def matches(requirement,span):
    return same_quantity(requirement,span) and requirement.accounting_basis==span.accounting_basis


def converted(span,requirement):
    return Decimal(span.value)*SCALES.get(span.unit,Decimal(1))/SCALES.get(requirement.unit,Decimal(1))


def audit_coverage(spec,spans,documents):
    # Re-extract source-derived fields; a forged period/header/value cannot pass by supplying plausible metadata.
    canonical={s.id:s for s in extract_candidates(build_units(documents),documents)}
    valid=[]
    for s in spans:
        d=documents.get(s.doc_id)
        if not d or s.disclosed_at>spec.as_of or s!=canonical.get(s.id):continue
        if hashlib.sha256(d['text'].encode()).hexdigest()!=s.doc_sha256 or d['text'][s.start:s.end]!=s.quote:continue
        valid.append(s)
    supported=[];missing=[];conflicts=[];audited=[]
    for r in spec.requirements:
        # Any eligible basis (reported, restated) for the same quantity can contradict the requested one.
        related=[s for s in valid if same_quantity(r,s)];candidates=[s for s in related if matches(r,s)]
        if len({converted(s,r) for s in related})>1:conflicts.append(r.id);missing.append(r.id)
        elif candidates:supported.append(r.id);audited.extend(s.id for s in candidates)
        else:missing.append(r.id)
    return CoverageResult(not missing and not conflicts,tuple(supported),tuple(missing),tuple(conflicts),tuple(sorted(set(audited))))
