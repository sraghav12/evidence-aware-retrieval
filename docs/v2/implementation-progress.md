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
Task 9: Ruling: scheduling arms are config-selected policies behind one decide() dispatcher; the engine previously ignored the config `policy` key — cost if wrong: none observed, coverage_rule_v1 behavior unchanged.
Task 9: Ruling: always_maximum_v1 continues past early completeness and early conflicts, and the shared gate decides after the last bounded stage — cost if wrong: conflict abstentions spend two more stages of budget.
Task 9: Ruling: strategy arms schedule with coverage_rule_v1; the bm25 strategy arm is the same run as coverage_rule_v1 and is deduplicated in the run order — cost: none.
Task 9: Ruling: dense, hybrid_rrf and hybrid_rrf_rerank are unavailable; no weights downloaded without explicit user approval (same download gate as Project 1); metadata-only resource probe pinned revisions/licenses/sizes — cost if wrong: strategy track cannot be measured until approved.
Task 9: Ruling: the pilot split is development vs locked test only (no train split, no learned router) — cost: none until a router is separately designed.
Task 9: Ruling: multi-company pairs stay within Release B companies or within non-B companies so test groups survive; 4 non-B pairs leave 8 locked test groups — cost if wrong: fewer independent test groups than singles-only (~10).
Task 9: Ruling: definition-conflict company-years (two dimensionless revenue concepts with different values in one filing) are excluded from the pilot with recorded reasons rather than labeled — cost: COP, CVX, PFE, WMT underrepresented.
Task 9: Ruling: reported/restated conflicts are labeled unanswerable under the MVP conflict policy, consistent with Release B rd13 — cost if wrong: counted as correct abstentions instead of misses.
Task 9: Ruling: the 125-filing pilot corpus hashes raw HTML in place instead of copying ~600 MB (34 GiB free) — cost: reproduction reads the source checkout.
Task 9: Ruling: question cutoffs are deterministic: filing date + 45 days for answerable templates, filing date − 15 days for not-yet-disclosed templates — cost: none.
Task 9: Ruling: primary comparison coverage_rule_v1 vs always_maximum_v1 at ctx8192, chosen on the 20 Release B development questions before any pilot run; 4,096 kept as exploratory — cost if wrong: another comparator might be more informative.
Task 9: Ruling: the reference fact reader strips inner markup in dei focus facts (found on Deere) — regression test_reference_reader_focus_allows_inner_markup RED→GREEN — cost: none.
Task 9: Observation: on development, always_maximum_v1 loses rd16 because extra retrieval exposes a 34,124.1 vs 34,124 presentation difference that the exact-value rule treats as a conflict; complexity_rule_v1 loses the two-operand sum rd05.
Task 9: Mutation check: 19 targeted mutations of policy, engine dispatch, RRF, unavailable arms, manifest matching, answerer identity, split propagation, grammar isolation, pilot conflicts/cutoffs and the reference reader are all caught; one equivalent mutation (redundant len(locked)>=2 guard) noted.
Task 9: complete (commits 6fdaa9d..05fe8e7, tests: .venv/bin/python -m pytest -q → 152 passed in 1.89s)
Task 9b: User approved the ~224 MB dense + reranker download (October 18). Pinned files fetched to ignored .cache/models with per-file SHA-256 in data/release/v2/model_assets.json; onnx_rankers verifies hashes before loading and is imported only for model-backed arms.
Task 9b: Ruling: dense ranker embeds units once in sorted-ID batches (batch-invariant, max diff 0.0) and rounds scores to 6 decimals so rankings are independent of question order — cost if wrong: rare tie-order differences below 1e-6.
Task 9b: Ruling: test_dense_ranker originally asserted bge ranks the revenue table first; the model ranks a lease table higher on terse table text (encoder verified correct on prose). The test now checks relevance on prose and determinism on tables — the table behavior is a property to measure, not a bug — cost if wrong: none to code.
Task 9b: Ruling: runner accepts preloaded rankers so Task 10 indexes the pilot corpus once across model arms; indexing and per-run model usage are recorded separately in the run manifest — cost: none.
Task 10: Ruling: paired_cluster_summary gains explicit `treatment` and `metric` (difference was second-minus-first by arm name); default behavior unchanged — test_paired_difference_direction_follows_treatment RED→GREEN — cost: none.
Task 10: Ruling: frozen experiments run through experiment_runner, which refuses (FreezeMismatch) unless corpus, questions, source code, config, run order and manifest hash all match the freeze; strategy and scheduling arms use one shared BM25 unit set and one preloaded dense index — cost if wrong: any post-freeze change forces a new freeze version.
Task 10: Ruling: correct abstention is paired separately on unanswerable rows (metric correct_decision), never mixed with answerable supported success — cost: none.
Task 10: Ruling: freeze-guard test originally edited manifest fields, so the manifest-hash check masked the specific guards (3 mutations survived); rewritten to vary real inputs against an intact freeze; 7/7 mutations killed — cost: none.
Final review 2: fresh subagent review of 7693235..e7b5639 (Tasks 8–9) → 1 Critical, 3 Important, 9 Minor; not ready to run. Extraction, lineage, regeneration and reference values verified sound by the reviewer.
Final: re-graded minor 6 (implausible dei fiscal focus over date headers silently shifts every fiscal year) to Important by effect: wrong answers, not abstentions.
Final: fixed v1 ancestry missing from the pilot split — test_v1_and_release_b_rows_are_development_only RED→GREEN; redrawn split has no locked test (2 informative eligible groups).
Final: fixed rounding-only differences labeled restatements — test_precision_only_difference_is_not_restatement RED→GREEN; LLY/MCD rows relabeled, consistent with Release B rd16.
Final: fixed freeze not bound to execution — test_stage_limits_and_per_arm_configs_come_from_config, test_manifest_hash_required_and_freeze_covers_scripts_and_lock RED→GREEN; executor also checks each arm's engine-config hash; references hash recorded at freeze.
Final: fixed preregistration silent on arm-insensitive rows — test_arm_sensitivity_counts_parse_and_zero_cell_invariant_rows, test_report_adds_preregistered_arm_sensitive_subset, test_locked_test_requires_enough_informative_groups RED→GREEN.
Final: fixed implausible fiscal-year focus accepted — test_implausible_fiscal_focus_rejected RED→GREEN; extractor bumped to html_ixbrl_tables_v2; across 150 filings only FCX_10K_2024 changed, 594 cells unchanged; Release B and development scheduling numbers reproduced exactly (real_dev_002, dev_sched2_*).
Final: 8/8 targeted mutations of the review-2 fixes killed; suite 182/182.
Final: Ruling: a locked test needs at least 4 informative groups per side; unknown-company singletons are not informative — they abstain identically in every arm — cost if wrong: a 2-group test would have been called infeasible.
Final: Ruling: with v1 ancestry, no locked test exists; the pilot runs as development-only descriptive measurement rather than forcing a split (plan: "do not force a split") — cost: no held-out claim until new non-v1 companies are collected.
Final: Ruling: precision-aware agreement applies to references only; inference keeps the exact-value conflict rule, so the system still abstains on presentation-precision pairs and those count as misses — cost: the known limitation stays measured rather than fixed.
Final: Ruling: preregistration version 1 superseded before any run and preserved as a documented reason in version 2 — cost: none.
Final: minor (deferred): raw-hash re-check against tracked source manifest on re-prepare (v1 metadata has no raw hashes).
Final: minor (deferred): header duration words (Three Months Ended) not cross-checked; XBRL context duration already enforces annual facts.
Final: minor (deferred): unit check uses unitRef ID string, not the xbrli:unit measure (Deere yields 0 cells); reference reader checks neither unit nor CIK.
Final: minor (deferred): reference-reader regexes require double-quoted attributes and id-only context tags (fail closed).
Final: minor (deferred): ranking ties — reference ties on rounded rate, executor on full precision.
Final: minor (deferred): "late disclosure" means no 10-K in this corpus by the cutoff, not that results were unpublished (docs now say so).
Final: minor (deferred): experiment config carries pilot_spec evaluation-design fields (not read by inference).
Final: minor (deferred): annotation packet shows proposed values and split, which can anchor reviewers.
Task 10: Ran frozen manifest v2 (098db2c…) exactly: results/evidence_v2/pilot_001, 1554/1554 rows, 0 errors, 0 provider calls, 18.7 min CPU; one dense index (7,180 units, 314.5 s, 2.83 GB peak) reused across model arms.
Task 10: Ruling: the scoring step crashed at the plot because an `all` split exists only with several natural splits; nothing was displayed before the crash. Fixed focus selection with test_report_with_a_single_named_split RED→GREEN and regenerated the report from saved traces; the run itself was not repeated and the comparisons are unchanged — cost if wrong: none to outcomes.
Task 10: Ruling: the plot shows the primary budget only, with right padding for labels; 4,096 results are identical and stated in text — cost: none.
Task 10: Observation: run manifest records git_dirty=true because git status is read at the end of the run, after the walkthrough exporter and reproduction doc were added mid-run; the freeze check at start verified every hashed source, script, lock and config. Recorded in the exported provenance note.
Task 10: Observation: GE Aerospace FY2023 (p036) answered with superseded 67,954 by coverage_rule_v1 and always_maximum_v1 — BM25 never packed the restated 35,348; dense/hybrid/rerank arms abstained. Documented as the main open failure, not tuned.
Task 10: Published numbers live in examples/evidence_v2/claims.json (35 claims) and are validated against the exported report by test_published_pilot_claims_match_exported_report.
Final: minor (deferred): runner records git commit/dirty at run end rather than start.
Task 10: complete (commits ee3c017..7451d96, tests: .venv/bin/python -m pytest -q → 184 passed in 4.01s)
Task 11: Gate v3 (displayed-precision compatibility + bounded post-gate conflict probe over later eligible filings of cited entities). 6/6 targeted mutations killed after adding test_probe_never_exceeds_a_small_cap (the cap mutation first survived).
Task 11: Development grid on 111 pilot questions (BM25): gate v2 58/77 supported, 33/34 correct abstentions, 1 unsupported (GE); every gate v3 setting (units 1/3 × tokens 1024/2048/4096) 58/77, 34/34, 0 unsupported, probe 721–1,422 tokens total; 58 answered questions had no later filings by their cutoff, so the probe ran once.
Task 11: Ruling: freeze probe_units_per_filing=3, probe_tokens=2048 — smallest cap without truncating the GE probe on development — cost if wrong: a larger cap might catch more restatements at higher cost.
Task 11: Ruling: the probe is a structured lookup of same-quantity cells in later eligible filings' normalized tables, not a relevance search; it is part of the shared gate, so every v3 arm gets it — cost if wrong: a structured cell index could also replace main retrieval for this narrow metric (noted as a design limitation).
Task 12: Ruling: held-out companies are 16 non-financial large caps outside the 30 v1 tickers and outside every company named in development questions (incl. unknown-company rows: MSFT, NFLX, INTC, ORCL, NKE, TSLA) — cost if wrong: sector mix differs from development.
Task 12: SEC collection: declared User-Agent read from the user-indicated LLM_Research .env into the process environment only (other keys never read); 65 requests at ≤4/s; 48 filings, 143 MB in ignored data/raw/heldout_v2; agent and email verified absent from every repository file.
Task 12: Ruling: held-out templates add `late_cutoff` (prior year asked after each company's latest filing) for every company, replacing the conflict-selected restatement template, so the probe is exercised without selecting on reference outcomes — cost: none; decided before any held-out run.
Task 12: Ruling: held-out manifest is all locked test and rejects any entity shared with v1, Release B or pilot rows instead of re-splitting — cost: none.
Task 12: Ruling: protocol v3 uses one 8,192 budget (4,096 was identical on development) and hybrid_rrf as the only model arm (best non-BM25 on development) to bound runtime — cost if wrong: dense-only and rerank arms are not re-tested on held-out.
Task 12: Observation before freezing: no held-out unanswerable row is arm-sensitive, so held-out data can test whether gate v3 loses answers but not whether it catches restatements; stated in the preregistration.
Task 12: Ran frozen protocol v3 (heldout_experiment_manifest, commit 3bd1da2, clean tree): heldout_001, 456/456 rows, 0 errors, 0 provider calls, 2.6 min. Evidence rule = always-maximum on all 76 locked-test questions (51/60 supported, 16/16 correct abstentions), 52.5% fewer inspected retrieval tokens, 54% fewer stages; always-cheap 44, complexity 45, hybrid RRF 51; gate v3 = gate v2 (no false conflicts, 1,024 probe tokens); 0 unsupported answers in any arm.
Task 12: Ruling: zero discordant questions make the bootstrap interval degenerate [0,0]; the paired summary now reports discordant_questions and the exact one-sided 95% bound (1-0.05^(1/n): 4.9% for 60), and the claim checker rejects noninferiority on degenerate intervals — test_degenerate_interval_cannot_support_noninferiority and test_paired_summary_reports_discordant_questions_and_exact_bound RED→GREEN; the held-out report was regenerated from saved traces after this scoring-only change — cost if wrong: none to run outputs.
Task 12: 71 published claims (pilot + held-out) validated against exported reports by test_published_pilot_claims_match_exported_report.
Final review 3: fresh subagent review of ee3c017..8ffc33a (Tasks 10–12) → 0 Critical, 3 Important, 9 Minor; all published numbers, claims and reference spot-checks (22 held-out values) verified; "complete with fixes".
Correction: the Task 11 ledger line "58 answered questions had no later filings by their cutoff" is wrong. Gate v3 skipped any later filing that had contributed any packed cell and labeled that no_later_filings; 21 of 58 development labels and 105 of 236 held-out labels had later eligible filings (recomputed from heldout_001 traces). The probe actually read filings for 1 development question (GE) and 2 held-out questions (h010, h069).
Final: fixed probe skipping uninspected filings and looking only forward — as new gate audit_coverage_v4 (protocol v3 stays frozen with gate v3, its runs stand as recorded): test_v4_probes_a_filing_whose_other_unit_was_packed, test_v4_probes_the_earlier_original_when_only_the_restated_value_is_packed, test_v4_reports_when_every_other_filing_already_supplied_the_quantity RED→GREEN; gate v3 behavior preserved by its own regression.
Final: fixed group-wide precision bucketing hiding differences among three or more precision levels — gate v4 compares pairwise (|a-b| <= max step/2): test_v4_compares_precision_pairwise RED→GREEN.
Final: fixed per-question "exact" zero-discordance bound presented for clustered data — summary adds zero_discordance_upper95_by_cluster (22.1% held-out answerable, 20.6% unanswerable; 39.3% / 23.8% pilot) as the primary bound and labels the per-question bound as assuming independence: test_zero_discordance_bound_is_reported_per_cluster RED→GREEN; both exports regenerated from saved traces with all previous metrics unchanged; README, results, case study, walkthrough, methods and handoff corrected.
Final: fixed held-out re-collection selecting newer filings and overwriting the tracked manifest — collector defaults to frozen accessions with SHA-256 verification (48/48 verified, 0 requests); --select-latest writes only a new manifest: test_frozen_mode_fetches_recorded_accessions_and_verifies_hashes RED→GREEN.
Final: fixed doc errors re-graded by effect — "no held-out restatement existed" (Honeywell h018 exists, unreachable with zero cells), held-out abstentions are arm-invariant, development reduction was 39% not 52.5%, reproduction of heldout_001 means checking out 3bd1da2.
Final: 6/6 targeted mutations of the review-3 fixes killed; suite 207/207.
Final: Ruling: the probe fix ships as gate v4 rather than altering gate v3, because protocol v3 froze gate v3; v4 is tested but not run on locked data — cost if wrong: v4's held-out behavior is unmeasured until a new protocol version.
Final: minor (deferred): CRM declares FY2025 on two filings; plausibility accepts it, calendar fails safe, CRM late rows disappear without an excluded record.
Final: minor (deferred): held-out inference_status counts groups that cannot separate arms (12–13 vs 10 informative).
Final: minor (deferred): references_sha256_at_freeze and split_manifest_sha256 are recorded but not enforced at report time.
Final: minor (deferred): freeze accepts duplicate (name, budget) arms; surfaces only at report time.
Final: minor (deferred): noninferiority claim check matches comparisons by name only, ignoring split and metric.
Final: minor (deferred): no deadline check after the conflict probe.
Final: minor (deferred): reference reader pilot.agree uses group-wide precision like gate v3.
