# Release C preregistration (frozen before any pilot outcome)

Frozen October 18, 2026 in `data/release/v2/experiment_manifest.json`. The SHA-256 is recorded in that file and checked by `validate_experiment`. No pilot question has been run. This is a feasibility pilot with AI-proposed, unreviewed references, not a confirmatory study.

## Question

Does checking which numerical operands are still missing guide extra retrieval better than fixed or complexity-based schedules, at matched limits?

## Data

- **Pilot:** 114 questions in `data/release/v2/pilot_questions.jsonl` (id, question, as-of only). They come from 25 non-financial companies in the frozen v1 corpus plus five companies absent from it.
- **References:** AI-proposed from a separate raw inline-XBRL fact reader (`evaluation/evidence_aware/xbrl_reference.py`), stored in `data/release/v2/references/pilot.jsonl`. Human reviewers so far: 0.
- **Mix:** 76 answerable and 38 unanswerable.

| Template | Count |
|---|---|
| Single-company extraction | 41 |
| Growth | 20 |
| Two-company sums | 7 |
| Two-company rankings | 6 |
| Not-yet-disclosed fiscal years | 24 |
| Reported/restated conflicts | 6 |
| Out-of-grammar paraphrases | 5 |
| Unknown companies | 5 |

- **Exclusions:** 18 company-year templates were excluded with reasons. 16 are definition conflicts, where one filing tags two different dimensionless revenue figures (ConocoPhillips, Chevron, Pfizer, Walmart). 2 are FCX templates whose filings declare duplicate fiscal-year focus. Banks and an asset manager (BAC, BLK, GS, JPM, WFC) fall outside the reviewed revenue definition.
- **Split:** company components, with shared sources and derivation ancestry, in `data/release/v2/pilot_split_manifest.json`. Public grammar templates never connect questions.
  - Every component touching a Release B company is development.
  - 22 independent groups: 14 development (75 questions) and 8 locked test (39 questions, 25 answerable).
  - Fewer than 12 test groups, so **all test intervals are descriptive only**.

## Arms (matched per budget profile)

All arms share the following:
- source units (`units_hash`);
- the coverage gate (`audit_coverage_v2`);
- the answer audit;
- the Decimal executor (no model answerer);
- stage limits: 8,192 per stage, 24,576 cumulative retrieval, 24,576 cumulative verification, 30,000 ms deadline, 12 packed sections;
- 512 output tokens.

Two context budgets are frozen: 4,096 and 8,192.

| Track | Arms |
|---|---|
| Scheduling (BM25) | `always_cheap_v1`, `coverage_rule_v1` (treatment), `complexity_rule_v1` (≤2 operands cheap-only, otherwise all three stages; author-selected and frozen), `always_maximum_v1` (all three bounded stages) |
| Strategy | `bm25` (same run as `coverage_rule_v1`). `dense`, `hybrid_rrf` and `hybrid_rrf_rerank` are **unavailable** (see [resource probe](resource_probe.md)) |

Paired run order is a seeded shuffle (seed 11) of 912 runs (114 questions × 4 scheduling arms × 2 budgets, 1 repeat). The order hash is in the manifest. Provider requests: 0. Estimated cost: none (no provider).

## Primary comparison, chosen on development only

**Primary:** `coverage_rule_v1` versus `always_maximum_v1` at the 8,192 context budget.

It was chosen from the 20 Release B development questions, before any pilot run:

| Arm (8,192) | Supported / 16 answerable | Correct abstentions / 4 | Retrieval stages | Inspected retrieval tokens |
|---|---|---|---|---|
| always_cheap_v1 | 11 | 4 | 15 | 51,955 |
| coverage_rule_v1 | 12 | 4 | 18 | 64,788 |
| complexity_rule_v1 | 11 | 4 | 19 | 66,931 |
| always_maximum_v1 | 11 | 4 | 45 | 158,257 |

The 4,096 budget gave identical quality on development, so the plan's author default of 8,192 is the primary budget. 4,096 stays as a frozen exploratory profile.

On development, `always_maximum_v1` lost one answer (Eli Lilly). Its extra retrieval reached a filing that presents 34,124.1 as 34,124, and the exact-value conflict rule abstained. `complexity_rule_v1` lost the two-operand sum that needs section search. These are development observations, not hypotheses confirmed.

## Endpoints and analysis

- **Primary endpoint:** supported numerical success on answerable test questions. Success means correct value and unit, the reference requirements, source re-audit and citation audit.
- **Co-primary:** correct abstention on unanswerable test questions.
- **Resource:** inspected retrieval and verification tokens. These are whitespace estimates, not billed tokens.
- **Secondary:** retrieval stages, p50/p95 local wall time, peak memory.
- **Paired difference:** treatment minus comparator per question, with a 95% component-cluster bootstrap (2,000 resamples, seed 11). Answerable and unanswerable rows are analyzed separately.
- **Noninferiority margin (candidate):** 2 percentage points, with a 15% inspected-token reduction as the resource target. With 8 test groups and 25 answerable test questions, this pilot cannot establish noninferiority. A nonsignificant difference will be reported as inconclusive.
- **Multiplicity:** one primary comparison. Every other arm and budget is exploratory.
- **Failure policy:** errors and timeouts stay in denominators. Unavailable arms are reported, never substituted. No rerun because of an outcome. Bugs found after unlocking require a new protocol version and a fresh run.

## Gates still open

- Human review of the annotation packet (`data/release/v2/annotation/pilot_packet.csv`). 53 rows require a second reviewer, including every unanswerable and conflict row.
- Download approval for dense and reranker weights.
- Any model answerer: it needs a pinned model revision, prompt hash and decoding, plus separately authorized spend. Live execution is disabled.
