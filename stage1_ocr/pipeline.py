"""End-to-end Stage 1 OCR helper.

Takes a base64-encoded image and runs the full Stage 1 pipeline:

    1. Denoise  -- DenoisingAutoEncoder (see denoising/train_denoising_autoencoder.ipynb)
    2. Segment  -- classical CV pipeline in segmentation/segment_characters.py
    3. Recognize -- per-character CNN or EfficientNet-B0 (see recognition/*.ipynb)

Returns a payload of the form:

    {
        "status": "success",
        "extracted_text": "7391",
        "denoised_image": "<base64 PNG>",
        "character_data": [{"bbox": [x, y, w, h]}, ...],
    }

The `recog_model` argument controls which recognizer is used:

    - "cnn"    -> stage1_ocr/models/recognition_cnn.pt      (default)
    - "effnet" -> stage1_ocr/models/recognition_efficientnet.pt

Both models + the denoiser are cached on first use so repeated calls are fast.
"""

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
from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

from segmentation.segment_characters import segment_image

MODELS_DIR = Path(__file__).resolve().parent / "models"

# Denoiser was trained on images resized to (W=540, H=420). See
# denoising/train_denoising_autoencoder.ipynb for the exact IMG_SIZE.
DENOISER_INPUT_SIZE = (540, 420)

# EMNIST byclass label map, order = digits, uppercase, lowercase (62 classes).
_LABEL_MAP_DEFAULT = (
    [str(d) for d in range(10)]
    + [chr(ord("A") + i) for i in range(26)]
    + [chr(ord("a") + i) for i in range(26)]
)


