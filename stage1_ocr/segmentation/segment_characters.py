"""Segment characters from a printed-text image.

Pipeline: binarize -> split into lines -> split into words -> connected
components per word, splitting any too-wide blob at projection minima.

Usage:
    python segment_characters.py --image page.png --out-dir out/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return cv2.GaussianBlur(gray, (3, 3), 0)


def binarize(gray: np.ndarray) -> np.ndarray:
    # Inverted Otsu so text pixels are 255.
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return [(start, end_exclusive), ...] for True runs in a 1-D bool array."""
    if not mask.any():
        return []
    padded = np.concatenate([[False], mask, [False]])
    diff = np.diff(padded.astype(np.int8))
    starts = np.nonzero(diff == 1)[0]
    ends = np.nonzero(diff == -1)[0]
    return list(zip(starts.tolist(), ends.tolist()))


def segment_lines(
    binary: np.ndarray, min_line_height: int = 4
) -> list[tuple[int, int]]:
    row_ink = binary.sum(axis=1) / 255.0
    if row_ink.max() == 0:
        return []

    threshold = 0.05 * row_ink.max()
    mask = row_ink > threshold

    lines: list[tuple[int, int]] = []
    for y0, y1 in _runs(mask):
        if y1 - y0 >= min_line_height:
            lines.append((y0, y1))
    return lines


def adaptive_word_gap(col_ink: np.ndarray) -> int:
    # Pick the largest jump in sorted gap widths as the word/char split.
    zero_runs = _runs(col_ink == 0)
    if len(zero_runs) < 3:
        return 10**9

    widths = sorted(e - s for s, e in zero_runs)
    trimmed = widths[1:-1] if len(widths) > 4 else widths
    arr = np.array(trimmed, dtype=np.float32)
    if arr.size < 2:
        return max(widths) + 1

    ratios = arr[1:] / np.maximum(arr[:-1], 1e-3)
    jump_idx = int(np.argmax(ratios))
    if ratios[jump_idx] < 1.8:
        return max(widths) + 1

    return max(int(arr[jump_idx + 1]), 3)


def segment_words(line_bin: np.ndarray) -> list[tuple[int, int]]:
    col_ink = line_bin.sum(axis=0) / 255.0
    word_gap = adaptive_word_gap(col_ink)

    ink_runs = _runs(col_ink > 0)
    if not ink_runs:
        return []

    words: list[tuple[int, int]] = []
    cur_start, cur_end = ink_runs[0]
    for s, e in ink_runs[1:]:
        if s - cur_end >= word_gap:
            words.append((cur_start, cur_end))
            cur_start = s
        cur_end = e
    words.append((cur_start, cur_end))
    return [(s, e) for s, e in words if e - s >= 2]


def _raw_components(
    word_bin: np.ndarray, min_area: int
) -> list[tuple[int, int, int, int]]:
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(word_bin, connectivity=8)
    boxes: list[tuple[int, int, int, int]] = []
    for i in range(1, n_labels):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        boxes.append((int(x), int(y), int(w), int(h)))
    return boxes


def _split_wide_cc(
    box: tuple[int, int, int, int],
    word_bin: np.ndarray,
    target_width: float,
    wide_ratio: float = 1.4,
) -> list[tuple[int, int, int, int]]:
    # Cut touching glyphs at the lowest points of a smoothed column profile.
    x, y, w, h = box
    if w < wide_ratio * target_width:
        return [box]

    n = int(round(w / max(target_width, 1.0)))
    if n < 2:
        return [box]

    roi = word_bin[y : y + h, x : x + w]
    col = roi.sum(axis=0).astype(np.float32)

    smooth_win = max(3, int(target_width * 0.4) | 1)
    kernel = np.ones(smooth_win, dtype=np.float32) / smooth_win
    col_s = np.convolve(col, kernel, mode="same")

    min_spacing = max(2, int(round(target_width * 0.6)))
    candidates = list(range(1, w - 1))
    candidates.sort(key=lambda i: (col_s[i], abs(i - w / 2)))

    cuts: list[int] = []
    for idx in candidates:
        if len(cuts) >= n - 1:
            break
        if all(abs(idx - c) >= min_spacing for c in cuts):
            cuts.append(idx)
    cuts.sort()

    if not cuts:
        return [box]

    boundaries = [0] + cuts + [w]
    pieces: list[tuple[int, int, int, int]] = []
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        if b - a < 2:
            continue
        sub = roi[:, a:b]
        if sub.max() == 0:
            continue
        ys = np.nonzero(sub.any(axis=1))[0]
        xs = np.nonzero(sub.any(axis=0))[0]
        if ys.size == 0 or xs.size == 0:
            continue
        px = x + a + int(xs[0])
        py = y + int(ys[0])
        pw = int(xs[-1] - xs[0] + 1)
        ph = int(ys[-1] - ys[0] + 1)
        pieces.append((px, py, pw, ph))

    return pieces if pieces else [box]


