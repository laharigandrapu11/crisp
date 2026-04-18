import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STAGE1_URL = os.getenv("STAGE1_URL", "http://localhost:8000")
STAGE2_URL = os.getenv("STAGE2_URL", "http://localhost:8001")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/ocr")
async def ocr(request: Request):
    body = await request.json()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{STAGE1_URL}/ocr", json=body)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return JSONResponse(r.json())

@app.post("/api/compress")
async def compress(request: Request):
    body = await request.json()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{STAGE2_URL}/compress", json=body)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return JSONResponse(r.json())

@app.post("/api/compress/steps")
async def compress_steps(request: Request):
    body = await request.json()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{STAGE2_URL}/compress/steps", json=body)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return JSONResponse(r.json())

@app.post("/api/decompress")
async def decompress(request: Request):
    body = await request.json()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{STAGE2_URL}/decompress", json=body)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return JSONResponse(r.json())

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
