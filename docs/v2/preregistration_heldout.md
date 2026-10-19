# Protocol v3 preregistration: held-out companies and gate v3 (frozen before any held-out run)

Frozen October 18, 2026 in `data/release/v2/heldout_experiment_manifest.json`; the SHA-256 is in that file. `scripts/run_experiment_v2.py` refuses to run if any of the following differ from the freeze:
- the corpus, questions or config;
- the code, scripts or lock;
- the run order;
- any arm's engine configuration;
- the manifest hash.

No held-out question had been run by any system arm when this was frozen.

## What was fixed beforehand, on development data only

- **Gate v3** (Task 11) adds displayed-precision compatibility and one bounded conflict probe over later eligible filings of each cited entity. On the 111 pilot development questions it removed the only unsupported answer: GE FY2023 abstains instead of returning the superseded 67,954. It cost no supported answers (58/77 for both the evidence rule and always-maximum) and 1,422 probe tokens in total.
- **Probe settings:** 3 units per filing and 2,048 tokens, the smallest cap that did not truncate the GE probe. The full grid is recorded in `docs/v2/implementation-progress.md`.
- **New template:** a `late_cutoff` extraction (prior fiscal year, asked 45 days after each company's latest filing) was added for all companies, so the probe is exercised without selecting on known conflicts. This replaces the conflict-only restatement template used in development.

## Held-out data

- **Companies:** 16 non-financial companies outside the 30 v1 tickers and outside every company named in development questions: ABT, ADBE, CRM, CSCO, HON, IBM, LMT, LOW, MRK, PEP, QCOM, SBUX, TGT, TMO, TXN and UPS.
- **Filings:** each company's three latest original 10-Ks, collected from SEC EDGAR with a declared User-Agent (not stored), at most 4 requests per second, in 65 requests. That gives 48 filings, 143 MB, raw SHA-256 values in `data/release/v2/heldout_filings.json`, and 211 accepted cells (`heldout_source_manifest.json`).
- **Questions:** 76 (60 answerable, 16 unanswerable) from the frozen templates in `data/release/v2/heldout_questions.jsonl`.

| Template | Count |
|---|---|
| Extraction | 28 |
| Growth | 13 |
| Late cutoff | 13 |
| Not yet in a 10-K in this corpus | 15 |
| Out-of-grammar paraphrases | 2 |
| Two-company sums | 3 |
| Two-company rankings | 2 |

- **Exclusions:** 12 templates, with reasons. Cisco has no FY2023 calendar among its filings, Salesforce declares FY2025 on two filings, and IBM has no standard revenue concept.
- **References:** AI-proposed by the separate inline-XBRL fact reader in `references/heldout.jsonl`. Human reviewers: 0.
- **Split:** every row is locked test. The builder rejects any entity overlap with v1, Release B or pilot rows. 13 independent groups (≥ 12), so `pilot_interval_not_confirmatory`.

## Which rows can separate arms (from parsing and extraction coverage only)

| Rows identical in every arm | Count |
|---|---|
| Parse failures: no fiscal calendar yet | 15 |
| Parse failures: out-of-grammar paraphrase | 2 |
| Answerable, company with no extracted cells (Honeywell, IBM, Target) | 7 |
| Unanswerable, company with no extracted cells | 1 |

Arm-sensitive: **51 answerable questions in 10 groups, and 0 unanswerable**. Consequence, stated before running: the held-out test can show whether gate v3 *costs* answers through false conflicts, but it cannot show gate v3 *catching* a restatement. No arm-sensitive unanswerable row exists. Any claim that the probe prevents superseded answers rests on development evidence only.

## Arms (8,192 context, 512 output, shared units, stage limits and audit)

| Arm | Gate | Policy / backend |
|---|---|---|
| `always_cheap_v1` | v3 | BM25 |
| `coverage_rule_v1` (treatment) | v3 | BM25 |
| `complexity_rule_v1` | v3 | BM25 |
| `always_maximum_v1` (comparator) | v3 | BM25 |
| `hybrid_rrf` | v3 | Evidence rule, BM25 + bge-small RRF |
| `coverage_rule_v1_gate_v2` (gate ablation) | v2 | Evidence rule, BM25 |

That is 456 runs in seeded order (seed 11), with 0 provider requests.

## Comparisons

- **Primary:** `coverage_rule_v1` vs `always_maximum_v1` (both gate v3), measured by answerable supported success and inspected retrieval tokens. The question is whether the development finding replicates on new companies: equal supported success with fewer inspected tokens.
- **Secondary:** gate v3 vs gate v2 under the evidence rule, measured by supported success and unsupported answers. Hypothesis: no loss of supported answers on held-out data.
- **Exploratory:** every other arm.
- **Analysis:** paired 95% component-cluster bootstrap (2,000 resamples, seed 11), on all 76 questions and on the 51 arm-sensitive ones. With 13 groups, intervals are pilot intervals, not confirmatory, and the references are AI-proposed. A 2-point noninferiority margin is the recorded candidate; it is not claimed unless the interval clears it.
- **Failure policy:** errors and timeouts stay in denominators; no rerun because of an outcome. Bugs found after the run require a new protocol version.
