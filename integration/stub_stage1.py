from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class OCRRequest(BaseModel):
    image_base64: str

@app.post("/ocr")
def ocr(req: OCRRequest):
    return {"text": "7"}
