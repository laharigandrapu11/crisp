import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Person B — build your Huffman compression service here
# Run with: uvicorn main:app --port 8001

app = FastAPI()

class CompressRequest(BaseModel):
    text: str

class DecompressRequest(BaseModel):
    payload_base64: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/compress")
def compress(req: CompressRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        # TODO: Person B — implement Adaptive Huffman encoding
        # IMPORTANT: calculate compression_ratio from raw binary BEFORE base64 encoding
        # Example:
        #   compressed_bytes = huffman_encode(req.text)        # raw binary
        #   original_size = len(req.text.encode())
        #   compressed_size = len(compressed_bytes)            # measure HERE before base64
        #   payload_b64 = base64.b64encode(compressed_bytes).decode()
        #   return {"payload_base64": payload_b64, "metrics": {...}}
        raise NotImplementedError
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Compress not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression error: {str(e)}")

@app.post("/decompress")
def decompress(req: DecompressRequest):
    if not req.payload_base64:
        raise HTTPException(status_code=400, detail="payload_base64 is required")

    try:
        base64.b64decode(req.payload_base64)  # validate base64 early
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    try:
        # TODO: Person B — decode base64, run Huffman decompression, return original text
        # Example:
        #   compressed_bytes = base64.b64decode(req.payload_base64)
        #   text = huffman_decode(compressed_bytes)
        #   return {"text": text}
        raise NotImplementedError
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Decompress not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decompression error: {str(e)}")
