# Project 2 follow-up: bounded conflict probe (Task 11) and held-out companies (Task 12)

The user chose these two follow-ups on October 18, 2026. Spec authority: [design](../specs/2026-10-18-evidence-aware-retrieval-design.md). Global constraints are unchanged:
- 0 provider calls and `max_usd=0`;
- v1 byte-identical;
- references never reach inference;
- AI-proposed references keep their label;
- no tuning on held-out outcomes.

## Task 11: gate v3, a bounded post-gate conflict probe (developed on development data only)

**Problem.** Conflicts are only detected among retrieved evidence. In `pilot_001`, GE Aerospace FY2023 was answered with the superseded 67,954 because the restating 10-K was never retrieved.

**Design.** When coverage is complete and before execution, the probe runs once:
- It searches **later eligible filings of each cited entity**: filings disclosed after the earliest cited filing and on or before `as_of`. Restatements appear as comparative columns in later 10-Ks.
- **Bounds:** at most `probe_units_per_filing` statement-like units per later filing and `probe_tokens` inspected tokens in total, charged as a separate `conflict_probe` usage stage against the retrieval and verification allowances.
- **If budget is lacking**, the probe is recorded as skipped and the answer proceeds, flagged as unprobed.
- **Re-audit:** coverage is re-audited over packed plus probe evidence. An incompatible value abstains with `conflicting_evidence`.

Gate v3 also compares values at the coarser *displayed* precision of the two cells. For example, 34,124.1 and 34,124 in USD millions agree at a precision of 1, mirroring the references' XBRL-precision rule. No contract change is needed, because the displayed value string carries the precision.

**Tests first.** Required regressions:
- the probe finds a restatement in a later filing;
- the probe never reads filings after `as_of` or other entities;
- its cost is bounded and charged;
- a skipped probe is labeled;
- precision-only differences are not conflicts;
- genuine differences still conflict;
- gate v2 behavior is unchanged when v3 is off.

**Development check.** Pilot development questions only; choose and freeze `probe_units_per_filing` and `probe_tokens` there.

## Task 12: held-out companies outside all development ancestry

**Companies.** 16 non-financial large caps not among the 30 v1 tickers. Also excluded: every company named in development questions, including the unknown-company rows (Microsoft, Netflix, Intel, Oracle, Nike, Tesla). The list is ADBE, CRM, CSCO, QCOM, TXN, PEP, MRK, ABT, TMO, HON, UPS, LOW, TGT, SBUX, LMT and IBM. Each contributes its three latest annual 10-Ks.

**Collection.**
- `scripts/collect_heldout_v2.py` is standard-library only.
- The declared `SEC_EDGAR_USER_AGENT` comes from the environment and is never written to files.
- Requests are rate-limited well under SEC's 10/s maximum and cached in ignored `data/raw/heldout_v2/`.
- The manifest records the accession, SEC URL, raw SHA-256 and bytes for each filing.

**Questions.** The same frozen pilot templates, with fixed company pairs within the held-out set. All held-out rows are a locked test. A validator asserts zero entity overlap with any development row.

**Freeze and run.** Freeze protocol v3 before running any held-out question:
- **Arms:** four scheduling policies with gate v3, a gate-ablation arm (evidence rule with gate v2), and hybrid RRF with gate v3, at 8,192 context.
- **Primary comparison:** the evidence rule vs always-maximum, both with gate v3.
- **Secondary comparison:** gate v3 vs gate v2 under the evidence rule (unsupported answers and supported success).

Run once and report paired cluster intervals. The intervals are confirmatory only if at least 12 independent groups exist; even then this is still a pilot interval with AI-proposed references.
