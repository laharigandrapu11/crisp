
from __future__ import annotations

import random
import string

import pytest

from huffman import vitter
from huffman.tree import HuffmanTree


def encode_with_validation(data: bytes) -> str:
    tree = HuffmanTree()
    bits: list[str] = []
    tree.validate_invariants()

    for byte in data:
        leaf = tree.symbols_map.get(byte)
        if leaf is not None:
            bits.append(tree.path_from_root(leaf))
            vitter.vitter_update(tree, leaf)
        else:
            bits.append(tree.path_from_root(tree.nyt))
            bits.append(format(byte, "08b"))
            new_leaf = tree.split_nyt(byte)
            vitter.vitter_update(tree, new_leaf)
        tree.validate_invariants()

    return "".join(bits)


class TestHandTraced:
    @pytest.mark.parametrize("text", [
        "a",
        "aa",
        "ab",
        "aab",
        "abracadabra",
        "mississippi",
        "abcdefg",
    ])
    def test_round_trip(self, text):
        data = text.encode()
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    @pytest.mark.parametrize("text", [
        "a",
        "aab",
        "abracadabra",
        "mississippi",
    ])
    def test_invariants_hold_step_by_step(self, text):
        encode_with_validation(text.encode())


class TestEdgeCases:
    def test_single_byte(self):
        data = b"\x42"
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_all_same_byte(self):
        data = b"a" * 100
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_alternating(self):
        data = b"abab" * 50
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_null_bytes(self):
        data = b"\x00\x00\x00\x01\x02\x00"
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_high_bytes(self):
        data = b"\xff\xfe\xfd\xfc"
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_every_byte_value_once(self):
        data = bytes(range(256))
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data

    def test_every_byte_value_repeated(self):
        data = bytes(range(256)) * 4
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data


class TestRandomAscii:
    def test_many_short_strings_with_invariants(self):
        random.seed(42)
        for _ in range(200):
            length = random.randint(1, 300)
            text = "".join(random.choices(string.printable, k=length))
            data = text.encode()
            bits = encode_with_validation(data)
            assert vitter.decode(bits) == data

    def test_many_short_strings_fast(self):
        random.seed(123)
        for _ in range(1000):
            length = random.randint(1, 200)
            text = "".join(random.choices(string.printable, k=length))
            data = text.encode()
            bits, _ = vitter.encode(data)
            assert vitter.decode(bits) == data


class TestRandomBinary:
    def test_random_byte_sequences(self):
        random.seed(7)
        for _ in range(500):
            length = random.randint(1, 300)
            data = bytes(random.randrange(256) for _ in range(length))
            bits, _ = vitter.encode(data)
            assert vitter.decode(bits) == data


class TestLongInputs:
    @pytest.mark.parametrize("length", [1_000, 5_000, 10_000])
    def test_long_random_strings(self, length):
        random.seed(length)
        text = "".join(random.choices(string.printable, k=length))
        data = text.encode()
        bits, _ = vitter.encode(data)
        assert vitter.decode(bits) == data


class TestPublicApi:
    @pytest.mark.parametrize("text", [
        "7",
        "7391",
        "8675309867530986753098675",
        "00000",
        "abracadabra",
        "The quick brown fox jumps over the lazy dog.",
        "Unicode: café, naïve, résumé, 日本語",
        "The quick brown fox jumps over the lazy dog. " * 20,
    ])
    def test_compress_decompress_round_trip(self, text):
        raw, orig, total_bits = vitter.compress(text)
        assert vitter.decompress(raw) == text
        assert orig == len(text.encode("utf-8"))
        assert total_bits > 0

    def test_long_repeated_input_compresses_well(self):
        text = "aaaaaaaaaa" * 100
        raw, orig, _ = vitter.compress(text)
        ratio = orig / len(raw)
        assert ratio > 3.0, f"expected high compression on repetitive input, got {ratio:.3f}x"

    def test_random_input_does_not_compress_much(self):
        random.seed(0)
        data = bytes(random.randrange(256) for _ in range(2000))
        from huffman.bitpack import bits_to_bytes
        bits, _ = vitter.encode(data)
        raw = bits_to_bytes(bits)
        ratio = len(data) / len(raw)
        assert 0.7 < ratio < 1.2, f"random-data ratio out of sane range: {ratio:.3f}"
