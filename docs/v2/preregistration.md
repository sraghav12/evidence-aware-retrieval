# Release C preregistration, version 2 (frozen before any pilot outcome)

Frozen October 18, 2026 in `data/release/v2/experiment_manifest.json`. Its SHA-256 is recorded in that file. `scripts/run_experiment_v2.py` refuses to run if any of the following differ from the freeze:
- the corpus, questions or config;
- the source code, scripts or dependency lock;
- the run order;
- any arm's engine configuration;
- the manifest hash itself.

No pilot question had been run when this was written. This is a **development-only, descriptive feasibility pilot** with AI-proposed, unreviewed references. It is not a held-out or confirmatory study.

## Why version 1 was superseded (before any run)

A fresh review found three problems:
1. **The locked test was invalid.** The split ignored the published v1 questions, which the spec makes development-only. Seven of its eight test groups involved v1 companies, and two test questions repeated v1 gold answers.
2. **Rounding was labeled as restatement.** Presentation-precision differences (34,124.1 vs 34,124) were labeled as restatements, contradicting the Release B reference for the same figure.
3. **The freeze was not bound to execution** and missed mutable inputs.

All three are fixed with regression tests. In the redrawn split (seed 11), components touching any v1 or Release B company are development. Only 2 informative groups remained outside development, against a preregistered minimum of 4 per side, so **no locked test exists on this corpus**. The split is not forced.

## Data

- **Pilot:** 111 questions in `data/release/v2/pilot_questions.jsonl` (id, question, as-of only), covering 25 non-financial companies in the frozen v1 corpus plus five companies absent from it.
- **References:** proposed by a separate raw inline-XBRL fact reader that compares values at their stated XBRL precision. Stored in `data/release/v2/references/pilot.jsonl`. Human reviewers: 0.
- **Mix:** 77 answerable and 34 unanswerable.

| Template | Count |
|---|---|
| Extraction | 41 |
| Growth | 20 |
| Two-company sums | 7 |
| Two-company rankings | 6 |
| Not yet in a 10-K in this corpus by the cutoff | 24 |
| Genuine reported/restated conflicts (GE, Johnson & Johnson) | 3 restatement probes, plus conflicting growth and ranking rows |
| Out-of-grammar paraphrases | 5 |
| Unknown companies | 5 |

- **Exclusions:** 18 templates, with reasons. 16 are definition conflicts (ConocoPhillips, Chevron, Pfizer, Walmart); 2 are FCX templates with duplicated fiscal focus. Banks and an asset manager (BAC, BLK, GS, JPM, WFC) fall outside the reviewed revenue definition.
- **Split:** 13 independent components, all development (`data/release/v2/pilot_split_manifest.json`).

## Which questions can separate arms (computed from parsing and extraction coverage only)

| Rows identical in every arm | Count |
|---|---|
| Parse failures: no fiscal calendar yet | 24 |
| Parse failures: out-of-grammar paraphrase | 5 |
| Parse failures: unknown company | 5 |
| Answerable, but a required company has no extracted cell (ConocoPhillips, Deere, Exxon Mobil, Pfizer, Chevron) | 8 |

Arm-sensitive: **69 questions (64 answerable, 5 unanswerable) in 6 independent groups**. Results are reported for all 111 questions and for this preregistered 69-question subset.

## Arms (matched per budget profile)

Every arm shares:
- source units;
- the coverage gate and answer audit;
- the Decimal executor (no model answerer);
- stage limits from the config: 8,192 per stage, 8,192 cheap stage, 24,576 cumulative retrieval and 24,576 verification, 30,000 ms deadline, 12 packed sections;
- 512 output tokens.

Two context budgets are frozen: 4,096 and 8,192.

| Track | Arms |
|---|---|
| Scheduling (BM25) | `always_cheap_v1`, `coverage_rule_v1` (treatment), `complexity_rule_v1` (≤2 operands cheap-only; author-selected and frozen), `always_maximum_v1` (all three bounded stages) |
| Strategy (evidence rule) | `bm25` (same run as `coverage_rule_v1`); `dense` (bge-small-en-v1.5@5c38ec7); `hybrid_rrf` (BM25 + dense, `k=60`); `hybrid_rrf_rerank` (+ ms-marco-MiniLM-L6-v2@233902d over the first 60 candidates) |

Paired run order: a seeded shuffle (seed 11) of 1,554 runs (111 questions × 7 distinct arms × 2 budgets, 1 repeat; the executor is deterministic). One dense index is built once and reused. Provider requests: 0.

## Primary comparison (chosen on Release B development only)

`coverage_rule_v1` versus `always_maximum_v1` at the 8,192 context budget, chosen before any pilot run. Release B results, reproduced on the regenerated corpus (extractor v2):

| Arm | Supported / 16 | Correct abstentions / 4 | Retrieval stages | Inspected retrieval tokens |
|---|---|---|---|---|
| always_cheap_v1 | 11 | 4 | 15 | 51,955 |
| coverage_rule_v1 | 12 | 4 | 18 | 64,788 |
| complexity_rule_v1 | 11 | 4 | 19 | 66,931 |
| always_maximum_v1 | 11 | 4 | 45 | 158,257 |

The 4,096 budget gave identical results.

## Endpoints and analysis

- **Primary endpoint:** supported numerical success on answerable questions (value and unit, reference requirements, source re-audit, citation audit).
- **Co-primary:** correct abstention on unanswerable questions.
- **Resource:** inspected retrieval and verification tokens. These are whitespace estimates, not billed tokens.
- **Secondary:** retrieval stages, p50/p95 local wall time, peak memory, dense indexing time, reranker pairs.
- **Paired difference:** treatment minus comparator, with a 95% component-cluster bootstrap (2,000 resamples, seed 11). Reported on all 111 questions and on the arm-sensitive 69.
- **Status of intervals:** with 13 (or 6) independent groups and no locked test, every interval is descriptive. No noninferiority, superiority or savings claim follows from this pilot. The 2-point margin and 15% inspected-token target are recorded for a future confirmatory design.
- **Failure policy:** errors and timeouts stay in denominators; no rerun because of an outcome. Bugs found after the run require a new protocol version and a fresh run.

## Gates still open

- **Independent test data.** A confirmatory study needs companies or filings outside the v1 and Release B ancestry. That means new SEC collection with a declared User-Agent and rate limits.
- **Human review** of `data/release/v2/annotation/pilot_packet.csv`.
- **Any model answerer:** it needs a pinned model revision, prompt hash and decoding, plus separately authorized spend. Live execution is disabled.
