from __future__ import annotations
from pydantic import BaseModel, Field


class CompressRequest(BaseModel):
    text: str = Field(..., description="UTF-8 text to compress")


class DecompressRequest(BaseModel):
    payload_base64: str = Field(..., description="Base64-encoded compressed payload from /compress")


class Metrics(BaseModel):
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    entropy: float
    avg_bits_per_symbol: float
    encoding_efficiency: float


class CompressResponse(BaseModel):
    payload_base64: str = Field(..., description="Base64-encoded compressed bytes (use in /decompress)")
    metrics: Metrics
    code_map: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Final {symbol: bit-string} mapping after all bytes have been encoded. "
            "Reflects the tree's final state — codes used mid-stream differ because "
            "the tree adapts on every byte. Non-printable bytes appear as \\xNN escapes."
        ),
    )
    tree_structure: dict = Field(
        default_factory=dict,
        description=(
            "Nested-dict of the final Huffman tree for d3 / visualisation. "
            "Each node has {name, weight, number}; internal nodes add 'children'."
        ),
    )


class DecompressResponse(BaseModel):
    text: str = Field(..., description="Recovered UTF-8 text")


class HealthResponse(BaseModel):
    status: str = "ok"
    algorithm: str = "vitter-algorithm-v"


class ErrorResponse(BaseModel):
    error: str
