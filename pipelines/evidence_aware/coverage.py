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


def quantum(span,requirement):
    """Displayed precision of a cell, expressed in the requirement's unit (34124.1 USD_million -> 0.1)."""
    places=len(span.value.split('.')[1]) if '.' in span.value else 0
    return Decimal(1).scaleb(-places)*SCALES.get(span.unit,Decimal(1))/SCALES.get(requirement.unit,Decimal(1))


def compatible(spans,requirement,precision_aware):
    """precision_aware: False (exact), 'group'/True (gate v3: coarsest group precision) or 'pairwise' (gate v4: every pair within half its coarser step)."""
    values=[(converted(s,requirement),quantum(s,requirement)) for s in spans]
    if not precision_aware:return len({v for v,_ in values})<=1
    if precision_aware=='pairwise':return all(abs(a-b)<=max(qa,qb)/2 for i,(a,qa) in enumerate(values) for b,qb in values[i+1:])
    coarse=max((q for _,q in values),default=Decimal(1))
    return len({(v/coarse).quantize(Decimal(1)) for v,_ in values})<=1


def audit_coverage(spec,spans,documents,precision_aware=False):
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
        if not compatible(related,r,precision_aware):conflicts.append(r.id);missing.append(r.id)
        elif candidates:
            # With precision-aware agreement, only the most precise compatible cells carry the value.
            if precision_aware:finest=min(quantum(s,r) for s in candidates);candidates=[s for s in candidates if quantum(s,r)==finest]
            supported.append(r.id);audited.extend(s.id for s in candidates)
        else:missing.append(r.id)
    return CoverageResult(not missing and not conflicts,tuple(supported),tuple(missing),tuple(conflicts),tuple(sorted(set(audited))))
