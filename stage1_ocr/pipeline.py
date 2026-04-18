"""Stage 1 OCR pipeline: denoise -> segment -> recognize."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from segmentation.segment_characters import segment_image

MODELS_DIR = Path(__file__).resolve().parent / "models"
DENOISER_INPUT_SIZE = (540, 420)

class DenoisingAutoEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 6, 5),
            nn.ReLU(inplace=True),
            nn.Conv2d(6, 12, 3),
            nn.ReLU(inplace=True),
            nn.Conv2d(12, 24, 3),
            nn.ReLU(inplace=True),
            nn.Conv2d(24, 64, 1),
            nn.ReLU(inplace=True),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 24, 1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(24, 12, 3),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(12, 6, 3),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(6, 1, 5),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


class RecognitionCNN(nn.Module):
    # Must match the architecture in recognition/train_recognition_cnn.ipynb.
    def __init__(
        self,
        conv1_ch: int = 32,
        conv2_ch: int = 64,
        fc_dim: int = 128,
        dropout: float = 0.3,
        num_classes: int = 47,
    ) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, conv1_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(conv1_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(conv1_ch, conv1_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(conv1_ch),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(conv1_ch, conv2_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(conv2_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(conv2_ch, conv2_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(conv2_ch),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(conv2_ch * 7 * 7, fc_dim, bias=False),
            nn.BatchNorm1d(fc_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


_device: torch.device | None = None
_denoiser_cache: DenoisingAutoEncoder | None = None
_recog_cnn_cache: tuple[RecognitionCNN, dict[str, Any]] | None = None


def _pick_device() -> torch.device:
    global _device
    if _device is not None:
        return _device
    if torch.cuda.is_available():
        _device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        _device = torch.device("mps")
    else:
        _device = torch.device("cpu")
    return _device


def _load_denoiser() -> DenoisingAutoEncoder:
    global _denoiser_cache
    if _denoiser_cache is not None:
        return _denoiser_cache
    weights_path = MODELS_DIR / "denoising_autoencoder.pt"
    if not weights_path.is_file():
        raise FileNotFoundError(f"Denoising weights not found at {weights_path}.")
    model = DenoisingAutoEncoder().to(_pick_device())
    state = torch.load(weights_path, map_location=_pick_device())
    model.load_state_dict(state)
    model.eval()
    _denoiser_cache = model
    return model


def _load_recog_cnn() -> tuple[RecognitionCNN, dict[str, Any]]:
    global _recog_cnn_cache
    if _recog_cnn_cache is not None:
        return _recog_cnn_cache
    weights_path = MODELS_DIR / "recognition_cnn.pt"
    if not weights_path.is_file():
        raise FileNotFoundError(f"Recognition CNN weights not found at {weights_path}.")
    ckpt = torch.load(weights_path, map_location=_pick_device())
    params = ckpt["best_params"]
    model = RecognitionCNN(
        conv1_ch=params["conv1_ch"],
        conv2_ch=params["conv2_ch"],
        fc_dim=params["fc_dim"],
        dropout=params["dropout"],
        num_classes=ckpt["num_classes"],
    ).to(_pick_device())
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    meta = {
        "label_map": ckpt["label_map"],
        "img_size": ckpt["img_size"],
        "mean": ckpt["mean"],
        "std": ckpt["std"],
    }
    _recog_cnn_cache = (model, meta)
    return _recog_cnn_cache


def _decode_image(image_base64: str) -> np.ndarray:
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid base64 input: {e}") from e
    if not raw:
        raise ValueError("Decoded image is empty.")
    img = Image.open(io.BytesIO(raw)).convert("L")
    return np.asarray(img, dtype=np.uint8)


def _encode_png_base64(img_u8: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(img_u8, mode="L").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@torch.no_grad()
def _denoise(gray_u8: np.ndarray) -> np.ndarray:
    model = _load_denoiser()
    device = _pick_device()
    orig_h, orig_w = gray_u8.shape

    resized = cv2.resize(
        gray_u8, DENOISER_INPUT_SIZE, interpolation=cv2.INTER_AREA
    ).astype(np.float32) / 255.0
    x = torch.from_numpy(resized).unsqueeze(0).unsqueeze(0).to(device)
    y = model(x).clamp(0.0, 1.0).squeeze().cpu().numpy()

    out = (y * 255.0).astype(np.uint8)
    return cv2.resize(out, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)


def _collect_word_groups(
    segmentation: dict,
) -> list[list[tuple[int, int, int, int]]]:
    groups: list[list[tuple[int, int, int, int]]] = []
    for line in segmentation["lines"]:
        for word in line["words"]:
            chars = [
                (int(x), int(y), int(w), int(h))
                for (x, y, w, h) in (ch["bbox"] for ch in word["chars"])
            ]
            if chars:
                groups.append(chars)
    return groups


def _crop_and_pad_square(gray_u8: np.ndarray, bbox: tuple[int, int, int, int],
                         pad_ratio: float = 0.2) -> np.ndarray:
    x, y, w, h = bbox
    crop = gray_u8[y : y + h, x : x + w]
    if crop.size == 0:
        return np.full((28, 28), 255, dtype=np.uint8)

    pad = int(round(max(w, h) * pad_ratio))
    side = max(w, h) + 2 * pad
    canvas = np.full((side, side), 255, dtype=np.uint8)
    y0 = (side - h) // 2
    x0 = (side - w) // 2
    canvas[y0 : y0 + h, x0 : x0 + w] = crop
    return canvas


def _prepare_char_tensor(
    canvas: np.ndarray, img_size: int, mean: tuple, std: tuple
) -> torch.Tensor:
    resized = cv2.resize(canvas, (img_size, img_size), interpolation=cv2.INTER_AREA)
    # EMNIST is white-on-black, our input is the opposite.
    inverted = 255 - resized
    tensor = torch.from_numpy(inverted.astype(np.float32) / 255.0).unsqueeze(0)
    m = torch.tensor(mean).view(-1, 1, 1)
    s = torch.tensor(std).view(-1, 1, 1)
    return (tensor - m) / s


@torch.no_grad()
def _recognize_words(
    gray_u8: np.ndarray,
    word_groups: list[list[tuple[int, int, int, int]]],
    batch_size: int = 64,
) -> str:
    if not word_groups:
        return ""

    device = _pick_device()
    model, meta = _load_recog_cnn()
    label_map = meta["label_map"]

    flat_bboxes = [bb for group in word_groups for bb in group]
    tensors = [
        _prepare_char_tensor(
            _crop_and_pad_square(gray_u8, bb),
            meta["img_size"], meta["mean"], meta["std"],
        )
        for bb in flat_bboxes
    ]

    preds: list[int] = []
    for i in range(0, len(tensors), batch_size):
        batch = torch.stack(tensors[i : i + batch_size]).to(device)
        logits = model(batch)
        preds.extend(logits.argmax(dim=1).cpu().tolist())

    words: list[str] = []
    cursor = 0
    for group in word_groups:
        n = len(group)
        words.append("".join(label_map[p] for p in preds[cursor : cursor + n]))
        cursor += n
    return " ".join(words)


def ocr(image_base64: str) -> dict[str, Any]:
    """Run the OCR pipeline: denoise -> segment -> recognize."""
    gray = _decode_image(image_base64)
    denoised = _denoise(gray)

    # segment_image expects a 3-channel image.
    denoised_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    segmentation = segment_image(denoised_bgr)
    word_groups = _collect_word_groups(segmentation)

    extracted_text = _recognize_words(denoised, word_groups)

    flat_bboxes = [bb for group in word_groups for bb in group]
    return {
        "status": "success",
        "extracted_text": extracted_text,
        "denoised_image": _encode_png_base64(denoised),
        "character_data": [{"bbox": list(bb)} for bb in flat_bboxes],
    }
