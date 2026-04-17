# Service Contracts

These are the agreed JSON shapes for both services. Do NOT change them without telling the whole team.

---

## Stage 1 — OCR Service (Person A)

**Endpoint:** `POST http://localhost:8000/ocr`

**Request:**
```json
{ "image_base64": "iVBORw0KG..." }
```

**Response:**
```json
{ "text": "7391" }
```

---

## Stage 2 — Compression Service (Person B)

**Endpoint:** `POST http://localhost:8001/compress`

**Request:**
```json
{ "text": "7391" }
```

**Response:**
```json
{
  "payload_base64": "AbCdEf...",
  "metrics": {
    "original_bytes": 4,
    "compressed_bytes": 8,
    "compression_ratio": 0.5,
    "entropy": 2.0,
    "avg_bits_per_symbol": 9.0,
    "encoding_efficiency": 0.22
  }
}
```

---

**Endpoint:** `POST http://localhost:8001/decompress`

**Request:**
```json
{ "payload_base64": "AbCdEf..." }
```

**Response:**
```json
{ "text": "7391" }
```
