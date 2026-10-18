# Project 2: Evidence-Aware Budgeted Retrieval Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for native sequential implementation, task by task. Use `superpowers:subagent-driven-development` only if the user explicitly selects delegation. Steps use checkboxes. This is a proposed execution plan, not a record of completed implementation.

**Goal:** Extend Beyond Vector Search with auditable evidence completeness, bounded retrieval escalation, and defensible quality/resource evaluation for applied AI/ML hiring evidence.

**Architecture:** Parse requested operands, retrieve document units, extract source-linked cells, audit coverage, escalate missing evidence within explicit stage/resource limits, then calculate and audit citations. Save complete traces and score them in a separate evaluation process. Preserve v1 unchanged.

**Tech Stack:** Python >=3.11 (3.12.9 environment), dataclasses, Decimal, JSONL, pytest, small local BM25 implementation; pinned HTML parser for real filings; optional dense/reranking dependencies after fit checks.

**Spec:** [Project 2 design](../specs/2026-10-18-evidence-aware-retrieval-design.md). Also read the [original handoff](../../../Evidence%20aware%20retrieval%20confined%20cost.md); it defines the full field contracts. All product paths below are relative to the future `beyond-vector-search` checkout.

## Global Constraints

- Project 2 only. Do not edit Project 1, its data, environment or models.
- Preserve published `data/release/v1/` and `results/release_v1/` byte-for-byte; put new artifacts under v2 paths.
- Preserve unrelated source-checkout changes. New target: `/Users/sragh/Downloads/Projects/beyond-vector-search`, branch `feat/evidence-aware-v2`.
- Default `provider_enabled=false`, `max_usd=0`; no API calls, model downloads or training for Release A.
- Reference answers, gold evidence, oracle choices and test outcomes never enter inference features, prompts, retrieval units or runtime parsing.
- Existing 43 published questions and derivatives are development-only; fixture results do not establish real-data performance.
- Strict inference schemas reject unknown fields; decimal values serialize as strings; document offsets are zero-based half-open character ranges.
- Pilot defaults: 8,192 final context tokens, 512 final output tokens, cheap pool 20, hybrid pool 60, at most 12 packed sections, at most three retrieval stages and one final generation call.
- Every model-based comparison uses one fixed answerer/revision/prompt/decoding and matched final context/output limits. Executor-only results are separate.
- Independent human review is required for independently validated correctness; AI review must retain its actual label.
- Person-hours, annotation effort, compute time and calendar time are distinct. Re-estimate after the offline milestone.

## Review Focus

1. Gold fields embedded in v1 query records or preselected spans can create a fake working system: Task 1 strict loader and Task 6 inference/evaluation isolation tests reject this.
2. Raw HTML is local and untracked; flattened text loses table headers: Task 8 requires raw-source extraction and keeps source/layout failures in the report.
3. Empty retrieval, packing omissions and zero provider-call counts can break routing: Tasks 3/5 test post-packing coverage and explicit stage history.
4. Cache reuse, failed calls and missing prices can fabricate savings: Tasks 6/7 retain failures, nulls and original-versus-replay timing.
5. Cross-company bridges, duplicated templates and insufficient independent groups can leak test data or inflate certainty: Tasks 2/9 reject overlap and limit claims.

## File responsibilities and interfaces

| Path | Responsibility |
|---|---|
| `pipelines/evidence_aware/contracts.py` | Strict frozen inference, evidence, budget and trace schemas |
| `pipelines/evidence_aware/{parser,calendar,units,extraction}.py` | Supported grammar, source-derived units, table-cell extraction |
| `pipelines/evidence_aware/{retrieval,coverage,numeric,policy}.py` | Ranking, evidence audit, Decimal execution, bounded routing |
| `pipelines/evidence_aware/{engine,pipeline}.py` | Provider-free orchestration; explicit v1 adapter |
| `evaluation/evidence_aware/{dataset,ledger,runner,report}.py` | Split manifests, usage ledger, inference runner, reference-only scoring |
| `evaluation/__init__.py` | Preserve old public exports lazily, avoid provider imports for v2 offline modules |
| `scripts/{run_evidence_v2,report_evidence_v2,prepare_evidence_v2}.py` | Validated entrypoints, no top-level provider clients |
| `configs/evidence_v2_{offline,real_dev,experiment}.json` | Explicit fixture, real-development and later experiment settings |
| `tests/test_evidence_*.py`, `tests/fixtures/evidence_v2/` | Regression checks and synthetic source documents |
| `data/release/v2/` | Versioned source, public question and split manifests; evaluation references in a separate directory |
| `results/evidence_v2/<run_id>/` | Immutable config, traces, events, run status and reports |
| `docs/v2/` | Baseline inventory, decisions, annotation protocol, methods, results and interview walkthrough |

