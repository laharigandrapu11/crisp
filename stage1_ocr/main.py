import base64
import io
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class OCRRequest(BaseModel):
    image_base64: str

class BBox(BaseModel):
    bbox: List[int]

class OCRResponse(BaseModel):
    status: str
    extracted_text: str
    denoised_image: str
    character_data: List[BBox]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr", response_model=OCRResponse)
def ocr(req: OCRRequest):
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    try:
        image_bytes = base64.b64decode(req.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Image is empty")

    try:
        raise NotImplementedError
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="OCR not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
