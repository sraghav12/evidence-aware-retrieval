# Release B: raw SEC HTML extraction audit (engineering pilot)

Status, October 18, 2026: development pilot only. References are AI-authored and unreviewed; human review count is zero. No provider calls, model downloads or spending. These numbers are not an accuracy estimate and the 20 questions are not a locked test.

## Source lineage

The frozen v1 corpus stores normalized text only. Raw HTML exists solely as 150 untracked files in the original checkout's `data/raw/`; the clone never contained them. Before copying anything, each file was matched to `data/release/v1/corpus_150.jsonl.gz` metadata and the source `filing_manifest.json`: 150/150 match on file name, byte size, accession number and CIK, all decode as UTF-8, none are missing. `.env`, caches, old results and the source checkout's modified/untracked files were not read or copied.

`scripts/prepare_evidence_v2.py` hashes raw bytes, copies only the selected filings into ignored `data/raw/evidence_v2/` (157 MB, re-hashed after copy), and writes:

| Artifact | Tracked | Content |
|---|---|---|
| `data/release/v2/source_manifest.json` | yes | Per filing: accession, CIK, filing date, SEC URL, raw SHA-256 and bytes, v1 text SHA-256, normalized SHA-256, extractor version, accepted and rejected counts |
| `data/release/v2/extraction_audit_v1_corpus.json` | yes | Extraction counts for all 150 v1 filings |
| `data/processed/evidence_v2/real_dev_documents.jsonl` | no | Normalized documents consumed by inference (SHA-256 `4769f9fb917f…` in the manifest) |
| `data/processed/evidence_v2/real_dev_segments.jsonl` | no | Normalized offsets to table/row/cell locator, XBRL fact/context ID, raw character and byte ranges |
| `data/processed/evidence_v2/real_dev_extraction_failures.jsonl` | no | Every rejected candidate with its reason |

Untracked artifacts are regenerated deterministically from the raw bytes; tests assert identical output and normalized hashes on repeated runs.

## Extractor (`html_ixbrl_tables_v2`)

Python standard-library `html.parser` (pinned by the 3.12.9 interpreter), so the offline core still runs under `python -S`. A candidate is a `ix:nonFraction` fact with a revenue concept (`us-gaap:Revenues`, `RevenueFromContractWithCustomerExcluding/IncludingAssessedTax`, `SalesRevenueNet`) inside a table cell. Facts whose context has a segment or scenario dimension are skipped as non-consolidated. Every remaining candidate must pass all checks or is rejected with a reason:

1. Context exists, CIK matches the filing, unit is USD, number format is `num-dot-decimal`, scale maps to a supported unit.
2. Duration of 350–380 days. Fiscal year comes from `dei:DocumentFiscalYearFocus` and its context, offset by whole years (±20 days tolerance for 52/53-week years). Version 2 adds a plausibility check: fiscal years ending June–December must carry their end year, and January–May year ends may use the end year or the year before. FCX_10K_2024 declares FY2023 for a period ending December 2024, so it is now rejected as `implausible_fiscal_year_focus`. Its cells were already rejected through year headers; with date headers they would have been mislabeled.
3. Row label contains "revenue" or "sales" and not cost/expense/per-share/percent.
4. Exactly one period header covers the cell's grid column (colspan-aware), and that header covers only one context period. A full date must equal the context end date; a bare year must equal the derived fiscal year. Swapping column headers therefore rejects the cell.
5. A unit caption (`in thousands|millions|billions`) in the table header rows, or else in the 200 characters before the table, must agree with the XBRL scale.
6. Tables with any `rowspan` are unsupported.

Accepted cells become pipe rows (`revenue | unit | start | end | fiscal_year | reported | value | row_label | column_header | locator`) inside one `SECTION table N` unit per numeric table, followed by display rows for retrieval. The fiscal calendar holds only each filing's own focus year.

## Results on all 150 v1 filings

594 accepted revenue cells in 99 filings from 20 of 30 companies. With extractor v2, 891 rejection records:

| Reason | Count |
|---|---|
| missing_unit_header | 260 |
| row_label_not_revenue | 236 |
| missing_period_header | 115 |
| unsupported_unit (non-`usd` unitRef) | 114 |
| non_annual_period | 77 |
| ambiguous_period_header | 34 |
| unsupported_rowspan | 33 |
| missing_fiscal_year_focus | 16 |
| unit_header_mismatch | 3 |
| period_header_mismatch | 2 |
| implausible_fiscal_year_focus | 1 (document-level) |

