from __future__ import annotations

import base64
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import (
    CompressRequest, CompressResponse,
    DecompressRequest, DecompressResponse,
    HealthResponse, Metrics,
)
from .. import vitter
from .. import metrics as metrics_mod

app = FastAPI(
    title="Stage 2 — Adaptive Huffman Compression",
    description="Pure Vitter Algorithm V. Byte-level alphabet, 3-bit pad-length header, JSON+base64 transport.",
    version="1.0.0",
)

log = logging.getLogger("huffman.service")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/compress", response_model=CompressResponse)
def compress(req: CompressRequest) -> CompressResponse:
    if not req.text:
        raise HTTPException(status_code=400, detail="empty input")

    try:
        raw_bytes, original_bytes, total_bits, tree = vitter.compress_with_tree(req.text)
    except Exception as exc:
        log.exception("compression failed")
        raise HTTPException(status_code=500, detail=f"compression failed: {exc}") from exc

    payload_b64 = base64.b64encode(raw_bytes).decode("ascii")

    m = metrics_mod.compute_all(
        data=req.text.encode("utf-8"),
        raw_compressed=raw_bytes,
        total_bits_emitted=total_bits,
    )
    return CompressResponse(
        payload_base64=payload_b64,
        metrics=Metrics(**m),
        code_map=tree.code_map(),
        tree_structure=tree.to_dict(),
    )


@app.post("/decompress", response_model=DecompressResponse)
def decompress(req: DecompressRequest) -> DecompressResponse:
    if not req.payload_base64:
        raise HTTPException(status_code=400, detail="empty payload")

    try:
        raw_bytes = base64.b64decode(req.payload_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="malformed base64") from exc

    try:
        text = vitter.decompress(raw_bytes)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="payload decoded to invalid UTF-8") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"corrupted compressed payload: {exc}") from exc

    return DecompressResponse(text=text)


@app.exception_handler(HTTPException)
def http_exception_handler(_request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})
