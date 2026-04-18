import base64
import time
import json
import os
import requests

STAGE1_URL = os.getenv("STAGE1_URL", "http://localhost:8000")
STAGE2_URL = os.getenv("STAGE2_URL", "http://localhost:8001")


def warmup():
    dummy_img = base64.b64encode(b"dummy").decode()
    try:
        requests.post(f"{STAGE1_URL}/ocr", json={"image_base64": dummy_img}, timeout=30)
        requests.post(f"{STAGE2_URL}/compress", json={"text": "0"}, timeout=10)
    except Exception:
        pass


def run_pipeline(image_path):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    t0 = time.time()
    r1 = requests.post(f"{STAGE1_URL}/ocr", json={"image_base64": img_b64})
    t1 = time.time()
    text = r1.json()["text"]

    r2 = requests.post(f"{STAGE2_URL}/compress", json={"text": text})
    t2 = time.time()
    payload = r2.json()["payload_base64"]
    metrics = r2.json()["metrics"]

    r3 = requests.post(f"{STAGE2_URL}/decompress", json={"payload_base64": payload})
    t3 = time.time()
    recovered = r3.json()["text"]

    print(f"OCR text: {text} | Recovered: {recovered} | Lossless: {text == recovered}")
    print(f"Stage1: {t1-t0:.3f}s | Compress: {t2-t1:.3f}s | Decompress: {t3-t2:.3f}s | Total: {t3-t0:.3f}s")
    print(json.dumps(metrics, indent=2))
    return {"text": text, "recovered": recovered, "metrics": metrics,
            "latency": {"stage1": t1-t0, "compress": t2-t1, "decompress": t3-t2, "total": t3-t0}}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path>")
        sys.exit(1)
    warmup()
    run_pipeline(sys.argv[1])