Interfaces below are design decisions. Add private helpers as needed; do not silently change shared names between tasks.

```python
# contracts.py: field sets for QuerySpec, Requirement, EvidenceSpan,
# CoverageResult, AnswerRecord, BudgetState and UsageEvent follow the original handoff.
DocumentStore = dict[str, dict]
# QuestionInput is frozen with exactly id, question, as_of.
def load_question(record: dict) -> QuestionInput: ...
def load_query(record: dict) -> QuerySpec: ...
def load_span(record: dict) -> EvidenceSpan: ...
def manifest_hash(paths: list[Path]) -> str: ...

# parser.py: unsupported syntax raises UnsupportedQuery, caught by the engine.
def build_fiscal_calendar(documents: DocumentStore, as_of: str) -> dict: ...
def parse_query(question: str, as_of: str, aliases: dict[str, str], fiscal_calendar: dict) -> QuerySpec: ...
# units.py / extraction.py
def build_units(documents: DocumentStore) -> list[RetrievalUnit]: ...
def extract_candidates(units: list[RetrievalUnit], documents: DocumentStore) -> list[EvidenceSpan]: ...
# retrieval.py: public facade extracts only retrieved units; no reference loading.
class RetrievalBackend(Protocol):
    def retrieve(self, spec: QuerySpec, missing_ids: list[str], token_limit: int) -> list[EvidenceSpan]: ...
# coverage.py / numeric.py / policy.py
def audit_coverage(spec: QuerySpec, spans: list[EvidenceSpan], documents: DocumentStore) -> CoverageResult: ...
def execute_numeric(spec: QuerySpec, coverage: CoverageResult, spans: list[EvidenceSpan]) -> AnswerRecord: ...
def audit_answer(answer: AnswerRecord, spec: QuerySpec, spans: list[EvidenceSpan]) -> AnswerRecord: ...
def decide_route(spec: QuerySpec, coverage: CoverageResult, budget: BudgetState, state: RoutingState) -> RouteDecision: ...
# engine.py: explicit structured-input path is diagnostic unless parsed from the public question.
def run_spec(spec: QuerySpec, backends: dict[str, RetrievalBackend], documents: DocumentStore,
             config: dict, answerer: Answerer | None) -> RunTrace: ...
class Answerer(Protocol):
    def answer(self, spec: QuerySpec, spans: list[EvidenceSpan]) -> AnswerRecord: ...
# evaluation/evidence_aware
def build_split_manifest(queries: list[QuerySpec], documents: list[dict], seed: int) -> dict: ...
def validate_manifest(manifest: dict) -> None: ...
def reserve_call(event: UsageEvent, budget: BudgetState) -> None: ...
def run(config: dict, queries: list[QuerySpec]) -> Path: ...
def score_answers(traces: list[RunTrace], references: dict) -> list[dict]: ...
def paired_cluster_summary(rows: list[dict], cluster_key: str, seed: int) -> dict: ...
```

`load_question` rejects requirements, gold fields and all unknown fields. The CLI defaults to `input_mode=raw_question`: load QuestionInput records, build cutoff-aware public calendars, parse to QuerySpec, retain parse-failure rows, then pass only successfully parsed specs into the engine. `input_mode=diagnostic_spec` must be explicitly selected and gets a separate report. `RetrievalUnit` adds the design's source offsets/header fields. `RoutingState` records stage index and attempted action names. `RunTrace` contains raw question/as-of, parsed spec or parse failure, input mode, query/config/corpus/parser/policy hashes, per-stage selected and packed IDs, coverage snapshots, route decisions, final answer and usage events. `answerer=None` selects the executor-only control. A model answerer receives question/cutoff/source evidence only; the executor result is hidden and used for final audit. All matched arms share the same gate and audit. Narration with a supplied computed answer is a separately labeled optional mode, excluded from model-QA results. `BudgetState` adds retrieval/verification remaining counters, distinct from final-context allowance. Inference outputs carry no reference answers.

