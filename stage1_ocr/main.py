from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline import ocr as run_ocr

# Run with: uvicorn main:app --port 8000

app = FastAPI()


class OCRRequest(BaseModel):
    image_base64: str


class CharacterBox(BaseModel):
    bbox: list[int]


class OCRResponse(BaseModel):
    status: str
    extracted_text: str
    denoised_image: str
    character_data: list[CharacterBox]


@app.get("/health")
def health():
    return {"status": "ok"}


ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"description": "Invalid or missing base64 image input"},
    500: {"description": "Unexpected inference error"},
    503: {"description": "Required model weights are missing"},
}


@app.post("/ocr", response_model=OCRResponse, responses=ERROR_RESPONSES)
def ocr(req: OCRRequest):
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    try:
        return run_ocr(req.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model weights missing: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
