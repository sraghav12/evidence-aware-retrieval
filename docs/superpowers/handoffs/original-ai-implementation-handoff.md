# Three AI/ML Projects: AI Implementation Handoff

Prepared October 17, 2026. This package is a set of implementation instructions, not a claim that the projects or proposed commands already exist.

## What to give the AI model

For one project, attach its individual Markdown file and paste the kickoff prompt at its end. Each project file contains its own design, implementation plan, sources, checks, and first-session deliverable; prior conversation and the other files are not required.

For all three, attach `ALL-PROJECTS.md` and paste the coordinator prompt below. The combined file embeds these instructions and all three handoffs. The ZIP is a convenience copy of the same Markdown files.

| File | Project | Main skill evidence | First useful output |
|---|---|---|---|
| [01-correction-aware-memory.md](01-correction-aware-memory.md) | A small model that remembers corrections | Structured prediction, LoRA fine-tuning, memory evaluation | Offline correction trajectories, a deterministic updater, and a diagnostic report |
| [02-evidence-aware-retrieval.md](02-evidence-aware-retrieval.md) | Retrieval that escalates when evidence is incomplete | Retrieval engineering, budgeted routing, evaluation | An offline coverage gate and reproducible routing traces |
| [03-reproducible-llm-serving.md](03-reproducible-llm-serving.md) | Serving reliability across cache and precision settings | Inference systems, profiling, controlled experiments | A replay harness with mocked tools and explicit experiment manifests |

## Why these three belong together

The overall goal is to strengthen an early-career AI/ML portfolio with inspectable engineering and experiments that could later support a paper. The existing background includes deployed computer vision, cloud data pipelines, RAG, and PyTorch transformer work. The new projects add three distinct questions:

1. **Memory:** Can a small trained model maintain correct facts when information changes?
2. **Retrieval:** Can an evidence-based policy spend extra compute only where it improves the answer?
3. **Serving:** Can we understand and reduce behavior changes caused by serving state and numerical precision?

Keep them as three independent projects. Do not turn the first release into one giant agent platform, shared SDK, Kubernetes deployment, or universal evaluation product. A later integration demo can reuse immutable outputs once each project works on its own.

## Sequence and work allocation

The user selected all three projects. The sequence below is an author-selected execution default, not a new requirement to pick only one.

- **First:** get an offline smoke experiment working in all three repositories. This checks that each problem is measurable without a paid service or GPU.
- **First portfolio release:** prioritize the retrieval extension because it reuses an existing public project.
- **Next:** complete memory baseline and fine-tuning experiments once the evaluation is trustworthy.
- **In parallel where practical:** develop the serving harness and run local experiments. Schedule large-model training and GPU serving experiments so they do not compete for the same machine.

Assume 8–10 hours per week **total across the three**, until the user says otherwise. Earlier 2–6 week estimates described one project at a time; do not add three simultaneous promises to that schedule. Track person-hours and compute time separately, and revise the schedule after the first offline milestones. A first release and a paper submission are separate milestones.

GPU access is unconfirmed. The working hardware assumption is a Mac with an M4 Pro and 24 GB unified memory; inspect the actual host before choosing settings. Offline data, mock engines, replay evaluation, and documentation can proceed without model weights. Run a short resource probe before training or a full benchmark. macOS/Metal results are not evidence for Linux/CUDA behavior.

## Workspace ownership

Use separate repositories or isolated checkouts:

```text
chosen-workspace/
  correction-aware-memory/
  beyond-vector-search/        # independent clone/checkout, preserve original v1
  reproducible-llm-serving/
```

The user or AI may choose the parent directory. Repository names inside each plan are defaults. If an existing repository already serves the same project, inspect its instructions, status, and structure before adding files. Never reset or overwrite uncommitted work. Do not create project code inside a job-application repository just because the Markdown handoffs were saved there.

Multiple AI workers should each own one repository. They may exchange source links, config hashes, and finished reports; they should not concurrently edit shared files or launch competing model servers. Separate project artifacts and experiment IDs even when the same model is used. Cross-project integration is a stretch task.

## Common evidence standard

Each project plan defines its own schema and tests. Across all projects:

