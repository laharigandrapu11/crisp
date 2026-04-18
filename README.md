# CRISP

**C**ompression · **R**ecognition · **I**ntelligence · **S**ignal · **P**ipeline

A two-stage neural document pipeline: noisy scanned document image -> CNN-powered OCR -> adaptive Huffman compression -> losslessly recovered text. Both stages run as independent FastAPI microservices wired together by a thin integration layer and a live React/D3 frontend.

**Live demo:** [frontend-xnnzv4dy6q-uc.a.run.app](https://frontend-xnnzv4dy6q-uc.a.run.app/) (deployed on Google Cloud Run; expect a few seconds of cold-start delay on the first request).

> **20 / 20 lossless** on the benchmark set, **mean compression ratio 1.88x**, and **mean end-to-end latency 181 ms** per page. See [End-to-end benchmarks](#end-to-end-benchmarks) for the full numbers from [`docs/metrics.json`](docs/metrics.json).

---

## Architecture

```
Document image (base64 PNG)
          │
          ▼
┌─────────────────────────────────────┐
│  Stage 1 - OCR          port 8000   │
│                                     │
│  1. Denoising Autoencoder           │  Removes noise, folds, stains
│           │                         │
│           ▼                         │
│  2. Classical Segmentation          │  Otsu → projection → blobs
│           │                         │
│           ▼                         │
│  3. Recognition CNN (EMNIST)        │  47-class character classifier
└─────────────────┬───────────────────┘
                  │  extracted_text
                  ▼
┌─────────────────────────────────────┐
│  Stage 2 - Adaptive Huffman         │
│                          port 8001  │
│                                     │
│  Vitter Algorithm V Encoder         │  Single-pass, no dictionary
│           │                         │
│     ┌─────┴──────┐                  │
│     ▼            ▼                  │
│  6 Metrics   Tree + Code Map        │  For benchmarks / frontend
└──────┬──────────────────────────────┘
       │  payload_base64 + metrics + tree
       ▼
┌─────────────────────────────────────┐
│  Frontend / Client                  │
│                                     │
│  D3 adaptive tree animation         │  Consumes /compress/steps
│  POST /decompress → recovered_text  │  Lossless round-trip check
└─────────────────────────────────────┘
```

| | Stage 1 | Stage 2 |
|---|---|---|
| **Service** | `stage1_ocr/` | `stage2_huffman/` |
| **Port** | `:8000` | `:8001` |
| **Core model** | Denoising AE + EMNIST CNN | Vitter Algorithm V (from scratch) |
| **Input** | `image_base64` (PNG) | `text` (UTF-8) |
| **Output** | `extracted_text`, `denoised_image`, `character_data` | `payload_base64`, 6 metrics, `code_map`, `tree_structure` |
| **Mean latency** | 111 ms | 38 ms compress / 32 ms decompress |

The two services share **nothing** at runtime. They communicate over HTTP using the contracts in [`docs/CONTRACTS.md`](docs/CONTRACTS.md). Either stage can be redeployed, scaled, or swapped out independently.

---

## Quick start

```bash
git clone https://github.com/<your-org>/crisp.git
cd crisp

python -m venv .venv && source .venv/bin/activate
pip install -r stage1_ocr/requirements.txt
pip install -r stage2_huffman/requirements.txt

cd stage1_ocr && uvicorn main:app --port 8000 &
cd .. && cd stage2_huffman && uvicorn huffman.service.main:app --port 8001 &
cd ..

python frontend/server.py
```

Exercise the whole pipeline with one curl chain:

```bash
IMG=$(base64 -i path/to/page.png)

TEXT=$(curl -s -X POST http://localhost:8000/ocr \
  -H 'content-type: application/json' \
  -d "{\"image_base64\": \"$IMG\"}" | jq -r .extracted_text)

curl -s -X POST http://localhost:8001/compress \
  -H 'content-type: application/json' \
  -d "{\"text\": $(jq -Rs . <<<"$TEXT")}" | jq '.metrics'
```

Or run the full benchmark in one shot:

```bash
python -m integration.benchmark    # writes docs/metrics.json
```

---

## Repository layout

```
crisp/
├── stage1_ocr/         # CNN OCR microservice (FastAPI :8000)
├── stage2_huffman/     # Adaptive Huffman microservice (FastAPI :8001)
├── integration/        # End-to-end pipeline driver + benchmark harness
├── frontend/           # Static React/D3 UI + tiny Python static server
├── docs/               # API contracts, deployment notes, benchmark results
│   ├── CONTRACTS.md
│   ├── DEPLOYMENT.md
│   └── metrics.json
├── tests/              # Benchmark image fixtures (tests/benchmark_images/)
├── deploy.sh
└── README.md
```

---

## End-to-end benchmarks

All numbers below come straight from [`docs/metrics.json`](docs/metrics.json), produced by `python integration/benchmark.py` over a 20-image set spanning clean scans and noisy / folded / stained variants.

> **Hardware:** benchmarked locally on an **Apple M4 (CPU-only, 16 GB RAM, macOS 15)**. The hosted [Cloud Run demo](https://frontend-xnnzv4dy6q-uc.a.run.app/) runs on smaller shared instances (2 vCPU / 2 GB per service) and will be noticeably slower per request, especially on cold starts.

| Metric | Value |
| --- | --- |
| Images run | **20** |
| Lossless pass rate | **100 %** (20 / 20) |
| Mean total latency | **181 ms** (min 127 ms, max 320 ms) |
| Mean Stage 1 latency (OCR) | 111 ms |
| Mean compress latency | 38 ms |
| Mean decompress latency | 32 ms |
| Mean compression ratio | **1.88x** |
| Mean entropy | 3.83 bits / symbol |
| Mean encoding efficiency | **0.897** |
| Best ratio in dataset | **2.22x** on `FontLre_Clean_VA.png` |

Compression ratio is computed on the **raw** compressed bytes (not the base64 envelope), in line with the hackathon rubric. Encoding efficiency = entropy / avg_bits_per_symbol, clamped to [0, 1]. Values near 1.0 mean the adaptive code is operating within a fraction of a bit of the Shannon limit.

---

## Hackathon rubric coverage

| Rubric requirement | Where it lives | Notes |
| --- | --- | --- |
| CNN-based OCR | [`stage1_ocr/`](stage1_ocr/README.md) | Denoising autoencoder + EMNIST `balanced` CNN (47 classes), Optuna-tuned |
| Adaptive Huffman from scratch | [`stage2_huffman/`](stage2_huffman/README.md) | Vitter Algorithm V, no `zlib`, `gzip`, `bz2`, or `lzma` |
| Microservice architecture | `stage1_ocr/`, `stage2_huffman/` | Two independent FastAPI services on `:8000` and `:8001` |
| All 6 graduate-tier metrics | `/compress` response | `original_bytes`, `compressed_bytes`, `compression_ratio`, `entropy`, `avg_bits_per_symbol`, `encoding_efficiency` |
| Lossless guarantee | [`docs/metrics.json`](docs/metrics.json) | 20 / 20 (`lossless_pass_rate: 1.0`) |
| Frontend visualization | [`frontend/`](frontend/) | Live adaptive tree + animated swap highlights via `/compress/steps` |
| Inter-service contracts | [`docs/CONTRACTS.md`](docs/CONTRACTS.md) | JSON over HTTP, base64-encoded binary payloads |
| Deployment story | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), `Dockerfile`s | Both stages containerized; `deploy.sh` drives a full stand-up |

---

## Stage details

### Stage 1 - OCR pipeline

A FastAPI service that exposes a single `POST /ocr` endpoint and chains three steps internally: a small convolutional **denoising autoencoder** (trained on NoisyOffice), a classical **segmentation** step (Otsu binarization, horizontal projection, adaptive word-gap, connected components, wide-blob splitting), and a **recognition CNN** trained on EMNIST `balanced` with Optuna-tuned hyperparameters. Returns the extracted text, the denoised image, and per-character bounding boxes.

Full details, model architectures, training notebooks, and the API contract: [`stage1_ocr/README.md`](stage1_ocr/README.md).

### Stage 2 - Adaptive Huffman compression

A FastAPI service implementing **Vitter's Algorithm V** (JACM 1987) end-to-end from scratch: `Node` and `HuffmanTree` data structures, the two-step typed-block update, `MAX_NODES = 513` for the 256-byte alphabet plus a persistent NYT escape, a custom 3-bit-pad bit-packer, and the six rubric metrics. Exposes `/compress`, `/decompress`, and `/compress/steps` (per-byte trace of the tree, code map, and node swaps for the frontend animation).

Algorithm walk-through, wire format, library API, and design notes: [`stage2_huffman/README.md`](stage2_huffman/README.md).

---

## Service contracts

The wire format between Stage 1, Stage 2, and the frontend is defined in [`docs/CONTRACTS.md`](docs/CONTRACTS.md). At a glance:

- `POST /ocr` -> `{ extracted_text, denoised_image, character_data: [{ bbox: [x,y,w,h] }, ...] }`
- `POST /compress` -> `{ payload_base64, metrics: { 6 metrics }, code_map, tree_structure }`
- `POST /decompress` -> `{ text }`
- `POST /compress/steps` -> `{ steps: [{ step, char, is_new, swaps, tree, codes }, ...] }`

Stage 2 errors use a `{"error": "..."}` envelope. Stage 1 uses FastAPI's default `{"detail": "..."}` shape. Both use standard HTTP status codes (400 for bad input, 422 for validation failures, 500 for server faults).

---

## Performance notes

> [!WARNING]
> **Cold starts.** Stage 1 (CNN) loads PyTorch model weights on the first request, which is significantly slower than subsequent requests. Stage 2 (Huffman) is CPU-bound and starts instantly.
>
> **Action:** Send a single dummy image through the pipeline on startup before running latency benchmarks. `integration/pipeline.py::warmup()` does this automatically and is called by `integration/benchmark.py`.

The numbers in [End-to-end benchmarks](#end-to-end-benchmarks) reflect post-warmup latencies on an **Apple M4 (CPU-only)** local machine. Stage 1 accounts for roughly 61% of total latency; Stage 2 compress + decompress together take about 70 ms per page. The hosted [Cloud Run demo](https://frontend-xnnzv4dy6q-uc.a.run.app/) runs on smaller shared infrastructure (2 vCPU / 2 GB per service, scale-to-zero) so per-request latency there is higher and the first request after idle incurs a multi-second cold start.

---

## References

- J. S. Vitter, *"Design and Analysis of Dynamic Huffman Codes"*, JACM 1987
- D. A. Huffman, *"A Method for the Construction of Minimum-Redundancy Codes"*, Proc. IRE 1952
- Cohen et al., EMNIST: extended MNIST handwritten character dataset (`balanced` split, 47 classes)
- Castro-Bleda et al., NoisyOffice: synthetic noisy document dataset
- [`docs/CONTRACTS.md`](docs/CONTRACTS.md) - inter-service API contract
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) - deployment runbook
