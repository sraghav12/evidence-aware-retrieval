# Cursor handoff: Project 2 only

Updated October 18, 2026 (America/New_York). This file is the continuation context. Read it before edits. The user requested this handoff so Cursor can continue the work.

## User intent and authorization

Build **Evidence-Aware Budgeted Retrieval**, the second project, as a v2 extension of **Beyond Vector Search**, aimed at **applied AI / ML engineer** interviews. Demonstrate real, inspectable skill through source lineage, retrieval, bounded decisions, evaluation, and reproducibility. Do not promise a job, novel research, or unobserved performance wins. Project 1 is outside scope.

The user approved the written design/plan and native sequential implementation with “go ahead.” They also authorized trying a different available answer model if one is unavailable. Keep one fixed model across compared arms and record any substitution. That authorization does not create a paid API budget. Do not request design approval again.

## Start here

- Repository: this folder, `beyond-vector-search`.
- Branch: `feat/evidence-aware-v2`; seven implementation commits after baseline.
- Baseline: `675733109b30e80ce40c0a796bc0dd89e616c4ef`.
- Latest implementation commit before this handoff: `c37d5c9`.
- [Approved design](docs/superpowers/specs/2026-10-18-evidence-aware-retrieval-design.md).
- [Ten-task implementation plan](docs/superpowers/plans/2026-10-18-evidence-aware-retrieval.md).
- [Original Project 2 brief](docs/superpowers/handoffs/original-project-2.md).
- [Shared original handoff](docs/superpowers/handoffs/original-ai-implementation-handoff.md).
- [Durable task ledger and rulings](docs/v2/implementation-progress.md).

## What already works

Tasks 1–7 are implemented and tested:

1. Strict question/spec/evidence contracts, hashes, isolated clone and frozen-v1 inventory.
2. Eight synthetic source fixtures; public questions separate from references; leakage-safe grouping; lazy legacy evaluation imports.
3. Source-unit BM25, controlled question parser, public cutoff-aware fiscal calendar, conservative operand coverage.
4. Decimal extraction/sum/growth/ranking, exact scale conversion, ties and operand citations.
5. Three-stage routing (cheap, section, expanded), explicit state history, final packing recheck and legacy adapter.
6. Zero-budget runner, retained failures, reservations, usage/source/environment manifests, immutable output directories.
7. Separate offline evaluation, reference/source audits, paired cluster bootstrap helpers and HTML/JSON reports.

Fresh verification immediately before handoff: **94 tests passed in 1.40 seconds**, including the 23 historical tests. **All 26 published v1 release-file hashes unchanged.** The original dirty checkout is untouched. No model/provider inference, training, model downloads or publishing occurred. Free Python package dependencies were installed only in this repository's environment.

The eight synthetic cases yielded three supported answers and five correct abstentions, no query errors. One ranking case recovers two missing Beta operands via section search. This is functional validation, not real-data accuracy, human validation or a savings result.

## Exact next action

**Fresh whole-branch review is pending.** Review the range `6757331..c37d5c9` against Tasks 1–7, with tests first. Fix material findings through failing regressions, then a passing full suite. This checkpoint is implemented/tested but has not had independent code review; do not describe it as fully reviewed or merged.

Pay particular attention to strict nested input validation; inference/evaluation separation; table/period entailment; cumulative verification work and packing; end-to-end deadlines; reservation/failure accounting; source/config/trace integrity checks in reports; and whether statistics preserve paired independent units. The existing passing tests do not prove these areas are exhaustive.

Then continue **Task 8**, which has only been read, not implemented: raw SEC HTML extraction, provenance mapping, and a real development pilot of 12–20 questions over at least four company groups where feasible. Keep failures/unsupported layouts visible. Then Tasks 9–10 add strong controls and evidence packaging, with all resource/annotation gates retained. No product files for Tasks 8–10 exist yet.

Do not redo Tasks 1–7 or create another repository. Inspect current git status and ledger first. There are no known uncommitted product-code changes at this checkpoint; handoff/documentation updates are committed separately.

## Run and inspect

Use the existing isolated Python 3.12.9 environment:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -S scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --output results/evidence_v2/cursor_smoke_001
.venv/bin/python -S scripts/report_evidence_v2.py --results results/evidence_v2/cursor_smoke_001
```

Choose a new output name if it already exists. `-S` proves the offline core works with the standard library. The historical adapter/tests have optional compatibility dependencies pinned in `requirements-evidence-v2-compat.lock`; do not install the broad legacy requirements file unnecessarily.

Existing ignored local artifacts:

- `results/evidence_v2/stdlib_001/report.html` — inspectable report with full traces.
- `results/evidence_v2/stdlib_001/report.json` and `traces.jsonl`.
- `results/evidence_v2/offline_001/` — first run; its older manifest predates explicit source hashes. Preserve it as historical, prefer `stdlib_001` for provenance.
- `.superpowers/sdd/2026-10-18-evidence-aware-retrieval/` — task briefs, RED test logs and live ledger; do not delete on handoff.

## Constraints and deliberate limits

- `provider_enabled=false`, `max_usd=0`. CLI live mode intentionally fails as unavailable without submitting a call. No funded provider adapter exists; injected test answerers are not live model experiments.
- Eight fixtures use a 64-whitespace-token cheap-stage cap to force one controlled recovery. The ordinary per-stage cap is 8192, final context 8192, output 512, cumulative retrieval/verification each 24576, deadline 30000 ms. Do not infer real savings from the fixture cap.
- Only controlled source-table text is supported so far. There is no real SEC HTML extractor yet.
- Runtime questions have exactly id/question/as_of; human/reference requirements never feed the raw-question path. Structured specs are diagnostic only.
- Human review count for v2 is zero. AI-authored references retain that label. V1's 43 questions and derivatives stay development-only.
- All numerical results require entity, metric, fiscal dates, units, basis, source hash, quote slice and eligible disclosure. Conflicts and unsupported calculations abstain.
- Keep v1 directories byte-identical. `docs/v2/v1_files_sha256.json` has the inventory. Do not silently add stronger retrieval backends under existing names; missing arms must be unavailable.
- Existing README describes v1 only. Do not present its model-judge scores as v2 numerical accuracy. Do not publish, push, merge or send outreach without user instruction.

## Local source and hardware for Task 8

Machine: Apple M4 Pro, 24 GiB. Default shell Python is 3.14; use `.venv/bin/python` (3.12.9).

Original source checkout is at `/Users/sragh/Downloads/GenAI/LLM_Research/beyond-vector-search`. It has 150 untracked raw HTML files under `data/raw/`, with frozen normalized metadata in `data/release/v1/corpus_150.jsonl.gz`. Raw files did not come through the new clone. Read/hash/copy only the required HTML into ignored new working data. Do not copy credentials, `.env`, caches, old result directories or the source checkout's unrelated changes. Source has a modified cost report and untracked legacy results/builder; leave them intact.

## Workflow continuity

The requested workflow is Superpowers native execution: failing tests before implementation, minimal code, passing focused/full checks, local task commits and durable progress notes. No automatic confirmation between tasks. If the Superpowers installation is available in Cursor, use `executing-plans`; otherwise follow the same explicit plan/ledger checks without claiming a skill ran.

Persistent user task state lives in `/Users/sragh/NOW.md`, under `# QUEUE`; update only this Project 2 task as meaningful work completes. Prefer durable repository notes over relying on the chat. Do not change user profiles or invent prior history.
