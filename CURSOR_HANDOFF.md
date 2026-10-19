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

Fresh verification at the original handoff: 94 tests passed, including the 23 historical tests. All 24 tracked v1 release-file hashes unchanged (an earlier "26" counted two gitignored source-only files; see `docs/v2/baseline.md`). The original dirty checkout is untouched. No model/provider inference, training, model downloads or publishing occurred. Free Python package dependencies were installed only in this repository's environment.

The eight synthetic cases yielded three supported answers and five correct abstentions, no query errors. One ranking case recovers two missing Beta operands via section search. This is functional validation, not real-data accuracy, human validation or a savings result.

## Cursor session, October 18, 2026 evening

- **Review of Tasks 1–7 done.** A fresh reviewer read `6757331..c37d5c9`: 0 Critical, 8 Important, 15 Minor. All Important findings, plus two minors re-graded by effect, are fixed in `7693235`, each with a failing-first regression in `tests/test_evidence_review_regressions.py`. 18/18 mutations of the fixed or previously untested checks are caught. Deferred minors and rulings are in `docs/v2/implementation-progress.md`.
- **Task 8 done (`4448255`, docs after).** Stdlib inline-XBRL table extraction with lineage (`pipelines/evidence_aware/html_source.py`), `scripts/prepare_evidence_v2.py`, `configs/evidence_v2_real_dev.json`, 20 public questions over 10 companies, separate AI-authored unreviewed references, source manifest and a 150-filing extraction audit. Run `results/evidence_v2/real_dev_001` (ignored): 12/16 answerable supported and reference-verified, 4/4 correct abstentions, 0 errors, 0 provider calls. Failures and limitations: `docs/v2/extraction_audit.md`.
- Verification: 122 tests pass; 24/24 v1 hashes unchanged; report regenerates byte-identically; source checkout status unchanged.

## Exact next action

**Task 9**: strong controls (always-cheap, always-maximum, complexity rule; dense/RRF/reranker only after a resource probe, missing backends marked unavailable), locked-split and experiment manifests, frozen arms. Live provider runs stay disabled at `max_usd=0`. Task 8 itself has not had an independent review; include `7693235..HEAD` in the next whole-branch review. The unresolved three-company ranking miss (rd06) is the first thing the stronger retrieval arms should be tested against.

Do not redo Tasks 1–8 or create another repository. Inspect git status and the ledger first.

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
- Real SEC HTML is supported only for consolidated inline-XBRL revenue cells that pass header, caption and label cross-checks; everything else is rejected with a recorded reason.
- Runtime questions have exactly id/question/as_of; human/reference requirements never feed the raw-question path. Structured specs are diagnostic only.
- Human review count for v2 is zero. AI-authored references retain that label. V1's 43 questions and derivatives stay development-only.
- All numerical results require entity, metric, fiscal dates, units, basis, source hash, quote slice and eligible disclosure. Conflicts and unsupported calculations abstain.
- Keep v1 directories byte-identical. `docs/v2/v1_files_sha256.json` has the inventory. Do not silently add stronger retrieval backends under existing names; missing arms must be unavailable.
- Existing README describes v1 only. Do not present its model-judge scores as v2 numerical accuracy. Do not publish, push, merge or send outreach without user instruction.

## Local source and hardware for Task 8

Machine: Apple M4 Pro, 24 GiB. Default shell Python is 3.14; use `.venv/bin/python` (3.12.9).

Original source checkout is at `/Users/sragh/Downloads/GenAI/LLM_Research/beyond-vector-search`. It has 150 untracked raw HTML files under `data/raw/`, with frozen normalized metadata in `data/release/v1/corpus_150.jsonl.gz`. Raw files did not come through the new clone. All 150 match v1 metadata; the 50 pilot filings are copied and hashed in ignored `data/raw/evidence_v2/`. Do not copy credentials, `.env`, caches, old result directories or the source checkout's unrelated changes. Source has a modified cost report and untracked legacy results/builder; leave them intact.

## Workflow continuity

The requested workflow is Superpowers native execution: failing tests before implementation, minimal code, passing focused/full checks, local task commits and durable progress notes. No automatic confirmation between tasks. If the Superpowers installation is available in Cursor, use `executing-plans`; otherwise follow the same explicit plan/ledger checks without claiming a skill ran.

Persistent user task state lives in `/Users/sragh/NOW.md`, under `# QUEUE`; update only this Project 2 task as meaningful work completes. Prefer durable repository notes over relying on the chat. Do not change user profiles or invent prior history.
