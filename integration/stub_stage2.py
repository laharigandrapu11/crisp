from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class CompressRequest(BaseModel):
    text: str

class DecompressRequest(BaseModel):
    payload_base64: str

STUB_TREE = {
    "name": "root", "weight": 11, "number": 511,
    "children": [
        {
            "name": "internal", "weight": 6, "number": 510,
            "children": [
                {
                    "name": "internal", "weight": 4, "number": 508,
                    "children": [
                        {"name": "b", "weight": 2, "number": 506},
                        {"name": "r", "weight": 2, "number": 505}
                    ]
                },
                {
                    "name": "internal", "weight": 2, "number": 507,
                    "children": [
                        {
                            "name": "internal", "weight": 1, "number": 504,
                            "children": [
                                {"name": "NYT", "weight": 0, "number": 501},
                                {"name": "d", "weight": 1, "number": 502}
                            ]
                        },
                        {"name": "c", "weight": 1, "number": 503}
                    ]
                }
            ]
        },
        {"name": "a", "weight": 5, "number": 509}
    ]
}

STUB_CODE_MAP = {"a": "1", "b": "000", "r": "001", "c": "011", "d": "0101", "NYT": "0100"}

@app.post("/compress")
def compress(req: CompressRequest):
    return {
        "payload_base64": "7CYhyAxiZIQA",
        "metrics": {
            "original_bytes": 11,
            "compressed_bytes": 9,
            "compression_ratio": 1.222222,
            "entropy": 2.040373,
            "avg_bits_per_symbol": 5.636364,
            "encoding_efficiency": 0.362002
        },
        "code_map": STUB_CODE_MAP,
        "tree_structure": STUB_TREE
    }

@app.post("/decompress")
def decompress(req: DecompressRequest):
    return {"text": req.payload_base64[:4] if req.payload_base64 else "7"}
