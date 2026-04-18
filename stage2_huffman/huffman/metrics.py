from __future__ import annotations
import math
from collections import Counter


def shannon_entropy(data: bytes) -> float:
    """H = -Σ p(x)·log₂p(x). Returns 0.0 for empty input."""
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


def compression_ratio(original_bytes: int, compressed_bytes: int) -> float:
    if compressed_bytes == 0:
        return 0.0
    return original_bytes / compressed_bytes


def avg_bits_per_symbol(total_bits_emitted: int, num_symbols: int) -> float:
    if num_symbols == 0:
        return 0.0
    return total_bits_emitted / num_symbols


def encoding_efficiency(entropy: float, avg_bits: float) -> float:
    """entropy / avg_bits_per_symbol, clamped to [0, 1]."""
    if avg_bits == 0.0:
        return 0.0
    return max(0.0, min(1.0, entropy / avg_bits))


def compute_all(data: bytes, raw_compressed: bytes, total_bits_emitted: int) -> dict:
    orig  = len(data)
    comp  = len(raw_compressed)
    n_sym = orig
    h     = shannon_entropy(data)
    avg   = avg_bits_per_symbol(total_bits_emitted, n_sym)
    eff   = encoding_efficiency(h, avg)
    ratio = compression_ratio(orig, comp)
    return {
        "original_bytes":      orig,
        "compressed_bytes":    comp,
        "compression_ratio":   round(ratio, 6),
        "entropy":             round(h,     6),
        "avg_bits_per_symbol": round(avg,   6),
        "encoding_efficiency": round(eff,   6),
    }
