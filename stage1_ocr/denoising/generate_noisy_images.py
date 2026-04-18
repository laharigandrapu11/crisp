"""Generate Gaussian and salt-and-pepper noisy versions of the clean grayscale
images in the NoisyOffice-style dataset.

Reads every `FontABC_Clean_EE.png` file from the clean grayscale directory and
writes two noisy counterparts into the simulated noisy directory, following
the existing `FontABC_NoiseD_EE.png` naming convention:

    FontABC_Clean_EE.png -> FontABC_Noiseg_EE.png   (Gaussian)
                         -> FontABC_Noises_EE.png   (salt & pepper)

Requires: numpy, Pillow.
"""

from __future__ import annotations


import re
import sys
import argparse
import numpy as np
from PIL import Image
from pathlib import Path


CLEAN_FILENAME_RE = re.compile(r"^(Font[A-Za-z]{3})_Clean_(TR|VA|TE)\.png$")


def add_gaussian_noise(
    img: np.ndarray, mean: float, std: float, rng: np.random.Generator
) -> np.ndarray:
    """Add zero(ish)-mean Gaussian noise on the 0-255 scale, clipped to uint8."""
    noise = rng.normal(loc=mean, scale=std, size=img.shape)
    noisy = img.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def add_salt_pepper_noise(
    img: np.ndarray, amount: float, ratio: float, rng: np.random.Generator
) -> np.ndarray:
    """Add salt-and-pepper noise.

    `amount` is the fraction of pixels that get corrupted in total; `ratio`
    controls the salt vs pepper split (ratio=0.5 -> equal salt and pepper).
    """
    if not 0.0 <= amount <= 1.0:
        raise ValueError("--sp-amount must be in [0, 1]")
    if not 0.0 <= ratio <= 1.0:
        raise ValueError("--sp-ratio must be in [0, 1]")

    out = img.copy()
    rand = rng.random(img.shape)
    salt_threshold = amount * ratio
    pepper_threshold = amount
    out[rand < salt_threshold] = 255
    out[(rand >= salt_threshold) & (rand < pepper_threshold)] = 0
    return out


def process_directory(
    clean_dir: Path,
    out_dir: Path,
    gaussian_mean: float,
    gaussian_std: float,
    sp_amount: float,
    sp_ratio: float,
    seed: int,
    overwrite: bool,
) -> tuple[int, int, int]:
    if not clean_dir.is_dir():
        raise FileNotFoundError(f"Clean image directory not found: {clean_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    written = 0
    skipped = 0
    unmatched = 0

    files = sorted(clean_dir.glob("*.png"))
    if not files:
        print(f"No .png files found in {clean_dir}", file=sys.stderr)

    for path in files:
        match = CLEAN_FILENAME_RE.match(path.name)
        if not match:
            print(f"[skip] unrecognized filename: {path.name}")
            unmatched += 1
            continue

        font, split = match.group(1), match.group(2)
        img = np.array(Image.open(path).convert("L"))

        targets = {
            "g": add_gaussian_noise(img, gaussian_mean, gaussian_std, rng),
            "s": add_salt_pepper_noise(img, sp_amount, sp_ratio, rng),
        }

        for code, noisy in targets.items():
            out_name = f"{font}_Noise{code}_{split}.png"
            out_path = out_dir / out_name
            if out_path.exists() and not overwrite:
                print(f"[skip] exists: {out_name}")
                skipped += 1
                continue
            Image.fromarray(noisy, mode="L").save(out_path)
            print(f"[write] {out_name}")
            written += 1

    return written, skipped, unmatched


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_clean = script_dir / "data" / "clean_images_grayscale"
    default_out = script_dir / "data" / "simulated_noisy_images_grayscale"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-dir", type=Path, default=default_clean)
    parser.add_argument("--out-dir", type=Path, default=default_out)
    parser.add_argument("--gaussian-mean", type=float, default=0.0)
    parser.add_argument("--gaussian-std", type=float, default=25.0)
    parser.add_argument("--sp-amount", type=float, default=0.05)
    parser.add_argument("--sp-ratio", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written, skipped, unmatched = process_directory(
        clean_dir=args.clean_dir,
        out_dir=args.out_dir,
        gaussian_mean=args.gaussian_mean,
        gaussian_std=args.gaussian_std,
        sp_amount=args.sp_amount,
        sp_ratio=args.sp_ratio,
        seed=args.seed,
        overwrite=args.overwrite,
    )
    print(
        f"\nDone. written={written}, skipped_existing={skipped}, "
        f"unmatched_filenames={unmatched}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