## Release A: offline engineering slice, Tasks 1–7

### Task 1: Isolated baseline and strict contracts

**Files:** create `pipelines/evidence_aware/{__init__,contracts}.py`, `tests/test_evidence_contracts.py`, `docs/v2/{baseline,decisions}.md`, `docs/v2/v1_files_sha256.json`, minimal locked offline dependencies. Read existing `pipelines/base.py` and release manifest.

**Consumes:** committed v1 snapshot and design. **Produces:** strict types/loaders, stable hashes and a clean isolated development baseline.

- [ ] Inspect source and target status. Use `superpowers:using-git-worktrees` for isolation selection; here the design selects a separate clone. Clone local committed history with `git clone --no-hardlinks /Users/sragh/Downloads/GenAI/LLM_Research/beyond-vector-search /Users/sragh/Downloads/Projects/beyond-vector-search`; verify HEAD, set existing public origin, and create `feat/evidence-aware-v2`. Do not reset an existing destination. Save every v1 release-file hash and source status in `docs/v2/baseline.md`. Copy the two reviewed planning documents into the checkout.
- [ ] Create an independent environment using the available uv-managed Python 3.12.9. Pin only the offline test dependencies initially. Do not install the entire legacy requirements file. Record interpreter/dependency versions and configuration hashes.
- [ ] Write failing tests: `test_rejects_gold_fields`, `test_rejects_nested_unknown_fields`, `test_decimal_roundtrip`, `test_nonfinite_decimal_rejected`, `test_stable_manifest`, `test_duplicate_requirement_ids_rejected`, `test_raw_question_rejects_requirements`. Assert `load_query` rejects `gold_answer`, nested `oracle_action`, and duplicate IDs; value `"120.00"` round-trips exactly; NaN/Infinity fail. Run `python -m pytest tests/test_evidence_contracts.py -q`; expect contract/import failure.
- [ ] Implement the original handoff's exact field contracts with enum/date/ID validation and stable serialization. Keep `__init__.py` free of SDK imports. Run the same command; require all tests pass. Commit only this task's files locally.

**First-session stop:** a verified isolated revision, preservation manifest and passing contract tests are a valid 90–120 minute checkpoint. Do not call this Release A complete.

### Task 2: Synthetic sources and leakage-safe manifests

**Files:** create `evaluation/evidence_aware/{__init__,dataset}.py`, `tests/fixtures/evidence_v2/{documents,queries,diagnostic_specs,references}.jsonl`, `tests/test_evidence_dataset.py`, `data/release/v2/split_manifest.json`; modify `evaluation/__init__.py` for lazy backward-compatible exports.

**Consumes:** Task 1 contracts. **Produces:** `build_split_manifest`, `validate_manifest`, eight original source fixtures with real offsets/hashes; references isolated from public questions.

- [ ] Write failing tests: `test_cross_company_bridge_stays_together`, `test_derived_template_and_source_overlap_rejected`, `test_v1_descendants_development_only`, `test_future_disclosure_ineligible`, `test_fixture_quote_slices_match`, `test_v2_import_does_not_import_legacy_evaluator`. Assert Alpha–Beta and Beta–Gamma cannot cross partitions; date after `as_of` is ineligible; every quote equals `text[start:end]`; importing the v2 dataset does not import `evaluation.metrics`. Run `python -m pytest tests/test_evidence_dataset.py -q`; expect failure.
- [ ] Implement manifest construction from inference-only query metadata and source ancestry, not answers. Make old evaluation exports lazy via module `__getattr__`; retain their existing public names and add an import-compatibility test in the full environment. Strictly separate public question text/as-of from diagnostic requirement specs and references. Template edges reflect shared base-case/paraphrase/generation ancestry, not generic public grammar; record grammar overlap separately and make no unseen-language claim.
- [ ] Keep `queries.jsonl` question-only; put handwritten structured requirements in `diagnostic_specs.jsonl` for unit diagnostics only. Create cases: complete extraction, mention-only, two-year growth, missing company, wrong fiscal period, incompatible units, late disclosure, conflicting restatement. Use a simple source-table fixture format with explicit column headers; compute actual hashes and spans from document text. Keep all eight in a smoke partition, not statistical train/test splits.
- [ ] Run the focused dataset tests; require zero forbidden overlaps and valid source slices. Commit the task's files.

