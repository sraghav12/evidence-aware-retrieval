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
