import base64
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Person A — build your CNN OCR service here
# Run with: uvicorn main:app --port 8000

app = FastAPI()

class OCRRequest(BaseModel):
    image_base64: str  # base64-encoded image

class OCRResponse(BaseModel):
    text: str  # recognized digits e.g. "7391"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr", response_model=OCRResponse)
def ocr(req: OCRRequest):
    # Validate base64 input
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    try:
        image_bytes = base64.b64decode(req.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Image is empty")

    try:
        # TODO: Person A — decode image, run through your CNN, return recognized text
        # Example:
        #   image = Image.open(io.BytesIO(image_bytes)).convert("L")
        #   text = your_model.predict(image)
        #   return OCRResponse(text=text)
        raise NotImplementedError
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="OCR not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
