# Evidence-aware retrieval: offline methods

Inference loads only question/as-of records and source documents. Fiscal dates come from cutoff-eligible public source metadata. A controlled grammar creates requirements, BM25 selects source sections, and a deterministic extractor proposes explicit table cells. Coverage rechecks source hashes, offsets, entity, metric, units, fiscal dates and accounting basis. Missing evidence can trigger section search and one expanded search. Conflicts abstain immediately. Numerical execution uses Decimal, cites every operand and preserves unrounded ranking order.

The synthetic representation is intentionally explicit, not an SEC HTML parser. The eight original cases exercise mechanics only. The 64-whitespace-token cheap-stage fixture cap deliberately withholds one company's table in the ranking case; the ordinary per-stage ceiling is 8192. No accuracy, transfer, novelty or dollar-savings conclusion follows from these cases. CPU wall time and process-high-water RSS are measured locally; whitespace tokens are estimates, and compute has no assigned dollar price.

The CLI currently supports only offline executor runs. Live mode exits with an unavailable-arm message without contacting a provider. Injected answerers are tested through a reservation boundary; no provider client has been implemented or used. When an answerer becomes unavailable, another can be selected under the user's authorization, but all compared arms must be rerun on the same pinned replacement. Switching models does not authorize spending.

Real filings (Release B) go through `pipelines/evidence_aware/html_source.py`, which cross-checks each consolidated inline-XBRL revenue fact against its visible column header, unit caption and row label before emitting a normalized row with a raw-HTML locator; see the [extraction audit](extraction_audit.md). Retrieval only considers units from filings disclosed by the cutoff, later stages skip units already inspected, and packing places units holding candidate cells first.

Evaluation loads references separately and verifies the run's status, config hash, corpus hash, trace checksum and question set before scoring. Supported numerical success requires the reference value/unit, the reference's requirements and/or evidence offsets, complete coverage reaudited against source documents and valid operand citations. Correct abstention is reported separately. AI-authored references are labeled as such. Runs retain source/config hashes, failures and numerical traces. Clustered comparisons reject unmatched rows and keep repeated questions together; fewer than 12 independent groups yields descriptive intervals only.

## Arms

Every arm in a comparison shares:
- the same source units and eligibility (cutoff, entity, section filter);
- the same selection rule, coverage gate, answer audit and Decimal executor;
- the same context, output and stage limits.

**Scheduling arms** (`pipelines/evidence_aware/policy.py`) all use BM25:

| Arm | Behavior |
|---|---|
| `always_cheap_v1` | One cheap stage, then the gate decides |
| `coverage_rule_v1` | The evidence rule: escalate only while operands are missing |
| `complexity_rule_v1` | Author-frozen: at most 2 operands means cheap only; otherwise all three stages |
| `always_maximum_v1` | All three bounded stages regardless of early completeness |

**Strategy arms** (`pipelines/evidence_aware/retrieval.py`, `onnx_rankers.py`) use the evidence rule with different rankers:
- BM25;
- dense (pinned bge-small-en-v1.5);
- hybrid RRF (`k=60`);
- hybrid plus a pinned cross-encoder reranker over the first 60 candidates.

Model weights are verified by SHA-256 before loading. A missing model makes its arm unavailable rather than falling back to BM25.

## Gate v3

The bounded conflict probe (`engine.py` `conflict_probe`) runs only when coverage is complete.
- **What it reads:** later eligible filings of each cited entity, meaning disclosed after the earliest cited filing for that entity and on or before `as_of`, excluding filings already packed.
- **What it checks:** up to 3 units per filing that contain a same-quantity cell, within 2,048 inspected tokens. The cost is charged to the retrieval and verification allowances and logged as a `conflict_probe` usage stage.
- **Outcome:** packed plus probed evidence is re-audited. An incompatible value abstains with `conflicting_evidence`. A probe without budget is recorded as `skipped_budget` and the answer proceeds.

Gate v3 also compares cells at the coarser *displayed* precision. For example, 34,124.1 and 34,124 USD million agree at a precision of 1 million. Only the most precise compatible cells are cited. Probe settings were chosen on development data before the held-out run.

## Frozen experiments

An experiment manifest (`evaluation/evidence_aware/experiment.py`) freezes and hashes:
- the arms, each with its exact engine configuration and that configuration's hash;
- the budget profiles and the seeded paired run order;
- the corpus, question and units hashes;
- source, script and dependency-lock hashes;
- the config;
- the primary and secondary comparisons;
- the arm-sensitivity analysis, computed from parsing and extraction coverage only, never from retrieval or answers.

`scripts/run_experiment_v2.py` refuses to run (`FreezeMismatch`) if any of these differ on disk. The pilot manifest was frozen as preregistration v2 and the held-out manifest as protocol v3; each was pushed before its run.

## Held-out collection

`evaluation/evidence_aware/sec_collect.py` collects the latest original 10-Ks from SEC EDGAR.
- **User-Agent:** declared and read from the environment, never written to disk.
- **Pacing:** at most 4 requests per second, retrying on 429 and 5xx responses.
- **Records:** accession, SEC URL, raw bytes and raw SHA-256. Preparation re-verifies those hashes.

The held-out split (`build_heldout_manifest`) makes every row locked test and rejects any entity shared with v1, Release B or pilot rows.

## Paired intervals and degenerate cases

Paired differences are treatment minus comparator, reported separately for answerable supported success and for unanswerable correct abstention. The 95% interval is a component-cluster bootstrap (2,000 resamples).

When no question differs between the arms, the bootstrap collapses to [0, 0]. The report therefore also gives the number of discordant questions and one-sided 95% upper bounds on the discordance rate, `1 - 0.05^(1/n)`. The primary bound uses n = independent clusters; a per-question bound (n = questions) is also reported but assumes independent questions. `evaluation/evidence_aware/claims.py` rejects noninferiority claims on degenerate or descriptive-only intervals, savings claims with unknown cost, replay latency presented as measured latency, and claims whose input mode differs from the run's.
