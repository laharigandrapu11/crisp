from __future__ import annotations

import random

import pytest

from huffman import bitpack


class TestRoundTrip:
    @pytest.mark.parametrize("length", list(range(31)))
    def test_zeros_round_trip(self, length):
        bits = "0" * length
        packed = bitpack.bits_to_bytes(bits)
        assert bitpack.bytes_to_bits(packed) == bits

    @pytest.mark.parametrize("length", list(range(31)))
    def test_ones_round_trip(self, length):
        bits = "1" * length
        packed = bitpack.bits_to_bytes(bits)
        assert bitpack.bytes_to_bits(packed) == bits

    @pytest.mark.parametrize("length", [5, 13, 21, 100, 500, 5000])
    def test_random_round_trip(self, length):
        random.seed(length)
        bits = "".join(random.choice("01") for _ in range(length))
        packed = bitpack.bits_to_bytes(bits)
        assert bitpack.bytes_to_bits(packed) == bits


class TestPadLength:
    def test_empty_input(self):
        # 0 data bits + 3-bit header = 3 bits total, pad to 8 = 5 pad bits.
        packed = bitpack.bits_to_bytes("")
        assert len(packed) == 1
        # First byte: 3-bit pad_length (=5) + 5 pad zeros
        # pad_length = 5 → binary "101", then "00000" padding
        assert packed[0] == 0b10100000
        # Round-trip recovers empty
        assert bitpack.bytes_to_bits(packed) == ""

    def test_five_bits(self):
        # 3 header + 5 data = 8, no padding needed (pad_length = 0).
        bits = "10101"
        packed = bitpack.bits_to_bytes(bits)
        assert len(packed) == 1
        # pad_length 0 → "000" prefix, then "10101"
        assert packed[0] == 0b00010101
        assert bitpack.bytes_to_bits(packed) == bits

    def test_exact_byte_boundary_avoids_bogus_pad(self):
        # The (8 - n % 8) % 8 form is what handles n % 8 == 0 correctly.
        # Naive `8 - n % 8` would give 8 pad bits instead of 0.
        # For 3-bit header case, total=8 when data=5. Already covered
        # above. For data=13: total=16, need 0 pad.
        bits = "0" * 13
        packed = bitpack.bits_to_bytes(bits)
        assert len(packed) == 2                       # exactly 2 bytes
        assert bitpack.bytes_to_bits(packed) == bits

    def test_one_bit_of_data(self):
        # 3 + 1 = 4, pad to 8 → pad_length = 4
        bits = "1"
        packed = bitpack.bits_to_bytes(bits)
        assert len(packed) == 1
        # "100" header + "1" data + "0000" pad = 10010000
        assert packed[0] == 0b10010000
        assert bitpack.bytes_to_bits(packed) == bits

    def test_seven_bits_of_data(self):
        # 3 + 7 = 10, pad to 16 → pad_length = 6
        bits = "1" * 7
        packed = bitpack.bits_to_bytes(bits)
        assert len(packed) == 2
        assert bitpack.bytes_to_bits(packed) == bits


class TestDecoderEdgeCases:
    def test_empty_bytes_returns_empty_string(self):
        assert bitpack.bytes_to_bits(b"") == ""


class TestPackedSize:
    @pytest.mark.parametrize("n_data_bits,expected_bytes", [
        (0, 1),    
        (5, 1),    
        (6, 2),    
        (13, 2),   
        (14, 3),   
        (21, 3),   
        (100, 13), 
    ])
    def test_packed_size_matches_formula(self, n_data_bits, expected_bytes):
        bits = "1" * n_data_bits
        packed = bitpack.bits_to_bytes(bits)
        assert len(packed) == expected_bytes
