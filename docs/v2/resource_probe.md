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

## Status in the frozen experiment

`dense`, `hybrid_rrf` and `hybrid_rrf_rerank` are **unavailable arms** in `data/release/v2/experiment_manifest.json`. The reason recorded is: no pinned local model installed, download not authorized. They are never replaced by BM25.

The adapters `HybridBackend` (RRF, `k=60`, ranks from 1) and `RerankBackend` exist and are tested with a deterministic test-only ranker. Enabling them requires all of the following:

1. Explicit user approval to download the pinned weights.
2. A recorded SHA-256 for each downloaded file.
3. A measured local index time and peak memory over the 125-filing pilot corpus.
4. A re-freeze of the experiment manifest. The manifest hash changes; the frozen primary comparison does not.
