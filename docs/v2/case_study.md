# Case study: checking for missing evidence before retrieving more

## The problem

Financial questions over SEC filings fail in specific ways:
- the right company but the wrong fiscal year;
- a number from a segment table instead of the consolidated statement;
- one of three companies silently missing;
- a figure the company later restated.

A retrieval system that ranks text by relevance has no way to know which of those happened. v1 of this project measured that gap with a model judge. v2 asks a narrower, checkable question:

> If the system knows exactly which numbers a question needs, can checking which of them are still missing decide when to retrieve more, and stop early without losing answers?

## What was built

1. **Parse into requirements.** A controlled grammar turns "What was Apple FY2024 revenue growth over FY2023?" into two requirements: Apple FY2024 and FY2023 consolidated reported revenue, in USD. Exact fiscal dates come only from filings disclosed by the question's cutoff. Unsupported wording abstains instead of guessing.
2. **Extract source cells from raw SEC HTML.** Each inline-XBRL revenue fact is accepted only if its context matches the visible column header, unit caption and row label. On the 150 v1 filings, 594 cells were accepted and 891 rejection records kept with reasons. Each accepted cell keeps its raw-HTML byte range and XBRL fact ID.
3. **Audit coverage.** For every requirement the gate checks entity, period, fiscal year, unit, disclosure cutoff, source hash and quote slice. Conflicting eligible values abstain.
4. **Escalate within budgets.** The stages are a cheap search, then a section search for the missing operands, then one expanded search. They run under token and deadline limits and never repeat inspected units.
5. **Compute or abstain.** Decimal arithmetic, every operand cited, otherwise a structured abstention.
6. **Evaluate fairly.** Every arm runs from one frozen manifest with matched gate, audit, limits and seeded paired order. The executor refuses to run if the code, corpus, questions or config drift from the freeze.

## Results (development pilot, descriptive)

111 questions over 25 companies, 1,554 paired runs, 0 provider calls ([full table](results.md)):

- **Evidence rule vs always running every stage:** identical scored outcomes on every question (58/77 supported, 33/34 correct abstentions), with 39% fewer inspected retrieval tokens and 44% fewer stages.
- **Cheaper fixed schedules lose answers:** 45/77 for always-cheap, 48/77 for an operand-count rule.
- **Pinned dense, hybrid RRF and cross-encoder reranking did not beat BM25** on these terse numeric table units (55, 57 and 56 vs 58). The reranker cost about 7× the median latency.

## What went wrong, and what that taught

- **A wrong answer from retrieval-bounded conflict checks.** For GE Aerospace FY2023 the evidence rule answered 67,954, the originally reported figure. The later 10-K restates it as 35,348, but BM25 never retrieved that cell, so the gate never saw the conflict. The dense arms happened to retrieve it and abstained. "No conflict found" is only as good as the retrieval behind it.
- **More retrieval can hurt an exact-value rule.** On development data, always-maximum lost an Eli Lilly answer because a later filing rounds 34,124.1 to 34,124. The inference gate still treats that as a conflict, though the references now compare at stated XBRL precision.
- **The locked test did not survive scrutiny.** A fresh review found the first split ignored the published v1 questions. Applying that rule collapsed the test to 2 informative groups, so the study was re-registered as development-only before any pilot run, rather than forcing a split.
- **Three-company questions are fragile under lexical ranking.** One company's tables can take every retrieval slot.

## Limits

- The references are AI-proposed and no human has reviewed them.
- There are 6 independent answerable groups and no held-out companies, so the intervals are descriptive.
- Supported scope is consolidated reported revenue for the controlled question forms.
- Token counts are whitespace estimates, and local compute is unpriced.
- No savings, noninferiority or generalization claim is made.

## Ownership and AI assistance

The project direction, scope decisions and approvals (repository, model download, publication) are the author's. Implementation, tests, reviews and documentation were produced with AI coding agents under that direction and checked by tests, mutation checks and two fresh code reviews. Before presenting it, the author should be able to walk through the parser, one source cell, one route, the strongest baseline and the failed hypothesis without notes. [interview_walkthrough.md](interview_walkthrough.md) is the script for that.
