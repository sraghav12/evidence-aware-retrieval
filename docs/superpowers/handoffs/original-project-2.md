# Evidence-Aware Budgeted Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL when available: Use `superpowers:executing-plans` to implement this plan task-by-task. Use `superpowers:subagent-driven-development` only if the user explicitly authorizes delegation. If these skills are unavailable, execute the same checked steps sequentially and record verification evidence. This document describes proposed work; a user instructing you to execute its kickoff authorizes the offline milestone. It does not establish a paid API budget.

**Goal:** Extend Beyond Vector Search with an auditable evidence-completeness gate that selectively spends more retrieval effort while preserving answer quality under measured resource budgets.

**Architecture:** Parse requested quantities, entities and fiscal periods; retrieve cheaply; verify cited evidence against every required operand; escalate incomplete cases through bounded section search. A fixed answer model consumes the selected evidence, while a deterministic executor computes supported numerical results. Separate strategy experiments from budgeted scheduling experiments.

**Tech Stack:** Existing Python >=3.11 project, pytest, JSONL artifacts, standard-library dataclasses/Decimal, existing retrieval dependencies where useful; optional local embedding/reranking models after checking hardware fit, license and download size. No additional service or training framework is necessary for the offline milestone.

**Spec:** The embedded design below is the complete portable specification. All paths are relative to the future Beyond Vector Search checkout; this file requires no sibling plans or private profile files.

## Global Constraints

- Preserve published `data/release/v1/` and `results/release_v1/` byte-for-byte; put new artifacts under v2 paths.
- Work in a new isolated clone or suitable existing checkout, inspect branch/status before edits, and never overwrite unrelated work.
- Default to offline fixtures and replay, with network providers disabled and `max_usd: 0`.
- The available machine is assumed to be a 24 GB Mac. GPU access and paid API budget are unconfirmed. Ordinary free local setup can proceed within an implementation request; first-session fixtures require neither model downloads nor remote calls.
- The provisional 8–10 hours/week is shared across all three selected projects, not dedicated to this project. Schedule by completed milestones; earlier 2–3 week estimates are not commitments.
- Reference answers, human evidence labels, oracle choices and evaluation-only fields must never enter inference features or prompts.
- Start with a rule; train no router until the rule and strong retrieval baselines have been measured.
- Keep the existing 43 published questions as development data; do not relabel them an untouched test.
- Independent human annotation is required before claiming independently validated correctness; an AI cannot certify its own labels as human review.

## Review Focus

1. A relevant company mention without the requested metric, unit or period must fail coverage; pin with Task 3's mention-only and wrong-column tests.
2. Cross-company questions can connect train and test companies; reject component overlap and post-cutoff disclosures in Task 2.
3. A correct-looking result from incompatible units, zero denominators or restatements must abstain or flag conflict; pin with Task 4.
4. Cached answers, timeouts, retries and missing prices can create false savings; Task 6 must retain failures and distinguish replay from fresh execution.
5. Gold or oracle-derived information can leak through query metadata and routing labels; Task 5 must reject gold-tainted inference inputs and test test-label exclusion.

---

## Embedded design: goal, rationale and scope

The practical problem is incomplete evidence, not merely irrelevant retrieval. A top-five search may retrieve Apple and NVIDIA passages yet omit AMD revenue, use a calendar-year statement for a fiscal-year question, or present a narrative mention without the required table column. Answer generation then fills the gap or silently drops a company. The proposed system makes these missing operands observable before answering.

This is an original project proposal informed by the sources below, not an established novel method or a promised accuracy improvement. Its portfolio value is a reproducible extension of an existing benchmark: explicit evidence contracts, conservative abstention, fair baselines, and complete resource traces. Its possible research value is testing whether auditable operand coverage predicts the need for escalation better than generic relevance or query complexity.

The MVP supports direct numerical extraction, year-over-year growth, sums and rankings over specified SEC annual filings. Exclude open-ended investment advice, unconstrained accounting interpretation, arbitrary generated Python, a production financial assistant, frontend polish, model fine-tuning and autonomous corpus expansion. Unsupported accounting definitions or ambiguous questions should produce a structured abstention.

