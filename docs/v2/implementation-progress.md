# SDD ledger — plan: docs/superpowers/plans/2026-10-18-evidence-aware-retrieval.md

Baseline: 23/23 tests pass, HEAD 6757331.
Pre-flight 1→2→3: strict contracts feed dataset and source extraction, no conflict.
Pre-flight 3→4→5: source-derived spans and coverage feed executor and routing, no conflict.
Pre-flight 5→6→7: traces feed runner then reference-only report, no conflict.
Pre-flight 8→9→10: real-source pilot precedes experimental claims, conditional resources retained.
Ruling: use approved separate clone rather than linked worktree — existing checkout is dirty — cost if wrong: additional disk, no source mutation.
Ruling: install curated pinned compatibility dependencies in the isolated environment to run the existing 23-test baseline — no full legacy requirements or model weights — cost: about 111 packages rather than a minimal pytest-only environment. Core runtime remains stdlib-only.
Ruling: recover Apple Git clone ref initialization by explicitly checking out transferred origin/main — verified source revision intact — cost: none to original repository.
Task 1: complete (commits 6757331..d0e8463, tests: .venv/bin/python -m pytest tests/test_evidence_contracts.py -q → 14 passed in 0.01s)
Task 2: complete (commits d0e8463..d01e738, tests: .venv/bin/python -m pytest tests/test_evidence_dataset.py -q → 8 passed in 0.04s)
Task 3: complete (commits d01e738..41e6cf9, tests: .venv/bin/python -m pytest tests/test_evidence_coverage.py tests/test_evidence_parser.py -q → 13 passed in 0.02s)
Task 4: complete (commits 41e6cf9..13da553, tests: .venv/bin/python -m pytest tests/test_evidence_numeric.py -q → 8 passed in 0.02s)
Task 5: complete (commits 13da553..37ba97d, tests: .venv/bin/python -m pytest tests/test_evidence_policy.py tests/test_evidence_adapter.py -q → 9 passed in 0.02s)
Task 5: Ruling: source fixtures use 64 inspected cheap-stage whitespace tokens to force a controlled missing-company recovery; normal defaults remain 8192 — small fixture corpus otherwise fits entirely and cannot exercise escalation — cost: fixture route behavior is illustrative, not evidence of savings on real data.
Task 6: complete (commits 37ba97d..cee6be5, tests: .venv/bin/python -m pytest tests/test_evidence_ledger.py tests/test_evidence_inference_isolation.py -q → 10 passed in 0.09s)
Task 7: complete (commits cee6be5..c37d5c9, tests: .venv/bin/python -m pytest tests/test_evidence_adapter.py tests/test_evidence_contracts.py tests/test_evidence_coverage.py tests/test_evidence_dataset.py tests/test_evidence_inference_isolation.py tests/test_evidence_ledger.py tests/test_evidence_numeric.py tests/test_evidence_parser.py tests/test_evidence_policy.py tests/test_evidence_report.py -q → 71 passed in 0.26s)
Final review: fresh subagent whole-branch review of 6757331..c37d5c9 → 0 Critical, 8 Important, 15 Minor; ready "with fixes". Probes reproduced every Important finding.
Final: re-graded by effect: two minors promoted — cost_per_correct_usd reported 0.0 although compute is unpriced (reads as free), and baseline/handoff claimed 26 preserved v1 hashes when 24 are tracked.
Final: fixed self-referential supported-success scoring — test_supported_success_requires_reference_evidence / _requirements RED→GREEN.
Final: fixed header scope leaking across tables — test_header_scope_resets_between_tables RED→GREEN.
Final: fixed packing starvation of escalated evidence and added per-stage packed/omitted records — test_saturated_cheap_stage_does_not_block_escalated_evidence RED→GREEN.
Final: fixed restated values silently ignored — test_restated_value_conflicts_with_reported RED→GREEN.
Final: fixed post-cutoff units reaching retrieval/answerer, unaudited citations accepted, no post-generation deadline — test_retrieval_excludes_documents_after_cutoff, test_answer_audit_rejects_span_the_gate_did_not_audit, test_answer_after_deadline_abstains RED→GREEN.
Final: fixed report scoring unverified inputs (config/corpus hash, status, question set) — test_report_rejects_config_drift/_corpus_drift/_incomplete_run, test_report_requires_reference_for_every_question RED→GREEN.
Final: fixed failed rows losing partial history/usage; error rows now usage_complete=false — test_stage_exception_retains_partial_trace RED→GREEN.
Final: pinned previously untested checks (coverage cutoff, post-audit deadline, verification decrement, trace checksum, row count) — tests pass on current code; each verified by mutation (18/18 mutations killed).
Final: fixed cost_per_correct_usd now null while compute unpriced — test_unpriced_compute_has_null_cost_per_correct RED→GREEN. Corrected v1 count in docs/v2/baseline.md (24 tracked, 24/24 unchanged).
Final: Ruling: later stages exclude units already inspected for the same question (found on real KO data: expanded_search re-selected exactly the cheap-stage units) — escalation that re-reads identical units cannot add evidence; inspected units stay packable — cost if wrong: a deliberately re-ranked unit cannot be re-inspected in a later stage.
Final: Ruling: RetrievalBackend.retrieve gains optional exclude_unit_ids; BM25 index statistics stay corpus-wide while candidates are cutoff-filtered — one index serves all questions — cost if wrong: post-cutoff term statistics slightly influence ranking (never evidence).
Final: Ruling: a normalized table is contiguous pipe rows; any non-row or new header-like line ends header scope — matches source-table layout and closes the wrong-column path — cost if wrong: tables interrupted by notes abstain instead of extracting.
Final: Ruling: references may state `requirements`; supported success requires the reference requirements and/or reference evidence offsets to match, and a reference with neither cannot score supported — cost if wrong: unverifiable references undercount success.
Final: Ruling: two regression fixtures adjusted after RED (stub backend accepts the new keyword; starvation fixture keeps its table contiguous under the new header rule) — re-verified by mutation — cost: none observed.
Final: minor (deferred): contract enum/ID whitelists for metric, unit, basis, IDs, AnswerRecord.status and UsageEvent.stage.
Final: minor (deferred): gate_false_complete mislabels executor abstentions (zero-base growth).
Final: minor (deferred): paired summary mixes answerable and unanswerable rows.
Final: minor (deferred): cluster labels should come from the split manifest, not reference defaults.
Final: minor (deferred): committed data/release/v2/split_manifest.json is not in validate_manifest format.
Final: minor (deferred): budget_exhausted vs incomplete_evidence attribution when allowance is nearly spent.
Final: minor (deferred): no indexing usage event.
Final: minor (deferred): adapter labels structured specs as raw_question.
Final: minor (deferred): config_hash includes output path; absolute paths in run artifacts.
Final: minor (deferred): core engine imports evaluation ledger (layering).
Final: minor (deferred): canonical re-extraction scans the whole corpus on every audit.
Final: minor (deferred): dense multi-statement lines reduce readability.
Final: minor (deferred): evidence tests need tests/ on sys.path.
Final: minor (deferred): RetrievalBackend relies on undeclared selected/inspected_tokens attributes.
Task 8: Ruling: Python stdlib html.parser is the pinned HTML parser (Python 3.12.9) — keeps the offline core stdlib-only and runnable under -S — cost if wrong: ~30 s for 150 filings, slower than lxml.
Task 8: Ruling: inline-XBRL context is the authority for period, entity, unit and scale; visible period header, unit caption and row label must agree or the cell is rejected — conservative per spec — cost if wrong: 890/1484 candidates rejected on the v1 corpus, mainly missing captions and non-revenue labels.
Task 8: Ruling: raw HTML parsing lives in new pipelines/evidence_aware/html_source.py; units.py is unchanged and extraction.py only gains the 10-column row header — normalized documents reuse SECTION units — cost if wrong: none to interfaces.
Task 8: Ruling: questions are data/release/v2/real_dev_questions.jsonl (plan said .json) to reuse the runner's JSONL loader — cost: file name differs from plan.
Task 8: Ruling: fiscal calendar entries come only from each filing's own dei focus year — direct evidence, no inference of prior-year calendars — cost: comparative-only years (rd19 Coca-Cola FY2020) abstain.
Task 8: Ruling: references built from an independent raw ix-fact reader (no table/header/caption logic); Walmart, Eli Lilly, out-of-grammar and comparative-only cases are labeled answerable so system abstentions count as misses — cost if wrong: success rate understated.
Task 8: Ruling: full normalized documents, segments and failure rows stay untracked (regenerable from raw filings); manifest, 150-filing audit, questions, references and two synthetic layout fixtures are tracked — cost: reproduction needs the source checkout's raw HTML.
Task 8: Observation (not changed): queries do not include fiscal-year tokens, and three-company ranking (rd06) loses BM25 slots to one company — left visible rather than tuned on development outcomes; Task 9 strong retrieval controls are the place to test it.
Task 8: Observation: a trial run on these questions exposed cutoff-unfiltered retrieval and repeated escalation; both were fixed in the review fix pass (7693235) with synthetic regressions before the recorded run real_dev_001 at 4448255.
Task 8: complete (commits 7693235..8c05992, tests: .venv/bin/python -m pytest -q → 122 passed in 1.78s)
