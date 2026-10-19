# Resource probe for dense and reranking arms

Checked October 18, 2026. Metadata only: Hugging Face model API (revision, license, file sizes). **No weights were downloaded, no model was loaded, and no provider was called.**

## Local environment

| Item | Observation |
|---|---|
| Hardware | Apple M4 Pro, 24 GiB unified memory |
| Free disk | about 34 GiB |
| Interpreter | Python 3.12.9 project environment (`.venv`) |
| Installed and usable | `onnxruntime` 1.31.0, `tokenizers` 0.23.3, `huggingface_hub` 2.2.0, `numpy` |
| Not installed | `torch`, `transformers`, `sentence-transformers`, `faiss` |
| Not used | `chromadb` is installed for v1, but its default embedder downloads a model on first use |

ONNX Runtime plus `tokenizers` can run the candidates below on CPU without installing PyTorch.

## Candidates (pinned revisions)

| Role | Model | Revision | License | Weights |
|---|---|---|---|---|
| Dense bi-encoder (preferred) | `BAAI/bge-small-en-v1.5` | `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` | MIT | 133.1 MB ONNX (133.5 MB safetensors) |
| Dense bi-encoder (alternative) | `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Apache-2.0 | 90.4 MB ONNX |
| Cross-encoder reranker (preferred) | `cross-encoder/ms-marco-MiniLM-L6-v2` | `233902d25c440f23af6f7d6e94d2946bac0bee0a` | Apache-2.0 | 91.0 MB ONNX |
| Cross-encoder reranker (larger) | `BAAI/bge-reranker-base` | `2cfc18c9415c912f9d8155881c133215df768a70` | MIT | 1112.5 MB ONNX |

Author recommendation if downloads are approved: the preferred dense model and the preferred reranker, about 224 MB total, CPU-only. The larger reranker is ten times the size and is not needed for a feasibility study.

## Download (user-approved, October 18, 2026)

The user approved downloading the two preferred models. Only the files each pinned revision needs were fetched into ignored `.cache/models/`: the ONNX weights, tokenizer, configs and model card (225.6 MB). Per-file SHA-256 values are in `data/release/v2/model_assets.json`:

| Model | ONNX SHA-256 |
|---|---|
| bge-small-en-v1.5 | `828e1496d7fa…` |
| ms-marco-MiniLM-L6-v2 | `5d3e70fd0c9f…` |

`pipelines/evidence_aware/onnx_rankers.py` verifies every hash before loading. A missing or altered file leaves the arm unavailable. The module is imported only for model-backed arms, so the offline core and `python -S` runs never load ONNX Runtime.

Implementation details:
- **Dense:** CLS pooling, L2 normalization, the bge query instruction on queries only, truncation at 512 tokens.
- **Indexing:** units are embedded once, in sorted-ID batches. Embeddings are batch-invariant (maximum difference 0.0 in a check), so rankings do not depend on question order.
- **Reranker:** scores (question, unit) pairs over the first 60 hybrid candidates.

## Measured cost (20 Release B development questions, 50 filings, CPU)

| Run | Wall time | Process high-water memory |
|---|---|---|
| BM25 | 1.7 s | 270 MB |
| Dense indexing: 2,668 units, 1.37M tokens | 115 s | 2.3 GB |
| Full hybrid + rerank run | 139 s | — |

The 125-filing pilot corpus is about 2.5× larger, so Task 10 loads the rankers once and reuses one index across arms.

On terse numeric table text, bge-small separates poorly. For "What was Apple FY2024 revenue?" it scored a lease-maturity table (0.535) above the revenue table (0.504). On equivalent prose the revenue sentence clearly wins (0.776 vs 0.547). This is a qualitative observation the strategy track will measure, not a result.

## Status in the experiment

The adapters (`DenseBackend`, `HybridBackend` with RRF `k=60` and ranks from 1, `RerankBackend`) reuse BM25's units, cutoff, entity and section eligibility, and selection rule. With verified assets, all 16 arms are available. The manifest is re-frozen after the Tasks 8–9 review fixes and before any pilot run; the primary comparison is unchanged.
