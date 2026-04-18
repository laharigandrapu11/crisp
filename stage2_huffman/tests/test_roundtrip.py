

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import string
import pytest

from huffman.vitter import compress, decompress


def roundtrip(text: str) -> bool:
    """Return True if decompress(compress(text)) == text."""
    raw, _, _ = compress(text)
    return decompress(raw) == text



@pytest.mark.parametrize("text", [
    "7391",       
    "7",          
    "0",
    "00000",      
    "8675309",
    "abracadabra", 
    "abb",          
    "aab",
    "abc",
])
def test_known_strings(text):
    assert roundtrip(text), f"round-trip failed for {text!r}"


def test_single_character():
    assert roundtrip("a")
    assert roundtrip("z")
    assert roundtrip("0")


def test_single_repeated_character():
    for char in ["a", "0", " ", "Z"]:
        text = char * 100
        assert roundtrip(text), f"round-trip failed for {char!r} * 100"


def test_two_character_alternating():
    assert roundtrip("ababababab")
    assert roundtrip("0101010101")


def test_all_printable_ascii_once():
    text = string.printable
    assert roundtrip(text)


def test_digits_only():
    for _ in range(20):
        text = "".join(random.choices("0123456789", k=random.randint(1, 20)))
        assert roundtrip(text), f"round-trip failed for {text!r}"


def test_random_printable_strings():
    rng = random.Random(42)
    failures = []
    for i in range(1000):
        length = rng.randint(1, 500)
        text = "".join(rng.choices(string.printable, k=length))
        if not roundtrip(text):
            failures.append((i, repr(text[:40])))
    assert not failures, f"{len(failures)} round-trip failures: {failures[:5]}"


def test_random_byte_sequences():
    rng = random.Random(99)
    failures = []
    for i in range(100):
        length = rng.randint(1, 200)
        data = bytes(rng.randint(0, 255) for _ in range(length))
        try:
            text = data.decode("latin-1")   
        except Exception:
            continue
        try:
            raw, _, _ = compress(text)
            recovered = decompress(raw)
            if recovered != text:
                failures.append((i, repr(text[:30])))
        except Exception as exc:
            failures.append((i, f"exception: {exc}"))
    assert not failures, f"{len(failures)} byte-sequence failures: {failures[:5]}"


def test_long_input():
    rng = random.Random(7)
    text = "".join(rng.choices(string.ascii_letters + string.digits, k=10_000))
    assert roundtrip(text)


def test_long_repeated():
    text = "abcd" * 2500   
    assert roundtrip(text)


def test_metrics_present_and_sane():
    from huffman.metrics import compute_all
    text = "7391"
    data = text.encode("utf-8")
    raw, orig, bits = compress(text)
    m = compute_all(data, raw, bits)

    assert m["original_bytes"] == 4
    assert m["compressed_bytes"] > 0
    assert m["compression_ratio"] > 0
    assert 0.0 <= m["entropy"] <= 8.0          
    assert m["avg_bits_per_symbol"] > 0
    assert 0.0 <= m["encoding_efficiency"] <= 1.0


def test_entropy_zero_for_constant_string():
    from huffman.metrics import shannon_entropy
    assert shannon_entropy(b"aaaaaaa") == 0.0


def test_entropy_max_for_two_equal_symbols():
    from huffman.metrics import shannon_entropy
    import math
    h = shannon_entropy(b"ababab")
    assert abs(h - 1.0) < 1e-9
