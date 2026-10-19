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

Use a new output directory per run. Reporting reads saved files and does not call a model. The core works with the Python standard library; pytest is needed for its tests, and the separate compatibility lock supports the historical v1 test suite.
