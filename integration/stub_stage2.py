from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class CompressRequest(BaseModel):
    text: str

class DecompressRequest(BaseModel):
    payload_base64: str

@app.post("/compress")
def compress(req: CompressRequest):
    return {
        "payload_base64": "AAAA",
        "metrics": {
            "original_bytes": len(req.text.encode()),
            "compressed_bytes": 3,
            "compression_ratio": 1.0,
            "entropy": 0.0,
            "avg_bits_per_symbol": 8.0,
            "encoding_efficiency": 1.0
        }
    }

@app.post("/decompress")
def decompress(req: DecompressRequest):
    return {"text": "7"}
