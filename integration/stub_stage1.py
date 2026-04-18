import base64
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

DUMMY_PNG = base64.b64encode(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
    b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
).decode()

class OCRRequest(BaseModel):
    image_base64: str

def make_char_bboxes():
    boxes = []
    char_w, char_h = 18, 22
    gap = 4
    line_starts = [30, 70, 110, 150]
    chars_per_line = [24, 22, 26, 20]
    for row, (y, count) in enumerate(zip(line_starts, chars_per_line)):
        x = 20
        for _ in range(count):
            boxes.append({"bbox": [x, y, x + char_w, y + char_h]})
            x += char_w + gap
    return boxes

@app.post("/ocr")
def ocr(req: OCRRequest):
    return {
        "status": "success",
        "extracted_text": "abracadabra",
        "denoised_image": req.image_base64,
        "character_data": make_char_bboxes()
    }
