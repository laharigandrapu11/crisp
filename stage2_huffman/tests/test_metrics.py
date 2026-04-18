from __future__ import annotations

import math

import pytest

from huffman import metrics, vitter


class TestShannonEntropy:
    def test_empty_returns_zero(self):
        assert metrics.shannon_entropy(b"") == 0.0

    def test_single_symbol_is_zero(self):
        assert metrics.shannon_entropy(b"aaaa") == 0.0

    def test_uniform_over_256_is_eight(self):

        data = bytes(range(256))
        assert metrics.shannon_entropy(data) == pytest.approx(8.0)

    def test_two_equal_symbols_is_one(self):

        data = b"abab" * 10
        assert metrics.shannon_entropy(data) == pytest.approx(1.0)

    def test_three_to_one_ratio(self):

        data = b"aaab"
        expected = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))
        assert metrics.shannon_entropy(data) == pytest.approx(expected)

    def test_large_input_entropy_in_expected_range(self):

        text = "The quick brown fox jumps over the lazy dog." * 20
        h = metrics.shannon_entropy(text.encode())
        assert 3.5 < h < 5.0


class TestCompressionRatio:
    def test_equal_sizes(self):
        assert metrics.compression_ratio(100, 100) == 1.0

    def test_compressed_half_size(self):
        assert metrics.compression_ratio(100, 50) == 2.0

    def test_compressed_larger(self):
        assert metrics.compression_ratio(4, 5) == 0.8

    def test_zero_compressed_returns_zero_not_inf(self):
        assert metrics.compression_ratio(10, 0) == 0.0


class TestAvgBitsPerSymbol:
    def test_basic(self):
        assert metrics.avg_bits_per_symbol(24, 3) == 8.0

    def test_empty_input(self):
        assert metrics.avg_bits_per_symbol(0, 0) == 0.0


class TestEncodingEfficiency:
    def test_perfect_is_one(self):
        assert metrics.encoding_efficiency(8.0, 8.0) == 1.0

    def test_half_efficient(self):
        assert metrics.encoding_efficiency(4.0, 8.0) == 0.5

    def test_clamped_to_one(self):
        assert metrics.encoding_efficiency(8.0000001, 8.0) <= 1.0

    def test_clamped_above_zero(self):
        assert metrics.encoding_efficiency(-0.0, 1.0) == 0.0

    def test_zero_avg_bits_returns_zero(self):
        assert metrics.encoding_efficiency(0.0, 0.0) == 0.0


class TestComputeAll:
    def test_has_all_six_keys(self):
        data = b"hello"
        raw, _, total_bits = vitter.compress("hello")
        m = metrics.compute_all(data, raw, total_bits)
        assert set(m.keys()) == {
            "original_bytes",
            "compressed_bytes",
            "compression_ratio",
            "entropy",
            "avg_bits_per_symbol",
            "encoding_efficiency",
        }

    def test_original_bytes_matches_input(self):
        text = "hello, world"
        raw, _, total_bits = vitter.compress(text)
        m = metrics.compute_all(text.encode(), raw, total_bits)
        assert m["original_bytes"] == len(text.encode())

    def test_compressed_bytes_matches_raw(self):
        text = "hello"
        raw, _, total_bits = vitter.compress(text)
        m = metrics.compute_all(text.encode(), raw, total_bits)
        assert m["compressed_bytes"] == len(raw)

    def test_long_repetitive_text_gives_high_ratio(self):
        text = "aaaaaa" * 200
        raw, _, total_bits = vitter.compress(text)
        m = metrics.compute_all(text.encode(), raw, total_bits)
        assert m["compression_ratio"] > 3.0

    def test_long_english_gives_high_efficiency(self):
        text = "The quick brown fox jumps over the lazy dog. " * 50
        raw, _, total_bits = vitter.compress(text)
        m = metrics.compute_all(text.encode(), raw, total_bits)
        assert m["encoding_efficiency"] > 0.85

    def test_values_are_rounded(self):
        text = "testing"
        raw, _, total_bits = vitter.compress(text)
        m = metrics.compute_all(text.encode(), raw, total_bits)
        for key in ("compression_ratio", "entropy", "avg_bits_per_symbol", "encoding_efficiency"):
            s = str(m[key])
            if "." in s:
                assert len(s.split(".")[1]) <= 6
