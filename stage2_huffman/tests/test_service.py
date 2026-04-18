from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from huffman.service.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_has_expected_fields(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["algorithm"] == "vitter-algorithm-v"


class TestCompress:
    def test_returns_200_on_valid_input(self, client):
        r = client.post("/compress", json={"text": "hello"})
        assert r.status_code == 200

    def test_response_has_payload_and_metrics(self, client):
        body = client.post("/compress", json={"text": "hello"}).json()
        assert "payload_base64" in body
        assert "metrics" in body

    def test_payload_is_valid_base64(self, client):
        body = client.post("/compress", json={"text": "hello"}).json()
        decoded = base64.b64decode(body["payload_base64"], validate=True)
        assert len(decoded) > 0

    def test_metrics_has_all_six_keys(self, client):
        body = client.post("/compress", json={"text": "hello"}).json()
        assert set(body["metrics"].keys()) == {
            "original_bytes",
            "compressed_bytes",
            "compression_ratio",
            "entropy",
            "avg_bits_per_symbol",
            "encoding_efficiency",
        }

    def test_metrics_types(self, client):
        body = client.post("/compress", json={"text": "hello"}).json()
        m = body["metrics"]
        assert isinstance(m["original_bytes"], int)
        assert isinstance(m["compressed_bytes"], int)
        assert isinstance(m["compression_ratio"], (int, float))
        assert isinstance(m["entropy"], (int, float))


class TestRoundTrip:
    @pytest.mark.parametrize("text", [
        "7",
        "7391",
        "8675309867530986753098675",
        "aaaaaaaaaaaaaaaaaaaa",
        "abracadabra",
        "The quick brown fox jumps over the lazy dog.",
        "Unicode: café, naïve, résumé, 日本語",
        "a" * 500,
    ])
    def test_compress_then_decompress_recovers_text(self, client, text):
        r1 = client.post("/compress", json={"text": text})
        assert r1.status_code == 200
        payload = r1.json()["payload_base64"]

        r2 = client.post("/decompress", json={"payload_base64": payload})
        assert r2.status_code == 200
        assert r2.json()["text"] == text


class TestCompressErrors:
    def test_empty_string_returns_400(self, client):
        r = client.post("/compress", json={"text": ""})
        assert r.status_code == 400
        assert "empty" in r.json()["error"].lower()

    def test_missing_text_returns_422(self, client):
        r = client.post("/compress", json={})
        assert r.status_code == 422

    def test_wrong_type_returns_422(self, client):
        r = client.post("/compress", json={"text": 123})
        assert r.status_code == 422


class TestDecompressErrors:
    def test_empty_payload_returns_400(self, client):
        r = client.post("/decompress", json={"payload_base64": ""})
        assert r.status_code == 400

    def test_malformed_base64_returns_400(self, client):
        r = client.post("/decompress", json={"payload_base64": "!!!not-base64!!!"})
        assert r.status_code == 400
        assert "base64" in r.json()["error"].lower()

    def test_random_bytes_dont_crash_the_server(self, client):
        garbage = base64.b64encode(b"\x00\xff\xaa\x55").decode()
        r = client.post("/decompress", json={"payload_base64": garbage})
        assert r.status_code in (200, 400)
        if r.status_code == 400:
            assert "error" in r.json()

    def test_missing_payload_returns_422(self, client):
        r = client.post("/decompress", json={})
        assert r.status_code == 422


class TestErrorEnvelope:
    def test_compress_empty_has_envelope(self, client):
        r = client.post("/compress", json={"text": ""})
        assert r.status_code == 400
        body = r.json()
        assert list(body.keys()) == ["error"]
        assert isinstance(body["error"], str)

    def test_decompress_bad_base64_has_envelope(self, client):
        r = client.post("/decompress", json={"payload_base64": "!!!"})
        assert r.status_code == 400
        body = r.json()
        assert list(body.keys()) == ["error"]


class TestStatelessness:
    def test_repeated_same_input_gives_same_output(self, client):
        text = "hello"
        outputs = set()
        for _ in range(5):
            r = client.post("/compress", json={"text": text})
            outputs.add(r.json()["payload_base64"])
        assert len(outputs) == 1, \
            f"service leaking state — got {len(outputs)} different outputs: {outputs}"

    def test_interleaved_requests_dont_interfere(self, client):
        a1 = client.post("/compress", json={"text": "aaaaa"}).json()["payload_base64"]
        _  = client.post("/compress", json={"text": "zzzzz"}).json()["payload_base64"]
        a2 = client.post("/compress", json={"text": "aaaaa"}).json()["payload_base64"]
        assert a1 == a2


class TestInspectionFields:
    def test_code_map_is_present(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        assert "code_map" in body
        assert isinstance(body["code_map"], dict)

    def test_code_map_contains_every_seen_symbol(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        for ch in "abrcd":
            assert ch in body["code_map"], f"missing {ch!r} in code_map"
        assert "NYT" in body["code_map"]

    def test_code_map_values_are_bit_strings(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        for sym, code in body["code_map"].items():
            assert isinstance(code, str)
            assert all(c in "01" for c in code), \
                f"code for {sym!r} contains non-bit characters: {code!r}"

    def test_code_map_most_frequent_gets_shortest_code(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        codes = body["code_map"]
        a_len = len(codes["a"])
        for sym in ("b", "r", "c", "d"):
            assert len(codes[sym]) >= a_len, \
                f"{sym!r} (freq<5) has shorter code than 'a' (freq=5)"

    def test_tree_structure_is_present(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        assert "tree_structure" in body
        assert isinstance(body["tree_structure"], dict)

    def test_tree_structure_root_shape(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        root = body["tree_structure"]
        assert root["name"] == "root"
        assert "weight" in root
        assert "children" in root
        assert len(root["children"]) == 2

    def test_tree_root_weight_equals_input_length(self, client):
        body = client.post("/compress", json={"text": "abracadabra"}).json()
        assert body["tree_structure"]["weight"] == 11

    def test_non_printable_bytes_use_hex_escape(self, client):
        body = client.post("/compress", json={"text": "a\x00b"}).json()
        keys = body["code_map"].keys()
        assert any("\\x" in k or k == "\\x00" for k in keys) or "\x00" in keys

    def test_single_symbol_input_has_minimal_tree(self, client):
        body = client.post("/compress", json={"text": "a"}).json()
        root = body["tree_structure"]
        assert root["name"] == "root"
        assert len(root["children"]) == 2
        child_names = {c["name"] for c in root["children"]}
        assert child_names == {"NYT", "a"}
