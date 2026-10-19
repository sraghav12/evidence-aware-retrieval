# Offline milestone results

Eight original synthetic source cases: three supported numerical answers and five correct abstentions, with zero recorded query errors. The ranking case recovers two missing Beta operands through section search and returns Alpha 20.00%, Beta 10.00%. The wrong-period, mention-only, mixed-currency, unavailable-disclosure and conflicting-value cases abstain.

These are hand-specified functional checks, not a population accuracy estimate. References are agent-authored. No model/provider inference, independent human evaluation or cost-reduction experiment has occurred. API spend is zero; local compute is unpriced. See saved traces and the offline HTML report for each requirement, source span and route.

Reproduce from repository root:

```bash
python3 -S scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --output results/evidence_v2/my_smoke
python3 -S scripts/report_evidence_v2.py --results results/evidence_v2/my_smoke
```

After the fresh whole-branch review fix pass, the same eight cases still give three supported answers and five correct abstentions.

## Release B: real-filings engineering pilot

20 development questions over 10 companies from raw SEC inline-XBRL HTML: 12/16 answerable questions supported and reference-verified, 4/4 unanswerable correctly abstained, 0 errors, 0 provider calls. Misses are a three-company ranking lost to BM25 slot competition, Walmart's two revenue concepts, one out-of-grammar wording and one comparative-only fiscal year. References are AI-authored and unreviewed; this is development data, not a test. Details, failure table and limitations: [extraction audit](extraction_audit.md).

## Release C: frozen pilot experiment (development-only, descriptive)

The run was `results/evidence_v2/pilot_001` (portable summary: `examples/evidence_v2/pilot_001_report.json`):
- 1,554 paired runs of the version 2 preregistration (manifest `098db2c…`) in its seeded order;
- executor only, 0 provider calls, 0 errors, 18.7 minutes on CPU.

There is no locked test: v1 ancestry leaves too few independent groups. The references are AI-proposed and unreviewed. Every interval below is descriptive, with 6 independent answerable groups.

All 111 questions (77 answerable, 34 unanswerable), 8,192 context; the 4,096 budget gave identical outcomes for every arm:

| Arm | Supported / 77 | Correct abstentions / 34 | Unsupported answers | Retrieval stages | Inspected retrieval tokens | p50 / p95 ms |
|---|---|---|---|---|---|---|
| always_cheap_v1 | 45 | 34 | 0 | 77 | 270,343 | 193 / 261 |
| complexity_rule_v1 | 48 | 34 | 0 | 89 | 313,867 | 194 / 376 |
| **coverage_rule_v1** (evidence rule) | **58** | 33 | 1 | 130 | 498,333 | 194 / 587 |
| always_maximum_v1 | 58 | 33 | 1 | 231 | 815,991 | 514 / 597 |
| dense + evidence rule | 55 | 34 | 0 | 142 | 605,807 | 199 / 600 |
| hybrid RRF + evidence rule | 57 | 34 | 0 | 135 | 539,845 | 199 / 593 |
| hybrid RRF + rerank + evidence rule | 56 | 34 | 0 | 135 | 591,839 | 1,404 / 4,267 |

What the data show:

- **Primary comparison (evidence rule vs always-maximum).** Paired difference 0.0 (95% cluster interval [0.0, 0.0], 6 groups) on answerable questions, and 0.0 on unanswerable ones. Every question had the same scored outcome under both arms, and the evidence rule used 44% fewer retrieval stages and 39% fewer inspected retrieval tokens. On the 69-question arm-sensitive subset both arms support 58/64.
- **Cheaper schedules lose answers.** Always-cheap supports 45 and the operand-count rule 48, versus 58.
- **Dense retrieval did not beat BM25 on these table units.** Dense alone supported 55 and hybrid RRF 57; adding the reranker gave 56 at about 7× the median latency. The model arms add one-time indexing: 7,180 units, 3.68M tokens, 314.5 s, 2.83 GB process peak. The reranker scored 15,746 pairs.
- **One unsupported answer, GE Aerospace FY2023 (as of 2026-03-15).** The evidence rule and always-maximum answered 67,954, the originally reported figure. The FY2024 10-K restates it as 35,348 after the GE Vernova spin-off. BM25 never packed the restated cell, so the gate saw no conflict. The dense, hybrid and rerank arms retrieved it and abstained. Conflict detection is bounded by what retrieval finds; this is the most important open failure.
- **Arm-invariant rows.** 34 parse failures plus 8 questions about companies with no extracted cells behave identically in every arm. They are kept in the 111-question denominators.

## Protocol v3: held-out companies (locked test) and gate v3

**Gate v3 on development.** The bounded post-gate conflict probe, plus displayed-precision compatibility, was designed and frozen on the 111 development questions. Under both the evidence rule and always-maximum it removed the single unsupported answer: GE FY2023 now abstains. It kept 58/77 supported, raised correct abstentions to 34/34, and cost 1,422 probe tokens in total.

**Held-out test.** 16 companies outside all development ancestry and 48 newly collected 10-Ks give 76 questions in 13 independent groups ([preregistration](preregistration_heldout.md), frozen and pushed before the run). Run `heldout_001` at clean commit `3bd1da2` made 456 runs with 0 errors and 0 provider calls in 2.6 minutes (portable summary: `examples/evidence_v2/heldout_001_report.json`).

| Arm (8,192, gate v3 unless noted) | Supported / 60 | Correct abstentions / 16 | Unsupported answers | Retrieval stages | Inspected retrieval tokens | p50 ms |
|---|---|---|---|---|---|---|
| always_cheap_v1 | 44 | 16 | 0 | 59 | 186,829 | 62 |
| complexity_rule_v1 | 45 | 16 | 0 | 63 | 203,703 | 62 |
| **coverage_rule_v1** (evidence rule) | **51** | 16 | 0 | 82 | 255,086 | 62 |
| always_maximum_v1 | 51 | 16 | 0 | 177 | 537,506 | 165 |
| hybrid RRF + evidence rule | 51 | 16 | 0 | 84 | 273,001 | 66 |
| evidence rule with gate v2 (ablation) | 51 | 16 | 0 | 82 | 255,086 | 62 |

- **Primary comparison replicated.** The evidence rule and always-maximum disagreed on 0 of 60 answerable and 0 of 16 unanswerable questions (12 and 13 groups), while the evidence rule inspected 52.5% fewer retrieval tokens and ran 54% fewer stages. On the 51 arm-sensitive questions both arms support 51/51.
- **The interval is degenerate.** With no discordant question the bootstrap gives [0, 0]. The exact one-sided 95% upper bound on the discordance rate is 4.9% for 60 questions, which is wider than the 2-point noninferiority margin, so **noninferiority is not established**. The claim checker rejects it.
- **Gate v3 cost nothing on held-out data.** It gave the same 51/60 and 16/16 as gate v2 with 1,024 probe tokens, and no false conflicts.
- **Gate v3's benefit was not tested on held-out data.** No arm-sensitive unanswerable question exists there, so the held-out test cannot show the probe catching a restatement. That benefit rests on the development GE case alone.
- **Hybrid RRF matched BM25 again** (51/60), with slightly more tokens.

None of this supports a noninferiority, savings or broad generalization claim. Local compute is unpriced and the token counts are whitespace estimates. The claims cited here are checked by `tests/test_evidence_claims.py` against the exported report.

Use a new output directory per run. Reporting reads saved files and does not call a model. The core works with the Python standard library; pytest is needed for its tests, and the separate compatibility lock supports the historical v1 test suite.