### Task 3: Source-derived retrieval and conservative evidence coverage

**Files:** create `pipelines/evidence_aware/{parser,calendar,units,extraction,retrieval,coverage}.py`, `tests/test_evidence_coverage.py`, `tests/test_evidence_parser.py`.

**Consumes:** Tasks 1–2 documents and contracts. **Produces:** `build_fiscal_calendar`, `parse_query`, `build_units`, `extract_candidates`, BM25 implementation of `RetrievalBackend`, `audit_coverage`.

- [ ] Write failing tests: `test_mention_is_not_evidence`, `test_wrong_table_column_fails`, `test_tampered_quote_fails`, `test_headers_survive_packing`, `test_period_is_not_filing_year`, `test_retrieval_uses_source_units_without_references`, `test_unsupported_query_abstains`, `test_fiscal_calendar_uses_only_cutoff_eligible_sources`, `test_unknown_calendar_abstains`. Assert the first three remain incomplete; moving only the year header changes accepted periods; deleting references leaves retrieved unit IDs unchanged. Run `python -m pytest tests/test_evidence_coverage.py tests/test_evidence_parser.py -q`; expect failure.
- [ ] Define versioned deterministic grammar for extraction, sum, growth and ranking over entity aliases and fiscal years. Resolve exact fiscal dates through `build_fiscal_calendar(documents, as_of)` using eligible source metadata/XBRL contexts, never reference requirements or values. Reject unavailable/conflicting fiscal dates and unsupported wording. Adding the explicit registry parameter is a documented refinement of the original three-argument parser boundary. Define BM25 exactly as the design specifies; stable unit-ID ties. Separate rankable source units from extracted spans; preserve headers when packing.
- [ ] Implement source hash/quote validation and exact entity/metric/basis/period/unit/header checks. Dates beyond cutoff, ambiguous cells and unresolved values fail closed. Test identical duplicate values versus conflicting values explicitly. Expose raw-question parse failures separately from structured diagnostic input.
- [ ] Run the focused tests; require expected supported/missing IDs and no reference imports. Commit. Dense/hybrid replay interfaces may be added, but do not label these arms experimentally evaluated.

### Task 4: Audited arithmetic and final claims

**Files:** create `pipelines/evidence_aware/numeric.py`, `tests/test_evidence_numeric.py`.

**Consumes:** audited coverage and spans. **Produces:** `execute_numeric`, `audit_answer` with operand citations and explicit abstention reasons.

- [ ] Write failing parameterized tests: `test_growth_100_to_120_is_20_percent` asserts value `"20.00"` with percent unit; `test_exact_unit_scale_conversion`; `test_zero_and_negative_base_abstain`; `test_mixed_currency_abstains`; `test_missing_operand_abstains`; `test_ties_preserve_entities`; `test_rank_uses_unrounded_values`; `test_uncited_added_claim_rejected`. Run `python -m pytest tests/test_evidence_numeric.py -q`; expect failure.
- [ ] Implement Decimal operation whitelist; preserve exactness until display with ROUND_HALF_EVEN. Use ordered groups for ranking ties and cite every contributing operand. An answer audit verifies cited spans satisfy requirements and numerical claims match the executor; optional narration cannot introduce additional quantities.
- [ ] Run the numeric tests; require Alpha 20.00%, Beta 10.00%, correct ties and explicit failure reasons. Commit.

### Task 5: Bounded routing and orchestration

**Files:** create `pipelines/evidence_aware/{policy,engine,pipeline}.py`, `tests/test_evidence_policy.py`, `tests/test_evidence_adapter.py`.

**Consumes:** retrieval, gate, executor. **Produces:** `decide_route`, `run_spec`, `EvidenceAwarePipeline(BasePipeline)` with `load_corpus`, `query`, and method `run_spec(spec) -> RunTrace`. The adapter has an explicit configured `as_of`; never infer it from today's clock.