class DenoisingAutoEncoder(nn.Module):
    """Mirror of the architecture defined in the training notebook."""

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
    """Mirror of the architecture defined in the CNN training notebook."""

    def __init__(
        self,
        conv1_ch: int = 32,
        conv2_ch: int = 64,
        fc_dim: int = 128,
        dropout: float = 0.3,
        num_classes: int = 62,
    ) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, conv1_ch, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(conv1_ch, conv1_ch, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(conv1_ch, conv2_ch, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(conv2_ch, conv2_ch, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(conv2_ch * 7 * 7, fc_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


_device: torch.device | None = None
_denoiser_cache: DenoisingAutoEncoder | None = None
_recog_cnn_cache: tuple[RecognitionCNN, dict[str, Any]] | None = None
_recog_effnet_cache: tuple[nn.Module, dict[str, Any]] | None = None


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
        raise FileNotFoundError(
            f"Denoising weights not found at {weights_path}. "
            "Run stage1_ocr/denoising/train_denoising_autoencoder.ipynb first."
        )
    model = DenoisingAutoEncoder().to(_pick_device())
    state = torch.load(weights_path, map_location=_pick_device())
    # The denoiser notebook saves a bare state_dict (no wrapping dict).
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
        raise FileNotFoundError(
            f"Recognition CNN weights not found at {weights_path}. "
            "Run stage1_ocr/recognition/train_recognition_cnn.ipynb first."
        )
    ckpt = torch.load(weights_path, map_location=_pick_device())
    params = ckpt.get("best_params", {})
    model = RecognitionCNN(
        conv1_ch=params.get("conv1_ch", 32),
        conv2_ch=params.get("conv2_ch", 64),
        fc_dim=params.get("fc_dim", 128),
        dropout=params.get("dropout", 0.3),
        num_classes=ckpt.get("num_classes", 62),
    ).to(_pick_device())
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    meta = {
        "label_map": ckpt.get("label_map", _LABEL_MAP_DEFAULT),
        "img_size": ckpt.get("img_size", 28),
        "mean": ckpt.get("mean", (0.1307,)),
        "std": ckpt.get("std", (0.3081,)),
    }
    _recog_cnn_cache = (model, meta)
    return _recog_cnn_cache


def _load_recog_effnet() -> tuple[nn.Module, dict[str, Any]]:
    global _recog_effnet_cache
    if _recog_effnet_cache is not None:
        return _recog_effnet_cache
    weights_path = MODELS_DIR / "recognition_efficientnet.pt"
    if not weights_path.is_file():
        raise FileNotFoundError(
            f"EfficientNet weights not found at {weights_path}. "
            "Run stage1_ocr/recognition/train_recognition_efficientnet.ipynb first."
        )
    ckpt = torch.load(weights_path, map_location=_pick_device())
    num_classes = ckpt.get("num_classes", 62)
    dropout = ckpt.get("best_config", {}).get("dropout", 0.2)

    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(dropout, inplace=False),
        nn.Linear(in_features, num_classes),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(_pick_device())
    model.eval()

    weights_meta = EfficientNet_B0_Weights.IMAGENET1K_V1.transforms()
    meta = {
        "label_map": ckpt.get("label_map", _LABEL_MAP_DEFAULT),
        "input_size": ckpt.get("input_size", 96),
        "mean": tuple(ckpt.get("mean", weights_meta.mean)),
        "std": tuple(ckpt.get("std", weights_meta.std)),
    }
    _recog_effnet_cache = (model, meta)
    return _recog_effnet_cache


def _decode_image(image_base64: str) -> np.ndarray:
    """Decode a base64-encoded image into a grayscale uint8 numpy array."""
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
    """Resize -> run autoencoder -> resize back. Returns uint8 at input resolution."""
    model = _load_denoiser()
    device = _pick_device()
    orig_h, orig_w = gray_u8.shape

    resized = cv2.resize(
        gray_u8, DENOISER_INPUT_SIZE, interpolation=cv2.INTER_AREA
    ).astype(np.float32) / 255.0
    x = torch.from_numpy(resized).unsqueeze(0).unsqueeze(0).to(device)
    y = model(x).clamp(0.0, 1.0).squeeze().cpu().numpy()

    out = (y * 255.0).astype(np.uint8)
    # Resize back to the original resolution so segmentation bboxes line up
    # with the input image's pixel coordinates.
    return cv2.resize(out, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)


def _collect_word_groups(
    segmentation: dict,
) -> list[list[tuple[int, int, int, int]]]:
    """Group character bboxes by word, in reading order.

    Returns a flat list of word-groups across all lines (line 0's words first,
    then line 1's words, ...). Each word-group is a list of `(x, y, w, h)`
    character bboxes left-to-right. Used so the recognizer can insert spaces
    between words when assembling the final string.
    """
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
    """Crop a character bbox and pad it to a square on a white background.

    EMNIST glyphs are centered in their canvas with breathing room on all
    sides, so we add ~20% margin before padding to square to match that prior.
    """
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


def _prepare_char_tensor_cnn(
    canvas: np.ndarray, img_size: int, mean: tuple, std: tuple
) -> torch.Tensor:
    """Resize to (img_size, img_size), invert to white-on-black, normalize."""
    resized = cv2.resize(canvas, (img_size, img_size), interpolation=cv2.INTER_AREA)
    # Source is dark-text-on-light-bg; EMNIST training data is the opposite.
    inverted = 255 - resized
    tensor = torch.from_numpy(inverted.astype(np.float32) / 255.0).unsqueeze(0)
    m = torch.tensor(mean).view(-1, 1, 1)
    s = torch.tensor(std).view(-1, 1, 1)
    return (tensor - m) / s


_effnet_base_transform_cache: dict[int, Any] = {}


def _prepare_char_tensor_effnet(
    canvas: np.ndarray, input_size: int, mean: tuple, std: tuple
) -> torch.Tensor:
    """Mirror the EfficientNet eval transforms (pre-Normalize steps)."""
    inverted = 255 - canvas
    pil = Image.fromarray(inverted, mode="L")
    if input_size not in _effnet_base_transform_cache:
        _effnet_base_transform_cache[input_size] = transforms.Compose(
            [
                transforms.Lambda(lambda img: img.convert("RGB")),
                transforms.Resize(
                    input_size,
                    interpolation=transforms.InterpolationMode.BILINEAR,
                ),
                transforms.CenterCrop(input_size),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
            ]
        )
    return _effnet_base_transform_cache[input_size](pil)


@torch.no_grad()
def _recognize_words(
    gray_u8: np.ndarray,
    word_groups: list[list[tuple[int, int, int, int]]],
    recog_model: str,
    batch_size: int = 64,
) -> str:
    """Recognize every character crop and reassemble with spaces between words."""
    if not word_groups:
        return ""

    device = _pick_device()
    if recog_model == "cnn":
        model, meta = _load_recog_cnn()
        prepare = lambda canvas: _prepare_char_tensor_cnn(
            canvas, meta["img_size"], meta["mean"], meta["std"]
        )
    elif recog_model == "effnet":
        model, meta = _load_recog_effnet()
        prepare = lambda canvas: _prepare_char_tensor_effnet(
            canvas, meta["input_size"], meta["mean"], meta["std"]
        )
    else:
        raise ValueError(f"Unknown recog_model={recog_model!r}. Use 'cnn' or 'effnet'.")

    label_map = meta["label_map"]

    flat_bboxes = [bb for group in word_groups for bb in group]
    tensors = [prepare(_crop_and_pad_square(gray_u8, bb)) for bb in flat_bboxes]

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


def ocr(image_base64: str, recog_model: str = "cnn") -> dict[str, Any]:
    """Run the full Stage 1 OCR pipeline on a base64-encoded image.

    Args:
        image_base64: Base64 string of any PIL-readable image (PNG, JPEG, ...).
        recog_model: "cnn" for the from-scratch CNN, "effnet" for EfficientNet-B0.

    Returns:
        {
            "status": "success",
            "extracted_text": "...",
            "denoised_image": "<base64 PNG>",
            "character_data": [{"bbox": [x, y, w, h]}, ...],
        }
    """
    gray = _decode_image(image_base64)
    denoised = _denoise(gray)

    # Segment on the 3-channel view because segment_image branches on ndim.
    denoised_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    segmentation = segment_image(denoised_bgr)
    word_groups = _collect_word_groups(segmentation)

    extracted_text = _recognize_words(denoised, word_groups, recog_model=recog_model)

    flat_bboxes = [bb for group in word_groups for bb in group]
    return {
        "status": "success",
        "extracted_text": extracted_text,
        "denoised_image": _encode_png_base64(denoised),
        "character_data": [{"bbox": list(bb)} for bb in flat_bboxes],
    }