def segment_chars(
    word_bin: np.ndarray, min_area: int, target_width: float
) -> list[tuple[int, int, int, int]]:
    raw = _raw_components(word_bin, min_area)
    boxes: list[tuple[int, int, int, int]] = []
    for cc in raw:
        boxes.extend(_split_wide_cc(cc, word_bin, target_width))
    boxes.sort(key=lambda b: b[0])
    return boxes


def _estimate_global_median_width(
    binary: np.ndarray,
    line_bands: list[tuple[int, int]],
    min_area: int,
) -> float:
    # Median CC width across lines, ignoring tiny noise and tall ligatures.
    if not line_bands:
        return 10.0
    median_line_h = float(np.median([y1 - y0 for y0, y1 in line_bands]))
    widths: list[int] = []
    for y0, y1 in line_bands:
        for _, _, w, h in _raw_components(binary[y0:y1, :], min_area):
            if 0.4 * median_line_h <= h <= 1.2 * median_line_h:
                widths.append(w)
    if not widths:
        return max(6.0, 0.5 * median_line_h)
    return max(4.0, float(np.median(widths)))


def segment_image(img: np.ndarray) -> dict:
    gray = preprocess(img)
    binary = binarize(gray)
    height, width = binary.shape[:2]

    line_bands = segment_lines(binary)

    if line_bands:
        median_line_h = float(np.median([y1 - y0 for y0, y1 in line_bands]))
    else:
        median_line_h = 10.0
    min_area = max(3, int(0.015 * median_line_h * median_line_h))
    target_width = _estimate_global_median_width(binary, line_bands, min_area)

    lines_out: list[dict] = []
    for li, (y0, y1) in enumerate(line_bands):
        line_bin = binary[y0:y1, :]
        word_bands = segment_words(line_bin)

        words_out: list[dict] = []
        for wi, (x0, x1) in enumerate(word_bands):
            word_bin = binary[y0:y1, x0:x1]
            char_boxes = segment_chars(
                word_bin, min_area=min_area, target_width=target_width
            )
            if not char_boxes:
                continue

            chars_out = [
                {
                    "index": ci,
                    "bbox": [x0 + bx, y0 + by, bw, bh],
                }
                for ci, (bx, by, bw, bh) in enumerate(char_boxes)
            ]
            wx0 = min(c["bbox"][0] for c in chars_out)
            wy0 = min(c["bbox"][1] for c in chars_out)
            wx1 = max(c["bbox"][0] + c["bbox"][2] for c in chars_out)
            wy1 = max(c["bbox"][1] + c["bbox"][3] for c in chars_out)
            words_out.append(
                {
                    "index": wi,
                    "bbox": [wx0, wy0, wx1 - wx0, wy1 - wy0],
                    "chars": chars_out,
                }
            )

        if not words_out:
            continue
        lx0 = min(w["bbox"][0] for w in words_out)
        ly0 = min(w["bbox"][1] for w in words_out)
        lx1 = max(w["bbox"][0] + w["bbox"][2] for w in words_out)
        ly1 = max(w["bbox"][1] + w["bbox"][3] for w in words_out)
        lines_out.append(
            {
                "index": li,
                "bbox": [lx0, ly0, lx1 - lx0, ly1 - ly0],
                "words": words_out,
            }
        )

    return {
        "width": int(width),
        "height": int(height),
        "median_char_width": round(target_width, 2),
        "lines": lines_out,
    }


def draw_boxes(img: np.ndarray, result: dict) -> np.ndarray:
    viz = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for line in result["lines"]:
        for word in line["words"]:
            for ch in word["chars"]:
                x, y, w, h = ch["bbox"]
                cv2.rectangle(viz, (x, y), (x + w, y + h), (0, 0, 255), 1)
    return viz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.image.is_file():
        raise FileNotFoundError(f"Input image not found: {args.image}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Failed to read image: {args.image}")

    result = segment_image(img)
    result["image"] = args.image.name

    stem = args.image.stem
    json_path = args.out_dir / f"{stem}_boxes.json"
    viz_path = args.out_dir / f"{stem}_viz.png"

    with json_path.open("w") as f:
        json.dump(result, f, indent=2)
    cv2.imwrite(str(viz_path), draw_boxes(img, result))

    n_lines = len(result["lines"])
    n_words = sum(len(l["words"]) for l in result["lines"])
    n_chars = sum(len(w["chars"]) for l in result["lines"] for w in l["words"])
    print(
        f"Done. lines={n_lines}, words={n_words}, chars={n_chars}\n"
        f"  JSON: {json_path}\n"
        f"  VIZ : {viz_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
