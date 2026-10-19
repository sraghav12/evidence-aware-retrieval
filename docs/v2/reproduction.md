# Reproducing Evidence-Aware Retrieval (v2)

Everything runs locally on CPU with no provider calls or API keys. Python 3.12 is the tested interpreter.

## 1. Offline check, standard library only (about 2 s)

Needs nothing beyond this repository:

```bash
python3 -S scripts/run_evidence_v2.py --config configs/evidence_v2_offline.json --output results/evidence_v2/my_smoke
python3 -S scripts/report_evidence_v2.py --results results/evidence_v2/my_smoke
```

Expected result: 8 synthetic questions, 3 supported answers, 5 correct abstentions, 0 errors. `results/evidence_v2/my_smoke/report.html` shows every route, requirement and citation. Use a new output directory each time; runs never overwrite.

## 2. Tests

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-evidence-v2-compat.lock
.venv/bin/python -m pytest -q
```

The suite includes the 23 historical v1 tests. Tests that need the pinned ONNX weights are skipped with an explicit reason when the weights are absent.

## 3. Real SEC filings (Release B, 20 development questions)

Raw HTML is not tracked. It is the 150-filing v1 corpus (`data/release/v1/corpus_150.jsonl.gz` metadata, files named `<doc_id>.html`). The prepare step checks each file's size, accession and CIK against the frozen metadata and records SHA-256 values in `data/release/v2/source_manifest.json`.

```bash
.venv/bin/python -S scripts/prepare_evidence_v2.py --config configs/evidence_v2_real_dev.json --source-raw-dir <dir with raw v1 HTML>
.venv/bin/python -S scripts/run_evidence_v2.py --config configs/evidence_v2_real_dev.json --output results/evidence_v2/<new_run>
.venv/bin/python -S scripts/report_evidence_v2.py --results results/evidence_v2/<new_run> --references data/release/v2/references/real_dev.jsonl
.venv/bin/python -S scripts/export_walkthrough_v2.py --results results/evidence_v2/<new_run>
```

Expected result: 12/16 answerable supported, 4/4 correct abstentions, 0 errors.

## 4. Release C pilot experiment (111 questions, 16 arms)

```bash
.venv/bin/python -S scripts/prepare_evidence_v2.py --config configs/evidence_v2_experiment.json --source-raw-dir <dir with raw v1 HTML>
.venv/bin/python -S scripts/draft_pilot_v2.py --config configs/evidence_v2_experiment.json --source-raw-dir <dir with raw v1 HTML>
.venv/bin/python -S scripts/freeze_experiment_v2.py --config configs/evidence_v2_experiment.json --dry-run
.venv/bin/python scripts/run_experiment_v2.py --config configs/evidence_v2_experiment.json --references data/release/v2/references/pilot.jsonl --output results/evidence_v2/<new_run>
```

How the steps check each other:
- **Draft:** regenerates byte-identical pilot files.
- **Freeze dry run:** must print the committed `manifest_sha256`.
- **Experiment run:** refuses to start if the corpus, questions, code, scripts, lock, config, run order or any arm's engine configuration differs from `data/release/v2/experiment_manifest.json`.

The dense, hybrid and rerank arms need the pinned ONNX models listed in `data/release/v2/model_assets.json`:
- `BAAI/bge-small-en-v1.5@5c38ec7`
- `cross-encoder/ms-marco-MiniLM-L6-v2@233902d`

Download only the listed files into `.cache/models/<repo>/<revision>/`; every SHA-256 is verified before loading. Budget about 10 minutes and about 2.5 GB of memory for the model arms on an Apple M4 Pro.

## What is and is not reproducible from the repository alone

| Item | From repository alone |
|---|---|
| Synthetic offline run and report | Yes |
| Test suite | Yes (model-dependent tests skip without weights) |
| Real-filing runs | Need the untracked raw SEC HTML |
| Pilot references | AI-proposed; human review count 0 |
| Saved run directories (`results/evidence_v2/`) | Ignored by git; regenerate as above. Portable excerpts are in `examples/evidence_v2/` |

## 5. Held-out companies (protocol v3, locked test)

Collection needs a real SEC User-Agent ("Name email") in the environment. It is sent only in request headers and never stored:

```bash
export SEC_EDGAR_USER_AGENT="Your Name you@example.org"
.venv/bin/python -S scripts/collect_heldout_v2.py --config configs/evidence_v2_heldout.json
.venv/bin/python -S scripts/prepare_evidence_v2.py --config configs/evidence_v2_heldout.json --source-raw-dir data/raw/heldout_v2 --filings-manifest data/release/v2/heldout_filings.json
.venv/bin/python -S scripts/draft_heldout_v2.py --config configs/evidence_v2_heldout.json
.venv/bin/python -S scripts/freeze_experiment_v2.py --config configs/evidence_v2_heldout.json --references data/release/v2/references/heldout.jsonl --split-manifest data/release/v2/heldout_split_manifest.json --output data/release/v2/heldout_experiment_manifest.json --dry-run
.venv/bin/python scripts/run_experiment_v2.py --config configs/evidence_v2_heldout.json --manifest data/release/v2/heldout_experiment_manifest.json --references data/release/v2/references/heldout.jsonl --output results/evidence_v2/<new_run>
```

Each collected filing's raw SHA-256 is recorded at download and re-checked during preparation. SEC may later amend or remove filings; the hashes show whether a re-collection matches. Re-running the experiment requires a fresh freeze, because the report code changed after `heldout_001` was run.