- [ ] Write failing tests: `test_complete_answers_after_cheap_only`, `test_missing_company_triggers_section_search`, `test_empty_stages_advance_without_provider_calls`, `test_expanded_search_runs_at_most_once`, `test_budget_exhaustion_abstains`, `test_packing_loss_reaudits_coverage`, `test_adapter_returns_pipeline_result`, `test_cumulative_allowance_blocks_escalation`, `test_model_prompt_excludes_executor_result`. Assert unresolved evidence produces exactly `cheap_search, section_search, expanded_search, abstain` with zero provider calls; stage history is monotonic even when backends return empty lists. Run `python -m pytest tests/test_evidence_policy.py -q`; expect failure.
- [ ] Implement explicit state transitions after each attempted action; check token reservations and monotonic deadlines before stages. Defaults: 8,192 inspected tokens per stage, cumulative retrieval 24,576 and verification 24,576, deadline 30,000 ms. `token_limit` bounds returned source-unit text including headers before extraction, not the whole BM25 index. Count repeated text on each inspection and separate indexing cost. Fixture estimates use whitespace tokens with explicit labels; actual model experiments use pinned tokenizer counts. Reaudit only packed evidence before execution. With `answerer=None`, return the audited deterministic result. A model answerer receives the question/cutoff and evidence only, while the executor result remains private to the auditor. Preserve one optional final narration call. Keep adapter import separate from SDK-free core; adapter tests run in the compatible full environment or a documented stubbed unit environment.
- [ ] Run focused policy tests; require bounded traces and zero provider invocation. Run the adapter check once dependencies are available; never silently call it passing if skipped. Commit.

### Task 6: Complete ledger and replay-safe inference CLI

**Files:** create `evaluation/evidence_aware/{ledger,runner}.py`, `scripts/run_evidence_v2.py`, `configs/evidence_v2_offline.json`, `tests/test_evidence_ledger.py`, `tests/test_evidence_inference_isolation.py`.

**Consumes:** engine and strict question-only inference records, parsed at runtime. **Produces:** `reserve_call`, `run`, immutable run directories and events; CLI `--config`, `--mode offline|live`, `--output`, `--dry-run`.

- [ ] Write failing tests: `test_zero_budget_never_calls_provider`, `test_retry_attempts_are_charged`, `test_unknown_price_is_null`, `test_timeout_retains_query_row`, `test_cache_key_changes_with_policy_or_corpus`, `test_replay_latency_is_not_provider_latency`, `test_existing_output_not_overwritten`, `test_reference_file_open_forbidden_during_inference`. Patch network/provider boundaries and reference-file access to raise. Run `python -m pytest tests/test_evidence_ledger.py tests/test_evidence_inference_isolation.py -q`; expect failure.
- [ ] Implement ledger with full original UsageEvent fields plus local peak-memory provenance; track failed/retried attempts. CLI validates provider settings and positive separately authorized live cap; no silent baseline replacement for unavailable artifacts. Save config, manifest, traces, usage, final run status; retain partial failures. Cache keys include corpus/query/parser/policy/model/prompt/budget/seed hashes.
- [ ] Run focused tests; then `python scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --mode offline --output results/evidence_v2/offline_001`. Require eight traces, one per fixture ID, no network, explicit replay/executor labeling. This command is proposed, not executed during planning.
- [ ] Commit implementation and portable sanitized fixture outputs; large/generated artifacts follow repository conventions. Never commit credentials or local absolute paths into public evidence.

### Task 7: Offline evaluation, failure report and Release A gate

**Files:** create `evaluation/evidence_aware/report.py`, `scripts/report_evidence_v2.py`, `tests/test_evidence_report.py`, `docs/v2/{methods,annotation_protocol,results}.md`.

**Consumes:** saved traces and separate references. **Produces:** `score_answers`, `paired_cluster_summary`, JSON and human-readable offline report.

- [ ] Write failing tests: `test_errors_stay_in_denominator`, `test_correct_abstention_not_counted_as_answer_success`, `test_no_correct_answers_has_null_cost_per_correct`, `test_repeats_resample_with_company_component`, `test_oracle_excluded_from_deployable_rows`, `test_infeasible_context_has_null_accuracy`, `test_missing_arm_or_query_prevents_paired_claim`, `test_small_cluster_count_limits_claim`. Run `python -m pytest tests/test_evidence_report.py -q`; expect failure.
- [ ] Implement separate answerable/unanswerable metrics and diagnostic/raw-question input modes. Reports show per-requirement coverage, selected spans, routing reasons, arithmetic, citations, failures, resource provenance and known limitations. Statistics reject duplicate/missing paired rows and keep repetitions in their independent component. Fixture reports have no population-confidence claim.
- [ ] Run `python -m pytest tests/test_evidence_*.py -q`; require passing applicable tests. Run `python scripts/report_evidence_v2.py --results results/evidence_v2/offline_001`; require deterministic regeneration from saved files without providers. Recompute all preserved v1 hashes; require exact match. In a separate compatible environment, run the existing suite with `python -m pytest -q`; report any dependency or baseline failure explicitly.
- [ ] Commit task files and record actual checks/output paths. Mark Release A complete only if eight traces, report regeneration, failure-path checks, zero-network checks and v1 preservation pass. Unavailable full-suite checks remain an explicit completion limitation.

