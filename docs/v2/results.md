# Offline milestone results

Eight original synthetic source cases: three supported numerical answers and five correct abstentions, with zero recorded query errors. The ranking case recovers two missing Beta operands through section search and returns Alpha 20.00%, Beta 10.00%. The wrong-period, mention-only, mixed-currency, unavailable-disclosure and conflicting-value cases abstain.

These are hand-specified functional checks, not a population accuracy estimate. References are agent-authored. No model/provider inference, independent human evaluation or cost-reduction experiment has occurred. API spend is zero; local compute is unpriced. See saved traces and the offline HTML report for each requirement, source span and route.

Reproduce from repository root:

```bash
python3 -S scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --output results/evidence_v2/my_smoke
python3 -S scripts/report_evidence_v2.py --results results/evidence_v2/my_smoke
```

Use a new output directory per run. Reporting reads saved files and does not call a model. The core works with the Python standard library; pytest is needed for its tests, and the separate compatibility lock supports the historical v1 test suite.