### Observed baseline, verified October 17, 2026

Read-only GitHub API inspection found default branch `main` at commit `675733109b30e80ce40c0a796bc0dd89e616c4ef`. The [published README](https://github.com/sraghav12/beyond-vector-search/tree/675733109b30e80ce40c0a796bc0dd89e616c4ef) describes v1 as 150 filings, 30 companies and 43 retained questions, with saved predictions/reporting. It is exploratory: one run, one answer model, agent-checked references and no independent human certification. Full-context was infeasible, not zero accuracy. These are repository observations, not newly established canonical resume facts.

Actual modules inspected at that commit:

| Existing path/interface | Observed behavior | Proposed extension boundary |
|---|---|---|
| `pipelines/base.py` | `BasePipeline.load_corpus(str)`, `query(str) -> PipelineResult`, and `timed_query(question, query_id="")`; result has answer, latency, tokens, cost, optional trace | Preserve this interface; v2 adapter returns detailed trace without altering v1 fields |
| `pipelines/vector_rag/pipeline.py` | `VectorRAGPipeline`; `_read_corpus`, `_chunk_documents`, `_build_context_block`, `query`; Chroma retrieval and generation are combined in `query` | Add independent retrieval backend; do not call `query` as a retrieval-only primitive |
| `pipelines/pageindex/pipeline.py` | `PageIndexPipeline`; `_split_doc_into_sections`, `_lexical_prefilter_sections`, `_selection_outline_for_question`; `query` performs model-based section selection and answering | Borrow section parsing semantics through an explicit adapter; charge any model selector separately |
| `evaluation/runner.py` | `build_pipeline`, `run_pipeline`, gold loading/resolution; writes result traces | Keep existing v1 runner intact; create separate v2 inference/evaluation entrypoints |
| `scripts/run_benchmark.py`, `evaluation/metrics.py` | Existing CLI and evaluation helpers | Reuse reporting ideas, not implicit v1 experimental defaults |

Private methods are observed implementation details, not stable public contracts. Inspect their current bodies again during execution; if upstream moved, document the mapping before editing. Existing constructors can instantiate provider clients, so offline tests must not instantiate them accidentally. Current package discovery includes `pipelines*` and `evaluation*`, which supports the proposed package locations.

### Worked example

Use a synthetic fixture: “As of 2025-03-01, rank Alpha and Beta by FY2024 revenue growth over FY2023.” Alpha has revenue 100 then 120 USD million; Beta has 200 then 220. The requirements are four revenue operands, not two company mentions. Cheap retrieval supplies Alpha's table and a Beta narrative paragraph: coverage is 2/4, so the rule requests Beta's income-statement section. The executor calculates 20% and 10%, ranks Alpha first, and cites both years for each company. If Beta's FY2024 filing was disclosed after the cutoff, abstain on the complete ranking even if its fiscal period ends before the cutoff. Never fabricate a complete ordering from a partial answer.

## Data contracts and evidence gate

Create `pipelines/evidence_aware/contracts.py` with frozen dataclasses and strict JSON loading. Reject unknown inference fields. All decimal quantities are strings in serialized artifacts; all dates use ISO-8601. Identity uses CIK when available, not ticker alone. Offsets are zero-based, half-open character ranges in a specified normalized document hash; preserve a mapping to raw HTML/table locations for audit.

Core types:

- `QuerySpec(id, question, as_of, requirements, operation)`: public inference input. `requirements` contains `Requirement(id, entity_id, metric, period_start, period_end, fiscal_year, unit, accounting_basis)`; metric aliases are versioned, never inferred from gold.
- `EvidenceSpan(id, doc_id, accession, doc_sha256, entity_id, disclosed_at, start, end, quote, metric, period_start, period_end, fiscal_year, unit, value, accounting_basis, table_headers, source_url)`: candidate operand with provenance. Extraction status and parser version accompany each record.
- `CoverageResult(complete, supported_requirement_ids, missing_requirement_ids, conflicts, audited_span_ids)`: gate output, not a probability of answer correctness.
- `AnswerRecord(status, value, unit, citations, reason)`: `status` is `answered`, `abstained` or `error`; rankings serialize ordered items in `value`.
- `BudgetState(context_tokens_remaining, output_tokens_remaining, calls_remaining, max_usd, estimated_usd_reserved, deadline_ms)`, `RoutingState(stage_index, attempted_actions)`, `RouteDecision(action, reason_codes, missing_requirement_ids)`, `UsageEvent(...)` and `RunTrace(...)`: defined in Task 1. `RoutingState` explicitly records completed retrieval stages and attempted actions; resource counts cannot stand in for stage history.

Synthetic inference and evidence examples, shortened to one requirement:

```json
{
  "id": "fixture_growth_alpha",
  "question": "What was Alpha FY2024 revenue?",
  "as_of": "2025-03-01",
  "requirements": [{
    "id": "alpha_rev_2024", "entity_id": "synthetic:alpha",
    "metric": "revenue", "period_start": "2024-01-01",
    "period_end": "2024-12-31", "fiscal_year": 2024,
    "unit": "USD_million", "accounting_basis": "reported"
  }],
  "operation": {"kind": "extract", "operands": ["alpha_rev_2024"]}
}
```

```json
{
  "id": "alpha_span_1", "doc_id": "alpha_annual_2024",
  "accession": "synthetic", "doc_sha256": "fixture_sha256",
  "entity_id": "synthetic:alpha", "disclosed_at": "2025-02-14",
  "start": 0, "end": 53,
  "quote": "Revenue (USD million), year ended 2024-12-31: 120",
  "metric": "revenue", "period_start": "2024-01-01",
  "period_end": "2024-12-31", "fiscal_year": 2024,
  "unit": "USD_million", "value": "120", "accounting_basis": "reported",
  "table_headers": ["USD million", "2024"],
  "source_url": "fixture://alpha"
}
```

Example hashes/offsets are illustrative; actual fixture creation must calculate the real hash and offsets and verify `document[start:end] == quote` rather than trusting these placeholder values.

### Operational completeness rule

`parse_query(question, as_of, aliases) -> QuerySpec` produces requested operands from the question and allowed company/metric dictionaries. The controlled fixture grammar is deterministic initially. Human-authored requirement specs may support diagnostic tests, but production query parsing is measured separately; never silently substitute human test annotations into deployed routing. Unsupported natural language returns `abstained: unsupported_query`.

`audit_coverage(spec, spans, documents) -> CoverageResult` accepts a requirement only when: entity identity matches; the metric and accounting basis match; the period dates and fiscal label match; units are explicit or a whitelisted exact conversion exists; the value is linked to the correct table row/column headers; source hash and quote offsets validate; and disclosure is on or before `as_of`. Filing year metadata alone is insufficient because a filing contains several fiscal periods. Preserve consolidated versus segment definitions and reported versus restated versions. Conflicting eligible values fail closed until the specified version policy resolves them.

A span must entail the operand, not just contain its words. Initially implement high-precision extraction of explicitly labeled numerical table cells with their headers; ambiguous narrative spans remain incomplete. A later model verifier may propose structured candidates but cannot bypass provenance/unit/period checks, and its cost and false-completeness rate are measured. Citation existence is necessary but not sufficient; independently audit entailment on labeled data.

`execute_numeric(spec, coverage, spans) -> AnswerRecord` uses Decimal and a fixed operation whitelist: extraction, sum, growth `(new-old)/old*100`, and ranking. It refuses missing coverage, incompatible currencies, zero denominators and unresolved accounting conflicts; negative-base growth is unsupported in the MVP. Preserve precision until final display; use ROUND_HALF_EVEN at two decimal percentage places. Rankings use unrounded values, return explicit ties and include every requested entity. No `eval`, generated code or execution of document instructions. Each numerical claim cites its operands; final answer auditing rejects uncited added claims.

Exact proposed callable boundaries (types are the contracts above; `DocumentStore = dict[str, dict]`):

```python
def parse_query(question: str, as_of: str, aliases: dict[str, str]) -> QuerySpec: ...
def audit_coverage(spec: QuerySpec, spans: list[EvidenceSpan], documents: DocumentStore) -> CoverageResult: ...
def execute_numeric(spec: QuerySpec, coverage: CoverageResult, spans: list[EvidenceSpan]) -> AnswerRecord: ...
def decide_route(spec: QuerySpec, coverage: CoverageResult, budget: BudgetState, state: RoutingState) -> RouteDecision: ...
class RetrievalBackend(Protocol):
    def retrieve(self, spec: QuerySpec, missing_ids: list[str], token_limit: int) -> list[EvidenceSpan]: ...
```

## Routing, retrieval and experimental controls

The rule policy is `decide_route(spec, coverage, budget, state) -> RouteDecision`. Complete audited coverage means `answer`. Otherwise use `section_search` for missing operands if resources allow and it has not been attempted; after one section escalation use `expanded_search` once; then abstain if still incomplete. The first cheap search always occurs. Initialize state after cheap retrieval as `RoutingState(stage_index=1, attempted_actions=["cheap_search"])`; append each attempted stage and increment the index even when it returns no evidence. Attempts cannot be removed on retry or inferred from provider-call counts because local retrieval may make no provider call. A request may therefore make at most three retrieval stages and one final answer-generation call. Empty, malformed or conflicting evidence never triggers an unbounded loop. The model is not allowed to redefine completeness.

New `RetrievalBackend.retrieve(spec, missing_ids, token_limit) -> list[EvidenceSpan]` separates retrieval from answer generation. Implement local BM25 first; add dense and reciprocal-rank-fusion hybrid over the same indexed units, then a pinned cross-encoder reranker as an optional backend. Freeze tokenizer, chunking/table-boundary policy, candidate pool, ranking ties and packing order. Keep table headers with cells; report when evidence is omitted by packing.

Use two experiment tracks:

1. **Strategy effectiveness:** fixed answer model/version, prompt, decoding, context-token cap, output cap and candidate units across BM25, dense, hybrid plus rerank and section selection. Compare selected evidence without claiming savings caused by switching answer models. Include a same-budget relevance-only packing control.
2. **Budgeted scheduling:** same answer model and final answer limits, comparing always-cheap, always-expensive, rule routing and optionally learned routing. Always-expensive uses the defined maximum bounded retrieval policy, not an infeasible full-corpus prompt. Show quality/resource Pareto curves at predeclared budgets; separate larger-context variants so extra context is not attributed solely to routing.

In model-based comparisons, require the same final answerer in every arm and audit its output against the deterministic result; count audit rejection as abstention. Report executor-only answers as a separate deterministic control, never silently mix them into an answer-model comparison.

For the pilot choose maximum final context 8,192 tokens, answer output 512 tokens, cheap retrieval pool 20, hybrid pool 60, and maximum packed sections 12. These are proposed starting configuration values, not empirically optimal settings. Charge all selector prompts outside final context to resource totals. Do not reuse v1 default token limits implicitly. A full-context row is `infeasible` if it cannot fit, never a fabricated scored answer.

Optional learned routing comes after evidence that features predict useful escalation. Generate counterfactual route labels only by exhaustive bounded runs on training questions, with the fixed answer model and cost function. Candidate features are query operand count, supported/missing ratios, score gaps, conflict flags, and token/call budget remaining. Begin with logistic regression; tune thresholds on development only. No test outcomes, reference values, gold spans, post-answer correctness, future evidence or oracle decisions are inference features. Report an oracle's post-hoc ceiling separately and exclude it from deployable comparisons.

## Dataset, independent review and statistics

First-session fixtures need no new SEC download. Preserve frozen v1 corpus hashes and document lineage. For later acquisition, follow [SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data): declared contact User-Agent, caching, backoff and conservative aggregate rate below the current 10 requests/second ceiling; recheck policy before downloading. Record accession, CIK, retrieval time, disclosure timestamp, fiscal dates, raw/normalized hashes and parser version. Public availability does not substitute for documenting redistribution terms.

Target a 100–200-question pilot, approximately balanced across extraction, growth, aggregation/ranking and deliberately unanswerable cases, with at least 12 independent company groups if feasible. This is a feasibility target, not a power calculation. A larger confirmatory study might require hundreds more questions and dozens of independent groups; estimate its required size from pilot paired discordance and cluster correlation by simulation before fixing a target. Do not promise that 200 questions resolves a two-point effect.

Construct the company-question bipartite graph first. All companies linked by any cross-company question form a connected component assigned wholly to train, development or test. Keep duplicate templates, source documents and derived questions grouped. Design cross-company questions within intended partitions to avoid creating one giant component; if grouping leaves too few independent units, redesign collection, not the leakage rule. Add a later-fiscal-period holdout with non-overlapping source-document ancestry inside a separately declared temporal experiment. Record calendar ranges, fiscal periods and disclosure cutoffs separately; test contemporaneous unavailability explicitly. Existing 43 questions remain development and may not migrate into test via paraphrases.

Store public inference questions and protected evaluation references separately. Reference records contain answer, arithmetic, all required evidence spans, acceptable rounding, answerability, reviewers and adjudication. An independent human checks source tables and calculation for every confirmatory item; a second human independently labels a stratified minimum 25% including all conflict/unanswerable cases. Record disagreements, correction history and agreement with uncertainty. If reviewers are unavailable, ship an engineering pilot labeled agent-reviewed; do not claim human validation or run a confirmatory conclusion.

Primary quality endpoint: supported numerical correctness, requiring correct result, complete requested entities/periods and entailed citations. Also report answer correctness alone, coverage recall, gate false-complete rate, citation precision, abstention/coverage curves, unsupported answers and parser failure. Keep errors and timeouts in intention-to-evaluate denominators, distinguish correct abstention from successful answer, and show answerable/unanswerable strata. Cost per correct answer is undefined when no answers are correct; never emit infinity disguised as zero.

Preregister after the pilot but before touching test outcomes: primary comparator, budget, quality noninferiority margin, cost reduction target, statistical method and multiplicity policy. A candidate decision rule is a 2 percentage-point noninferiority margin versus always-expensive plus at least 15% measured online-cost reduction. These are negotiable design choices, not success guarantees; justify them against application risk and power. A nonsignificant difference does not demonstrate noninferiority.

Run at least three paired fresh repetitions when spending is approved, with identical question IDs/model settings across arms, randomized arm order, unique run IDs and explicit cache mode. Repetition exposes provider variability; it does not multiply the number of independent questions. Compute paired differences and 95% cluster-bootstrap intervals resampling company connected components, keeping question repetitions together; for temporal/source dependence use the more conservative grouping and disclose the effective cluster count. Report sparse-group limitations, discordant pairs, per-task estimates, p50/p95 latency and failure counts. Do not repeatedly inspect test results to tune policy.

## Resource accounting and replay

`UsageEvent(event_id, query_id, stage, provider, model_revision, input_tokens, output_tokens, elapsed_ms, attempts, status, estimated_usd, billed_usd, price_version, cache_mode)` records stages `indexing`, `retrieval`, `router`, `verification`, `generation` and `judging`. Local stages record wall time and measured memory, with API cost zero and compute cost unpriced; that is not free compute. Unknown prices or missing token usage become null/unknown and invalidate a complete cost claim, never zero.

Proposed offline configuration, not an executed experiment:

```json
{"schema_version": 2, "provider_enabled": false, "max_usd": 0,
 "answerer": "fixture_replay", "policy": "coverage_rule_v1",
 "max_context_tokens": 8192, "max_output_tokens": 512,
 "max_retrieval_stages": 3, "cache_mode": "replay",
 "queries": "tests/fixtures/evidence_v2/queries.jsonl"}
```

Reserve a conservative maximum before each provider call; reconcile returned usage and count retries/failures. Estimated caps cannot guarantee an exact invoice ceiling or cancel an already submitted call. Default zero-budget mode forbids provider invocation entirely. Separate online query totals from one-time indexing, dataset annotation and offline judging, and publish both unamortized totals and a stated amortization scenario. Provider invoice reconciliation remains separate from token-price estimates. Replay cost describes the original recorded execution; replay latency is not generation latency. Cache keys include corpus, query spec, parser, policy, model revision, prompt, budget and seed hashes.

## Proposed file map and execution tasks

All paths below are proposed unless explicitly identified as existing above. No commands in this plan have been executed against a product checkout. Commit steps are local checkpoints; pushing, publishing and spending need separate authorization.

### Task 1: Safe baseline and strict contracts

**Files:** Create `pipelines/evidence_aware/{__init__,contracts}.py`, `tests/test_evidence_contracts.py`, `docs/v2/baseline.md`; read existing `pipelines/base.py`.

**Interfaces:** Produce the dataclasses above; `load_query(record: dict) -> QuerySpec`, `load_span(record: dict) -> EvidenceSpan`, `manifest_hash(paths: list[Path]) -> str`. `RunTrace` contains query/config/corpus hashes, decisions, coverage snapshots, packed IDs, answer and usage events; JSON serialization is stable.

- [ ] Inspect a new isolated clone's `git status --short` and `git branch --show-current`; record its revision and v1 hashes. Stop on unexpected local changes.
- [ ] Write `test_rejects_gold_fields`, `test_decimal_roundtrip`, `test_stable_manifest`; assert `gold_answer` is rejected and decimal strings remain exact. Run `python -m pytest tests/test_evidence_contracts.py -q`; expect import failure before implementation.
- [ ] Implement contracts/strict loaders and write observed revision mapping in `docs/v2/baseline.md`.
- [ ] Rerun the focused tests; expect all pass. Commit only this task's files.

### Task 2: Frozen fixtures and leakage-safe manifests

**Files:** Create `evaluation/evidence_aware/{__init__,dataset}.py`, `tests/fixtures/evidence_v2/{documents,queries,references}.jsonl`, `tests/test_evidence_dataset.py`, `data/release/v2/split_manifest.json`.

**Interfaces:** Consume Task 1 contracts; produce `build_split_manifest(queries: list[QuerySpec], documents: list[dict], seed: int) -> dict` and `validate_manifest(manifest: dict) -> None`. References are evaluation-only.

- [ ] Write tests for a cross-company bridge, duplicated question, source ancestry overlap and unavailable disclosure; assert the bridge stays in one component and post-cutoff spans are ineligible. Run the focused test file; expect failure.
- [ ] Create eight synthetic cases: complete extraction, mention-only, growth, missing company, wrong period, mixed units, later disclosure and conflicting restatement. Compute real offsets/hashes.
- [ ] Implement grouping, split validation and provenance manifests; existing43 IDs and derivatives are development-only.
- [ ] Run `python -m pytest tests/test_evidence_dataset.py -q`; expect pass with zero forbidden overlaps. Commit fixtures and implementation.

### Task 3: Retrieval and auditable coverage

**Files:** Create `pipelines/evidence_aware/{retrieval,coverage}.py`, `tests/test_evidence_coverage.py`.

**Interfaces:** Consume Task 1/2; produce `RetrievalBackend.retrieve(...)`, `parse_query(...)`, `audit_coverage(...)` with signatures specified above; a `DocumentStore` mapping document IDs to normalized text/hash backs auditing.

- [ ] Write `test_mention_is_not_evidence`, `test_wrong_table_column_fails`, `test_tampered_quote_fails`, `test_headers_survive_packing`; assert incomplete coverage for the first three. Run focused tests; expect failure.
- [ ] Implement deterministic query grammar, local BM25 backend and conservative table-cell gate; reject unsupported grammar explicitly.
- [ ] Add dense/hybrid/rerank adapter contracts with replay fixtures, not paid embedding calls or unapproved downloads. Mark unavailable live arms as unavailable.
- [ ] Run `python -m pytest tests/test_evidence_coverage.py -q`; expect pass and exact supported IDs. Commit.

### Task 4: Numeric execution and citations

**Files:** Create `pipelines/evidence_aware/numeric.py`, `tests/test_evidence_numeric.py`.

**Interfaces:** Consume audited coverage; produce `execute_numeric(...) -> AnswerRecord` and `audit_answer(answer: AnswerRecord, spec: QuerySpec, spans: list[EvidenceSpan]) -> AnswerRecord`.

- [ ] Write parameterized tests: 100→120 is `20.00%`; equivalent USD units convert; mixed currencies, zero/negative base and conflicting restatements abstain; tied rankings preserve both entities; missing operand fails. Run focused tests; expect failure.
- [ ] Implement Decimal whitelist and claim-to-operand citations; never execute model code. Reject final claims unsupported by cited operand IDs.
- [ ] Run `python -m pytest tests/test_evidence_numeric.py -q`; expect pass with deterministic answers and explicit abstention reasons. Commit.

### Task 5: Rule routing and compatibility adapter

**Files:** Create `pipelines/evidence_aware/{policy,pipeline}.py`, `tests/test_evidence_policy.py`; leave existing v1 pipeline registration unchanged initially.

**Interfaces:** Produce `decide_route(spec: QuerySpec, coverage: CoverageResult, budget: BudgetState, state: RoutingState) -> RouteDecision`; `EvidenceAwarePipeline(BasePipeline)` accepts injected backends, document store, config and answerer. `query(str) -> PipelineResult` retains the existing contract; a new `run_spec(spec: QuerySpec) -> RunTrace` supports v2 structured inputs.

- [ ] Write tests for answer-on-complete, missing-company escalation, two-escalation maximum, exhausted budget, gold-tainted inputs and no test labels in routing features; expect failure before code. With unchanged provider-call count across local stages, assert history still advances cheap → section → expanded → abstain and no stage repeats after empty evidence.
- [ ] Implement bounded rule stages and trace transitions; numerical results come from Task 4. Use an injected replay answerer initially. Optional narration must preserve the audited result and use one fixed answer model across comparisons.
- [ ] Run `python -m pytest tests/test_evidence_policy.py -q`; expect all pass and zero provider calls. Commit. Defer learned routing unless its later research gate passes.

### Task 6: Budget ledger and replay-safe CLI

**Files:** Create `evaluation/evidence_aware/{ledger,runner}.py`, `scripts/run_evidence_v2.py`, `configs/evidence_v2_offline.json`, `tests/test_evidence_ledger.py`.

**Interfaces:** Produce `reserve_call(event: UsageEvent, budget: BudgetState) -> None`, `run(config: dict, queries: list[QuerySpec]) -> Path`; reservations raise `BudgetExceeded`. CLI supports `--config`, `--mode offline|live`, `--output`, `--dry-run`; live requires an explicitly supplied positive budget and provider enablement.

- [ ] Write tests for zero-budget blocking, retry accounting, unknown price, timeout retention, distinct cache keys and replay labeling. Run focused tests; expect failure.
- [ ] Implement stage ledger, usage provenance, unique-run outputs and CLI validation. Missing model artifacts fail with a clear unavailable-arm record, not a silently substituted baseline.
- [ ] Run `python -m pytest tests/test_evidence_ledger.py -q`; expect pass. Run proposed CLI below; expect eight traces, no network calls and non-generation replay timing labels. Commit.

```bash
python scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --mode offline --output results/evidence_v2/offline_001
```

### Task 7: Paired evaluation and honest report

**Files:** Create `evaluation/evidence_aware/report.py`, `scripts/report_evidence_v2.py`, `tests/test_evidence_report.py`, `docs/v2/{annotation_protocol,preregistration,results}.md`.

**Interfaces:** Produce `score_answers(traces: list[RunTrace], references: dict) -> list[dict]`, `paired_cluster_summary(rows: list[dict], cluster_key: str, seed: int) -> dict`; evaluation is the only module allowed to load references.

- [ ] Write tests asserting errors remain denominators, repeat runs stay in clusters, no correct answers yields null cost-per-correct, oracle is excluded from deployable tables, and infeasible full-context has no accuracy value. Run focused tests; expect failure.
- [ ] Implement deterministic scoring, report provenance and clustered summaries; include annotation independence and pending preregistration fields as explicit incomplete work, not invented results.
- [ ] Run `python -m pytest tests/test_evidence_*.py -q`, then the existing suite with `python -m pytest -q`; expect passing checks and unchanged v1 artifact hashes. Run `python scripts/report_evidence_v2.py --results results/evidence_v2/offline_001`; expect labeled fixture report.
- [ ] Commit. Deliver offline artifacts first; seek the human labels and approved experiment budget before the live pilot. Document any unavailable verification without claiming completion.

## First session, completion and research gates

The first useful artifact is an eight-case offline fixture report showing required operands, retrieved spans, missing coverage, route decisions, numerical calculations, citations and abstentions. Aim for a 90–120 minute session completing the smallest tested slice; if the task list does not fit, ship its completed checkpoint and resume. Installing dependencies, downloading models or running the public benchmark is not implied by this handoff.

Engineering completion means strict contracts, offline behavior, v1 preservation, recorded failure paths, reproducible CLI/report and passing relevant tests. It does not require a favorable research outcome. Pilot completion adds independent annotations, approved measured runs, strong baselines and transparent uncertainty. A research success requires the preregistered quality/cost criterion on untouched data; failure to demonstrate it is a valid negative result.

Paper question: **Does audited quantity/entity/period coverage identify useful retrieval escalation under held-out companies and disclosure periods better than relevance-only or query-complexity routing, after matching answer models and resource budgets?** Ablate entity-only coverage, entity+period, full unit/metric coverage, citation audit, deterministic calculation, and model verification separately. Compare threshold policies across budgets; distinguish parser, retriever, gate and answerer errors. Test a separately sourced filing subset or company sector before claiming transfer.

Before proposing a submission, update related work, inspect released code, and ask whether the intervention adds knowledge beyond known completeness checking/routing. Novelty is unestablished. A credible negative result could show gate overhead erases savings, high-precision checks abstain too often, or strong hybrid retrieval eliminates the gap. Report it without inventing a new model-training phase to rescue the story.

Final deliverables: versioned data/split manifests; reviewer/adjudication records; configuration/environment hashes; runnable offline fixtures; measured baseline and policy traces when approved; separate online/indexing/judging cost tables; reproducible statistics; a short recorded or local demo; and a methods/results/limitations report. Resume wording must be reconciled with canonical evidence separately and use observed results, never proposed targets.

## Primary sources and reading order

All links were inspected read-only on October 17, 2026. Recheck revisions before execution; author-reported outcomes are not reproduced here.

1. [Beyond Vector Search source snapshot](https://github.com/sraghav12/beyond-vector-search/tree/675733109b30e80ce40c0a796bc0dd89e616c4ef). Read README, `pipelines/base.py`, vector and section pipelines, then evaluation runner. This is the actual extension baseline; distinguish published artifacts from historical data and newly proposed v2 files.
2. [When Learned Context Planning Fails to Beat Strong Retrieval](https://arxiv.org/html/2609.26976v1), September 22, 2026. Read experimental controls, held-out split and routing discussion. The authors find learned planning does not robustly beat strong retrieval in their bounded multiple-choice setting; oracle complementarity does not establish a deployable router. Motivation: rigorous controls, not a claim that their result transfers to financial QA.
3. [How to Build a Model Router in the Harness](https://www.langchain.com/blog/how-to-build-a-model-router-in-the-harness), October 1, 2026. Practitioner account linking domain-aware routing to traces and task outcomes. Borrow the evaluate-before-route discipline. Their coding-agent model-routing results are not evidence for this project's retrieval-routing gains.
4. [SEC: Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). Official access, identity and fair-access guidance. Read before any collection; record disclosure timing and durable accession identities rather than treating fiscal year or ticker as sufficient provenance.
5. [Elasticsearch BM25 similarity documentation](https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity) and [reciprocal-rank fusion documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion). Official implementation references for strong lexical/hybrid controls. Use their definitions to document local scoring and fusion choices; deploying Elasticsearch is unnecessary for this project.

## Copy-paste AI kickoff

> Implement the offline milestone in this standalone plan, one checked task at a time. First inspect the target checkout and compare its revision/interfaces with the observed commit. Use an isolated clone; preserve v1 artifacts and unrelated work. Keep network providers disabled, budget zero, and do not download models, train a router or purchase compute. Start with strict inference contracts and the eight synthetic fixtures; run the stated failing tests before minimal implementations and record actual passing evidence. Keep reference answers outside inference and use the specified quantity/unit/period provenance gate plus Decimal executor. Deliver the offline trace/report and a concise account of completed checks, unresolved human annotation and spending decisions. Do not claim improved accuracy, savings, novelty or independent validation from fixtures.