## Release B: real-filings engineering pilot

### Task 8: Raw HTML extraction and real development cases

**Files:** extend `units.py`, `extraction.py`; create `scripts/prepare_evidence_v2.py`, `configs/evidence_v2_real_dev.json`, `tests/test_evidence_html.py`, `data/release/v2/{source_manifest,real_dev_questions}.json`, separate `data/release/v2/references/real_dev.jsonl`, `docs/v2/extraction_audit.md`.

**Consumes:** local raw HTML copied explicitly into ignored v2 working data, with original accession/CIK lineage; no references in the inference stage. **Produces:** reproducible normalized source/table map and 12–20 development cases, at least four company groups if feasible.

- [ ] Inspect raw HTML paths without accessing `.env`; map them to frozen corpus metadata and hash original bytes before copying. Record missing sources. Add a compact redistributable or synthetic equivalent of each supported layout; full filings require source/terms documentation. Never pretend the clone included untracked HTML.
- [ ] Write failing tests: `test_html_cell_links_row_period_and_units`, `test_ambiguous_merged_header_abstains`, `test_html_missing_fails_closed`, `test_raw_to_normalized_lineage`, `test_reported_restated_conflict`, `test_no_reference_needed_for_extraction`. For a known cell assert original HTML locator, real normalized quote slice and raw hash; swapping column years must invalidate support. Run `python -m pytest tests/test_evidence_html.py -q`; expect failure.
- [ ] Implement pinned conservative HTML table extraction, raw-to-normalized segment mapping and origin locators. Handle supported layouts only. Build real development questions independently of model outcomes; keep raw text/as-of public and references separate. Include answerable cases and known missing/late/conflicting cases. If fewer than 12 cases or four groups are feasible, report actual counts and narrower scope rather than fabricate coverage.
- [ ] Run real-source preparation and inference with config `configs/evidence_v2_real_dev.json`, then regenerate the report from saved traces. Require source-hash validation and no gold input; disclose parser success, extractor failures, unsupported grammar and abstentions. Commit portable fixtures/provenance/docs; mark B as an engineering pilot, with actual review status and no independent accuracy claim without human labels.

## Release C and conditional research

### Task 9: Strong controls, locked splits and an experiment-ready manifest

**Files:** extend `retrieval.py`, `dataset.py`, `policy.py`; create `tests/test_evidence_baselines.py`, `tests/test_evidence_experiment_manifest.py`, `configs/evidence_v2_experiment.json`, `docs/v2/{resource_probe,preregistration}.md`, versioned v2 split/annotation manifests.

**Consumes:** A/B error analysis and source-derived units. **Produces:** matched strategy/scheduling arms and a frozen experiment definition, not an automatic paid run.

- [ ] Write failing tests: `test_all_arms_share_units_and_answerer`, `test_always_maximum_attempts_all_three_stages`, `test_complexity_control_uses_only_operand_count`, `test_rrf_rank_one_exact_score`, `test_split_overlap_rejected`, `test_model_revision_and_prompt_required`, `test_every_arm_has_identical_postpack_gate_and_audit`, `test_generic_grammar_does_not_connect_unrelated_cases`. Assert RRF for rank 1 in both lists equals `2/61`; test outcomes cannot alter complexity routing; identical final context/output limits appear in every matched arm. Run `python -m pytest tests/test_evidence_baselines.py tests/test_evidence_experiment_manifest.py -q`; expect failure.
- [ ] Implement always-cheap, always-maximum, evidence-rule and complexity policies. Default complexity control: <=2 operands uses cheap only, >2 runs all three bounded stages; freeze this author-selected rule before evaluation. Keep gate/executor common for scheduling; gate ablations are separate. Add dense/RRF/reranker through injected adapters, with a short resource probe, pinned revisions/licenses and download sizes before selecting models. Missing backends are unavailable arms, not BM25 under another name.
- [ ] Draft a 100–200-question pilot collection and independent annotation packet; enforce company components, shared source/template grouping and development-only ancestry of v1/B cases. Do not force a split if components collapse. Record effective independent groups and actual review counts. If human review is unavailable, continue as an agent-reviewed engineering study and defer confirmatory claims.
- [ ] Freeze exact arm/config/model/prompt/corpus hashes, paired run order, budget profiles, failure policy and analysis. Include a bounded candidate grid of 4,096 and 8,192 final-context tokens as the author default; final output stays 512. Choose primary comparator and one budget on development before any test outcome. Estimate exact requests/tokens and costs; keep live execution disabled pending separately authorized spend. A provider-free local measured study remains valid if all arms use the same answerer and local time/memory are reported.
- [ ] Run focused tests and manifest dry-run; require split checks, fixed comparisons and honest unavailable-arm status. Commit. A learned router requires measured benefit opportunity, training-only counterfactual labels and a separate approved design; no router training is included here.

