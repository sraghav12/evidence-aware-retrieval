# Five-minute walkthrough

Everything here is offline and uses saved files. The four real-filing traces are in [examples/evidence_v2/walkthrough.md](../../examples/evidence_v2/walkthrough.md).

## 0. Run it (30 s)

```bash
python3 -S scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --output results/evidence_v2/demo
python3 -S scripts/report_evidence_v2.py --results results/evidence_v2/demo
```

Open `results/evidence_v2/demo/report.html`. The run needs only the standard library and makes no API calls.

## 1. The parser (45 s)

"What was Apple FY2024 revenue growth over FY2023?" becomes two requirements, `cik:320193:revenue:2023` and `cik:320193:revenue:2024`. Their exact period dates come from the fiscal calendar of filings disclosed by the as-of date (`pipelines/evidence_aware/{parser,calendar}.py`). Ask "What was Apple FY2025 revenue?" as of mid-2025 and it abstains with `unknown_fiscal_calendar`, because the FY2025 10-K did not yet exist.

## 2. One source cell (60 s)

Apple FY2024 total net sales, 391,035, comes from `AAPL_10K_2024`, table 22, row 6, inline-XBRL fact `f-66`. The extractor accepted it only because all of these agreed:
- the context period (2023-10-01 to 2024-09-28) matched the column header "September 28, 2024";
- the scale (6) matched the caption "In millions";
- the row was labeled "Total net sales";
- the context has no segment dimension.

Swap two column headers and the cell is rejected (`tests/test_evidence_html.py`).

## 3. One route (60 s)

The Apple + Coca-Cola FY2023 sum:
1. **Cheap search:** finds Coca-Cola only, 1 of 2 operands.
2. **Section search:** targets the missing Apple operand and finds it in the consolidated statement.
3. **Answer:** 429,039 USD million, each operand cited.

The route is `cheap_search → section_search → answer`. Stage history is explicit, each later stage skips units already inspected, and the token and deadline budgets are checked before each stage.

Abstention example: Johnson & Johnson FY2022 as of mid-2024 sees 94,943 (original) and 79,990 (restated after Kenvue) and abstains with `conflicting_evidence`. As of mid-2023 only the original exists and it answers 94,943.

## 4. The strongest baseline (45 s)

Always-maximum runs all three bounded stages for every question. On the 111-question pilot it matched the evidence rule exactly (58/77 supported) while inspecting 64% more tokens. Pinned dense retrieval (bge-small) and hybrid RRF with a cross-encoder reranker did not beat BM25 on these table units. The comparison is honest because every arm shares one frozen manifest: same units, gate, audit, limits, and paired seeded order.

## 5. The failed hypothesis (60 s)

I expected "the gate will catch restatements." It catches only the ones retrieval finds. For GE Aerospace FY2023 the evidence rule answered the superseded 67,954 because BM25 never retrieved the restated 35,348; the dense arms did and abstained. Second, the planned locked test collapsed once v1 lineage was applied, so the study was re-registered as development-only before running, rather than forcing a split. What came next:
- **Conflict probe:** I added a bounded post-gate conflict probe (gate v3), tuned only on development data, which fixed GE without losing answers.
- **Held-out test:** I collected 16 new companies from SEC EDGAR, froze protocol v3 publicly, and ran it once. The evidence rule matched always-maximum on all 76 held-out questions with 52.5% fewer inspected tokens.
- **What I won't claim:** noninferiority. Zero discordant questions make the bootstrap interval degenerate, and counted by the 12 independent clusters the 95% bound on the discordance rate is 22%, far wider than the margin.

## Factual resume lines (drafts; the author decides whether and how to use them)

- Built an evidence-aware retrieval pipeline over raw SEC inline-XBRL filings. It extracts source-linked revenue cells (594 accepted, every rejection recorded with a reason), audits operand coverage and abstains on conflicts, with 180+ tests and mutation-checked safety guards.
- Ran a preregistered, hash-frozen 1,554-run comparison of seven retrieval and scheduling arms with paired cluster bootstrap analysis. The coverage-based rule matched the maximum-retrieval baseline on all 111 development questions with 39% fewer inspected tokens; development-only results with AI-proposed references.
- Diagnosed a retrieval-bounded failure mode (an unretrieved restatement led to a superseded answer) and added a bounded conflict probe designed on development data. A preregistered locked test on 16 newly collected companies (76 questions) matched always-maximum on every question with 52.5% fewer inspected tokens (39% on development); noninferiority is not claimed.
