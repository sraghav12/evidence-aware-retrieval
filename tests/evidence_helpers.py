import json
from pathlib import Path
from pipelines.evidence_aware.calendar import build_fiscal_calendar
from pipelines.evidence_aware.parser import parse_query
from pipelines.evidence_aware.units import build_units
from pipelines.evidence_aware.extraction import extract_candidates
ROOT=Path(__file__).parent/'fixtures/evidence_v2'


def documents():return {d['doc_id']:d for d in map(json.loads,(ROOT/'documents.jsonl').read_text().splitlines())}


def aliases(docs):return {d['entity_id'].split(':')[-1].casefold():d['entity_id'] for d in docs.values()}


def spec(question='What was Alpha FY2024 revenue?',docs=None):
    docs=documents() if docs is None else docs
    return parse_query(question,'2025-03-01',aliases(docs),build_fiscal_calendar(docs,'2025-03-01'))


def spans(docs=None):
    docs=documents() if docs is None else docs
    return extract_candidates(build_units(docs),docs)