### Task 10: Measured comparison and portfolio evidence

**Files:** extend `report.py`; create `tests/test_evidence_claims.py`, `docs/v2/{case_study,interview_walkthrough,reproduction}.md`, `examples/evidence_v2/`, generated quality/resource plot; update README only with completed evidence.

**Consumes:** frozen experiment manifest; measured local or explicitly authorized provider runs. **Produces:** reproducible findings, demo and evidence-linked claims.

- [ ] Write failing checks: `test_claims_reference_run_and_metric`, `test_replay_not_measured_latency`, `test_unknown_cost_blocks_savings_claim`, `test_noninferiority_requires_interval`, `test_raw_question_results_separate_from_diagnostics`. Run `python -m pytest tests/test_evidence_claims.py -q`; expect failure. Implement claim/report validation only where machine-checkable; scientific interpretation remains a documented review.
- [ ] Execute only the frozen permitted arms; at least three randomized paired fresh repetitions for provider comparisons when approved. Preserve raw failures, retries, missing-arm records, config hashes and actual usage. For a no-provider study label deterministic/local controls explicitly. Never tune on locked test outcomes; fix discovered bugs through a recorded new protocol/version.
- [ ] Generate quality/resource curves and paired 95% cluster intervals from saved outputs. Report supported answer success and correct abstention separately, index/online/judging costs separately, p50/p95 latency and peak memory. Assess the preregistered hypothesis without turning an inconclusive interval into a win; if no fully priced live data exist, publish no dollar-savings claim.
- [ ] Package a five-minute offline walkthrough: one successful early stop, one missing-company escalation, one principled abstention, and one unresolved failure. Add a 60-second README explanation, source-to-answer trace, exact reproduction commands, actual limitations, and an ownership/AI-assistance note. The user should be able to explain the parser, one source cell, one route, the strongest baseline, and a failed hypothesis.
- [ ] Run focused and relevant regression tests; regenerate reports from a fresh committed export in an isolated environment; verify v1 hashes and inspect demo output. Save exact command results. Commit locally; prepare factual resume language from the run evidence. Publishing, outreach and resume changes are separate user actions.

## Acceptance and scope map

| Requirement from original handoff | Task(s) |
|---|---|
| Preserve v1 and common adapter interface | 1, 5, 7, 10 |
| Strict inference contracts, provenance, no gold | 1–3, 6, 8 |
| Eight-case offline trace/report | 2–7 |
| Decimal arithmetic, operand citations, abstention | 3–5 |
| Three-stage routing and explicit history | 5–6 |
| Ledger, replay, unknown prices and retained failures | 6–7, 10 |
| Strong retrieval controls, matched models and budgets | 9–10 |
| Real source tables and independent annotations | 8–9 |
| Grouped/temporal splits and paired uncertainty | 2, 7, 9–10 |
| Held-out external generalization and possible paper | Deferred research release D; protocol after C |
| Learned router | Deferred unless counterfactual evidence justifies it |

**Stop condition:** A–C deliver a useful applied AI/ML portfolio project even if extra retrieval does not beat hybrid retrieval or gate overhead erases savings. Do not expand to a platform, finance assistant, training project or frontend to avoid reporting that result.

**Next concrete action after design review:** Task 1, isolated baseline plus strict contracts. Native sequential execution is the author recommendation because tasks share tight schema interfaces and this is one repository. Review the design before building; the current deliverable is planning only.