No cells were accepted for BAC, BLK, COP, CVX, DE, GS, JPM, PFE, WFC or XOM. Banks label revenue "net of interest expense" (rejected by the label rule); others lack an in-range unit caption, use rowspan or a non-`usd` unit ID. One WFC filing has no fiscal-year focus fact. FCX_10K_2023 and FCX_10K_2024 both declare fiscal-year focus 2023; v2 rejects the second as implausible. These are visible limitations, not repaired with references.

## Real-development pilot

10 companies (AAPL, AMD, CAT, GOOGL, JNJ, KO, LLY, META, NVDA, WMT), all 5 filings each: 50/50 prepared, 366 accepted cells, 191 rejected. 20 public questions in `data/release/v2/real_dev_questions.jsonl` (id, question, as-of only), written from the public grammar after inspecting extracted values across filings (to pick real late, conflicting, unknown and unsupported cases) but before any inference run. References are a separate file built from a direct inline-XBRL fact reader that does not use the table, header or caption logic.

Run `results/evidence_v2/real_dev_001` at clean commit `4448255`, reproduced with identical outcomes as `real_dev_002` on the extractor v2 corpus,, executor only, 0 provider calls, about 2 s of CPU for 20 questions:

| Outcome | Count |
|---|---|
| Supported answers, reference-verified (value, unit, requirements, source and citation audit) | 12 / 16 answerable |
| Correct abstentions | 4 / 4 unanswerable |
| Errors | 0 |
| Parse failures (all abstentions) | 5: `unknown_fiscal_calendar` ×3, `unknown_entity`, `unsupported_query` |

Behaviors observed on real filings:

- **Restatement:** Johnson & Johnson FY2022 revenue was reported as 94,943 and restated as 79,990 after the Kenvue separation. With an as-of of 2023-06-30 only the original filing is eligible and the system answers 94,943. With an as-of of 2024-06-30 both are eligible and it abstains with `conflicting_evidence`.
- **Escalation:** the Apple + Coca-Cola sum recovers through section search.
- **Cutoff:** Apple FY2025 (as-of before its 10-K) and the Apple/Coca-Cola FY2025 ranking (Coca-Cola's 10-K not yet filed) abstain.

Misses among answerable questions, all kept in the denominator:

| Question | Outcome | Cause |
|---|---|---|
| rd06 rank Apple, AMD, Coca-Cola by FY2024 growth | `incomplete_evidence` after all three stages | BM25 fills each stage's 12 units with Coca-Cola tables; AMD units selected by later stages are not its revenue tables. Lexical ranking limit for multi-company questions |
| rd15 Walmart FY2025 | `conflicting_evidence` | Walmart tags both Net sales (674,538) and Total revenues (680,985) as dimensionless revenue concepts; no concept-precedence policy exists |
| rd18 "How much revenue did Apple report in fiscal 2024?" | `unsupported_query` | Outside the controlled grammar |
| rd19 Coca-Cola FY2020 | `unknown_fiscal_calendar` | FY2020 appears only as a comparative; the calendar uses focus years only |

Known limitations a reader should weigh:

- **Conflict checks only see retrieved evidence.** rd16 (Eli Lilly FY2023) answered 34,124.1 from the cheap stage after inspecting the 2021–2023 filings. The eligible FY2025 10-K presents the same figure as 34,124 and was never retrieved. That answer matches the reference, but "no conflict" means none was found in the evidence retrieved.
- **Exact-value conflicts ignore presentation precision.** A 34,124.1 vs 34,124 pair would abstain.
- **Questions were authored with the system's grammar and failure modes in mind.** This is development data. The cutoff-filtered, non-repeating escalation fixes were motivated partly by a trial run on these questions; that history is recorded in `implementation-progress.md`.

## Reproduce

```bash
.venv/bin/python -S scripts/prepare_evidence_v2.py --config configs/evidence_v2_real_dev.json --source-raw-dir <source checkout>/data/raw
.venv/bin/python -S scripts/prepare_evidence_v2.py --config configs/evidence_v2_real_dev.json --source-raw-dir <source checkout>/data/raw --audit-all
.venv/bin/python -S scripts/run_evidence_v2.py --config configs/evidence_v2_real_dev.json --output results/evidence_v2/<new_run>
.venv/bin/python -S scripts/report_evidence_v2.py --results results/evidence_v2/<new_run> --references data/release/v2/references/real_dev.jsonl
```