- Record the git commit, dependency lock, model/tokenizer revision, dataset and prompt hashes, backend, hardware, seeds, and exact runtime options.
- Preserve raw outputs, failed attempts, exclusions, and analysis scripts. Publish an offline report path that does not make model calls.
- Separate smoke fixtures, development examples, and locked test data. Never train on test cases or use gold answers to decide an inference-time action.
- Use simple baselines and ablations that isolate the proposed mechanism. Keep format enforcement and answer-model choices comparable.
- Treat synthetic labels and model-judge scores as such. An AI cannot certify that an independent human reviewed its own generated labels.
- State metric denominators and failure policies. Report uncertainty at the independent unit—trajectory, company/document group, or experiment session—rather than treating correlated turns as independent examples.
- Distinguish requested improvements from observed results. Functional correctness and reproducibility are required; beating a baseline is an experimental outcome. A well-supported null result is valid.
- Resume claims come only after evidence exists. Do not write target numbers as achieved results, call a preprint accepted, or claim a novel method before checking related work.

Use read-only source retrieval and freely available local tools by default. Paid API/cloud budgets start at zero. When more resources become necessary, prepare the exact run, estimated usage and lower-cost fallback before asking for a budget. No publishing, recruiter/faculty messages, or external account changes are part of these handoffs.

## Source and research policy

The individual handoffs link primary papers and official implementation documentation with reading order and purpose. Read methods and limitations, not just abstracts. Source access is not a successful reproduction, and author-reported results are not verified results from this project. Check current code and model licenses before copying or redistributing artifacts.

Some sources are preprints; identify their status from the current source. An unavailable author repository should produce an explicit reproduction limitation, not a fake implementation claim. It does not prevent an independently specified MVP.

Reddit, X and YouTube informed the initial project selection. They are not dependencies or technical specifications; follow the primary sources in the project files when implementing.

## From project to paper

For each project, finish these gates in order:

1. Reproduce or carefully characterize a baseline with pinned settings.
2. Identify a failure pattern and compare it with existing related work.
3. Freeze a falsifiable hypothesis, evaluation split, primary metric, and analysis plan.
4. Implement one intervention; test the relevant ablations and external/generalization condition.
5. Release reproducible artifacts and write methods, results, uncertainty, and limitations.
6. Evaluate an appropriate workshop, reproducibility track, or other venue after results and novelty checks. Verify actual deadlines and submission rules then.

We do not yet have three novel contributions or guaranteed publishable results. The portfolio engineering should remain useful even if a paper hypothesis fails.

## Coordinator kickoff prompt

```text
I want to implement all three projects described in the attached Markdown.
Treat each individual handoff as a self-contained design and task plan.
Start doing the work; do not replace it with another broad research or planning phase.

First inspect this workspace, its instructions, available tools, and hardware.
Create or reuse isolated project repositories without overwriting existing work.
Record any necessary deviations from the proposed paths/interfaces before edits.

Complete the first offline milestone in each project. If parallel workers are
available, give each one exclusive ownership of a separate project repository;
otherwise do those milestones sequentially. Prioritize the retrieval project's
first portfolio release after all three smoke experiments are in place.

Use the proposed defaults where information is missing. No paid API or cloud
budget is approved; do not let unavailable paid services or GPUs block offline
implementation. When a resource is needed for the next real experiment, show
the exact planned run and cost estimate while continuing independent work.

Follow the project-specific tests and acceptance criteria. Preserve v1 results,
raw outputs, provenance and locked evaluation splits. Do not invent experiment
results, independent human validation, performance wins, novelty, or publication.

For each milestone, report changed files, checks actually run and their outputs,
artifact paths, scientific limitations, and the next concrete task. Finish with
an honest per-project status: implemented, tested, experimentally evaluated,
or waiting for a specific resource. Keep those statuses distinct.
```

## Delivery checklist

- [ ] The receiving model can explain the project's goal and non-goals.
- [ ] It knows its repository, first task, inputs, outputs, and verification command.
- [ ] It can start offline without reading another conversation.
- [ ] It knows which requirements are functional checks and which are research hypotheses.
- [ ] It knows how to handle missing compute, unavailable paper code, and null results.

The project-specific commands are a proposed interface for the future implementer. They have not been executed as part of creating this package.
