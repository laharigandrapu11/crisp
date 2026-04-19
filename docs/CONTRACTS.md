# Service Contracts

These are the agreed JSON shapes for both services. Do NOT change them without telling the whole team.

---

## Stage 1 — OCR Service

**Endpoint:** `POST http://localhost:8000/ocr`

**Request:**
```json
{ "image_base64": "iVBORw0KG..." }
```

**Response:**
```json
{
  "status": "success",
  "extracted_text": "7391",
  "denoised_image": "base64_string_here...",
  "character_data": [
    { "bbox": [10, 10, 25, 40] }
  ]
}
```

> `extracted_text` is the recognized string — this is what gets passed to Stage 2.
> `denoised_image` is the CNN-denoised image (base64 PNG) — displayed in the UI.
> `character_data` bounding boxes are drawn as overlays on the denoised image in the UI.

---

## Stage 2 — Compression Service

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
  },
  "code_map": {
    "a": "1",
    "b": "000",
    "NYT": "0100"
  },
  "tree_structure": {
    "name": "root",
    "weight": 11,
    "number": 511,
    "children": [
      {
        "name": "internal",
        "weight": 6,
        "number": 510,
        "children": [
          { "name": "b", "weight": 2, "number": 506 },
          { "name": "r", "weight": 2, "number": 505 }
        ]
      },
      { "name": "a", "weight": 5, "number": 509 }
    ]
  }
}
```

> `code_map` maps each character to its Huffman binary code string — used to render the tree.
> `tree_structure` is the full Adaptive Huffman tree. Leaf nodes have no `children`. `NYT` = Not Yet Transmitted node.

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
