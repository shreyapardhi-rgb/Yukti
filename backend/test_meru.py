import json
import os
import random
import shutil
import subprocess
import unittest
import zlib

import core
from app import app
from bench import compare
from core import MeruError, decode, encode, rank_block, unrank_block
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPingalaVocabulary(unittest.TestCase):
    def test_prastara_counts(self):
        for n in range(9):
            self.assertEqual(len(core.prastara(n)), 2 ** n)
        self.assertEqual(core.prastara(2), ["00", "01", "10", "11"])

    def test_meru_rows(self):
        rows = core.meru_rows(6)
        self.assertEqual(rows[5], [1, 5, 10, 10, 5, 1])
        for r in rows:
            self.assertEqual(sum(r), 2 ** (len(r) - 1))

    def test_uddishta_nashta_inverse(self):
        for n in range(1, 9):
            for i in range(2 ** n):
                self.assertEqual(core.uddishta(core.nashta(n, i)), i)

    def test_matra_vritta_is_fibonacci(self):
        counts = [len(core.matra_vritta(m)) for m in range(1, 9)]
        self.assertEqual(counts, [1, 2, 3, 5, 8, 13, 21, 34])


class TestBlockRank(unittest.TestCase):
    def test_saket_ranks_match_hand_calculation(self):
        expected = {"01110011": (5, 15), "01100001": (3, 30), "01101011": (5, 12),
                    "01100101": (4, 26), "01110100": (4, 33)}
        for blk, kr in expected.items():
            self.assertEqual(rank_block(blk), kr)

    def test_all_8bit_blocks_roundtrip(self):
        for v in range(256):
            blk = format(v, "08b")
            k, r = rank_block(blk)
            self.assertEqual(unrank_block(8, k, r), blk)

    def test_ranks_are_unique_inside_group(self):
        seen = set()
        for v in range(256):
            seen.add(rank_block(format(v, "08b")))
        self.assertEqual(len(seen), 256)

    def test_bad_k_and_rank(self):
        with self.assertRaises(MeruError):
            unrank_block(8, 9, 0)
        with self.assertRaises(MeruError):
            unrank_block(8, 5, 56)


class TestStreamCodec(unittest.TestCase):
    def test_saket_golden(self):
        bits = core.text_to_bits("saket")
        enc = encode(bits, 8)
        self.assertEqual(len(bits), 40)
        self.assertEqual(len(enc), 92)
        self.assertEqual(enc[40:50], "0101001111")  # k=5 (0101), rank 15 (001111)
        self.assertEqual(core.bits_to_text(decode(enc)), "saket")

    def test_empty_input(self):
        self.assertEqual(decode(encode("", 8)), "")

    def test_roundtrip_random_many_block_sizes(self):
        rnd = random.Random(7)
        for _ in range(300):
            n = rnd.randint(0, 200)
            bits = "".join(rnd.choice("01") for _ in range(n))
            b = rnd.choice([1, 2, 3, 5, 8, 13, 16, 31, 32, 64])
            self.assertEqual(decode(encode(bits, b)), bits)

    def test_unicode_text_roundtrip(self):
        for s in ["hello", "संस्कृत पिङ्गल", "naïve café 😀", "a"]:
            bits = core.text_to_bits(s)
            self.assertEqual(core.bits_to_text(decode(encode(bits, 8))), s)

    def test_corrupt_streams_raise(self):
        enc = encode(core.text_to_bits("abc"), 8)
        for bad in [enc[:-3], enc + "0", enc[:20], ""]:
            with self.assertRaises(MeruError):
                decode(bad)
        with self.assertRaises(MeruError):
            encode("012", 8)
        with self.assertRaises(MeruError):
            encode("0101", 0)

    def test_padding_is_trimmed(self):
        self.assertEqual(decode(encode("10101", 8)), "10101")


class TestVersionedContainer(unittest.TestCase):
    def test_pack_unpack_roundtrip(self):
        bits = core.text_to_bits("Yukti Pingala Codec v2")
        container = core.pack_container(bits, block=12)
        self.assertTrue(container.startswith(core.CONTAINER_MAGIC))
        self.assertEqual(container[4], 2)
        decoded, meta = core.unpack_container(container)
        self.assertEqual(decoded, bits)
        self.assertTrue(meta["crc_verified"])
        self.assertEqual(meta["version"], 2)
        self.assertEqual(core.bits_to_text(decoded), "Yukti Pingala Codec v2")

    def test_crc_catches_corruption(self):
        bits = core.text_to_bits("Critical payload data")
        container = bytearray(core.pack_container(bits, block=8))
        # Corrupt CRC32 bytes directly
        corrupted_crc = bytearray(container)
        corrupted_crc[15] ^= 0xFF
        with self.assertRaises(core.MeruError) as ctx:
            core.unpack_container(bytes(corrupted_crc))
        self.assertEqual(ctx.exception.code, "CHECKSUM_MISMATCH")

        # Corrupt payload byte
        corrupted_payload = bytearray(container)
        corrupted_payload[core.CONTAINER_HEADER_SIZE + 1] ^= 0x01
        with self.assertRaises(core.MeruError):
            core.unpack_container(bytes(corrupted_payload))

    def test_legacy_v1_autodetect(self):
        bits = "01011001" * 4
        legacy_stream = encode(bits, 8)
        decoded, meta = core.unpack_container(legacy_stream)
        self.assertEqual(decoded, bits)
        self.assertEqual(meta["version"], 1)
        self.assertFalse(meta["crc_verified"])


class TestHonestCompression(unittest.TestCase):
    def test_text_does_not_compress(self):
        r = compare(core.text_to_bits("saket"), 8, repeats=2)
        self.assertFalse(r["compresses"])
        self.assertTrue(r["roundtrip_ok"])

    def test_sparse_data_compresses(self):
        bits = core.make_preset("sparse", 4096, 1)
        r = compare(bits, 16, repeats=2)
        self.assertTrue(r["compresses"])
        self.assertLess(r["meru_bits"], r["raw_bits"])

    def test_dense_data_compresses_too(self):
        bits = core.make_preset("mostly_ones", 4096, 1)
        self.assertTrue(compare(bits, 16, repeats=2)["compresses"])

    def test_random_data_does_not_compress(self):
        bits = core.make_preset("balanced", 4096, 1)
        self.assertFalse(compare(bits, 8, repeats=2)["compresses"])

    def test_zlib_reference(self):
        raw = core.bits_to_bytes(core.make_preset("all_zeros", 800))
        self.assertEqual(zlib.decompress(zlib.compress(raw, 9)), raw)


class TestMulberry(unittest.TestCase):
    def test_deterministic(self):
        a, b = core.mulberry32(123), core.mulberry32(123)
        self.assertEqual([a() for _ in range(5)], [b() for _ in range(5)])

    def test_range(self):
        r = core.mulberry32(1)
        for _ in range(1000):
            self.assertTrue(0.0 <= r() < 1.0)

    def test_presets_density(self):
        bits = core.make_preset("sparse", 5000, 9)
        self.assertLess(bits.count("1") / 5000, 0.08)
        self.assertEqual(core.make_preset("all_zeros", 50).count("1"), 0)


class TestApi(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_health(self):
        self.assertEqual(self.c.get("/api/health").get_json()["status"], "ok")

    def test_encode_decode_roundtrip(self):
        r = self.c.post("/api/encode", json={"text": "saket", "block": 8}).get_json()
        self.assertEqual(r["encoded_bits"], 92)
        self.assertEqual(r["blocks"][0]["k"], 5)
        d = self.c.post("/api/decode", json={"encoded": r["encoded"], "as_text": True}).get_json()
        self.assertEqual(d["text"], "saket")

    def test_compare(self):
        r = self.c.post("/api/compare", json={"text": "saket", "block": 8}).get_json()
        self.assertFalse(r["compresses"])
        self.assertIn("ONLY ENCODES", r["verdict"])

    def test_errors_are_400(self):
        self.assertEqual(self.c.post("/api/encode", json={"bits": "12"}).status_code, 400)
        self.assertEqual(self.c.post("/api/encode", json={"bits": "01", "block": 99}).status_code, 400)
        self.assertEqual(self.c.post("/api/decode", json={"encoded": "01"}).status_code, 400)
        self.assertEqual(self.c.post("/api/encode", data="x").status_code, 400)
        self.assertEqual(self.c.get("/api/nope").status_code, 404)

    def test_pattern_endpoints(self):
        self.assertEqual(self.c.get("/api/prastara?n=3").get_json()["count"], 8)
        self.assertEqual(self.c.get("/api/meru?rows=5").get_json()["rows"][4], [1, 4, 6, 4, 1])
        self.assertEqual(self.c.get("/api/matra?m=5").get_json()["count"], 8)
        self.assertEqual(self.c.get("/api/nashta?n=3&index=5").get_json()["pattern"], "101")
        self.assertEqual(self.c.get("/api/uddishta?pattern=101").get_json()["index"], 5)

    def test_generate(self):
        r = self.c.post("/api/generate", json={"preset": "sparse", "length": 100, "seed": 3}).get_json()
        self.assertEqual(r["length"], 100)

    def test_pack_unpack_api(self):
        pack_res = self.c.post("/api/pack", json={"text": "Vedic Codec", "block": 8}).get_json()
        self.assertEqual(pack_res["version"], 2)
        self.assertIn("container_base64", pack_res)

        unpack_res = self.c.post("/api/unpack", json={"container_base64": pack_res["container_base64"], "as_text": True}).get_json()
        self.assertEqual(unpack_res["text"], "Vedic Codec")
        self.assertTrue(unpack_res["crc_verified"])


class TestDecodeSafetyAndFuzz(unittest.TestCase):
    def test_oversized_claimed_length_fails_instantly(self):
        # 40-bit header claiming 4 billion bits
        four_billion = format(4_000_000_000, "032b") + format(8, "08b")
        with self.assertRaises(core.MeruError) as ctx:
            decode(four_billion)
        self.assertEqual(ctx.exception.code, "CLAIMED_LENGTH_TOO_LARGE")

    def test_truncated_header_claims_rejected_pre_allocation(self):
        # Claiming 1,000 bits with only 45 bits in stream
        claimed_stream = format(1000, "032b") + format(8, "08b") + "01010"
        with self.assertRaises(core.MeruError) as ctx:
            decode(claimed_stream)
        self.assertEqual(ctx.exception.code, "STREAM_TRUNCATED")

    def test_fuzz_random_garbage_never_crashes(self):
        rnd = random.Random(1337)
        for _ in range(500):
            # Generate random bit length up to 256
            length = rnd.randint(0, 256)
            garbage_bits = "".join(rnd.choice("01") for _ in range(length))
            try:
                res = decode(garbage_bits)
                self.assertIsInstance(res, str)
            except core.MeruError:
                # Valid controlled rejection
                pass
            except Exception as e:
                self.fail(f"decode() raised unexpected exception {type(e)} on input: {garbage_bits}")

    def test_fuzz_single_bit_flips_on_valid_stream(self):
        rnd = random.Random(42)
        sample = core.make_preset("sparse", 256, 1)
        valid_stream = encode(sample, 8)
        for _ in range(200):
            idx = rnd.randint(0, len(valid_stream) - 1)
            flipped_bit = "0" if valid_stream[idx] == "1" else "1"
            mutated = valid_stream[:idx] + flipped_bit + valid_stream[idx + 1:]
            try:
                res = decode(mutated)
                self.assertIsInstance(res, str)
            except core.MeruError:
                pass
            except Exception as e:
                self.fail(f"decode() raised unexpected exception {type(e)} on mutated stream at index {idx}")


class TestByteFastPaths(unittest.TestCase):
    def test_bytes_roundtrip(self):
        data = b"Hello Yukti and Pingala 12345!"
        encoded_bits = core.encode_bytes(data, 8)
        decoded_bytes = core.decode_bytes(encoded_bits)
        self.assertEqual(decoded_bytes, data)

    def test_bytes_empty(self):
        self.assertEqual(core.decode_bytes(core.encode_bytes(b"", 8)), b"")

    def test_bytes_various_block_sizes(self):
        data = b"\x00\x00\xff\xaa\x55\x00\x11"
        for block in [1, 4, 8, 16, 32, 64]:
            enc = core.encode_bytes(data, block)
            dec = core.decode_bytes(enc)
            self.assertEqual(dec, data, f"Failed roundtrip for block {block}")


class TestSection5Endpoints(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_info_endpoint(self):
        r = self.c.get("/api/info")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["version"], "2.0.0")
        self.assertIn("limits", data)
        self.assertIn("header_layout", data)
        self.assertIn("endpoints", data)

    def test_docs_endpoint(self):
        r = self.c.get("/api/docs")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Yukti", r.data)

    def test_trace_endpoint(self):
        r = self.c.post("/api/trace", json={"bits": "101001", "block": 6})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["block_size"], 6)
        self.assertEqual(len(data["blocks"]), 1)
        blk = data["blocks"][0]
        self.assertEqual(blk["k"], 3)
        self.assertIn("binomial_terms", blk)
        self.assertEqual(len(blk["binomial_terms"]), 6)
        self.assertIn("running_sum", blk)

    def test_sweep_endpoint(self):
        r = self.c.post("/api/sweep", json={"density": 0.05, "length": 512, "step": 8})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["density"], 0.05)
        self.assertGreater(len(data["points"]), 0)
        first_pt = data["points"][0]
        self.assertIn("block", first_pt)
        self.assertIn("ratio", first_pt)
        self.assertIn("compresses", first_pt)

    def test_analyze_endpoint(self):
        # All zeros has 0 entropy
        zeros_res = self.c.post("/api/analyze", json={"bits": "0" * 100, "block": 8}).get_json()
        self.assertEqual(zeros_res["shannon_entropy_per_bit"], 0.0)
        self.assertEqual(zeros_res["theoretical_min_bits"], 0)

        # Balanced bits has high entropy
        rnd_bits = core.make_preset("balanced", 500, 42)
        bal_res = self.c.post("/api/analyze", json={"bits": rnd_bits, "block": 8}).get_json()
        self.assertGreater(bal_res["shannon_entropy_per_bit"], 0.9)
        self.assertIn("explanation", bal_res)

    def test_corrupt_endpoint(self):
        sample = core.make_preset("sparse", 64, 1)
        enc = core.encode(sample, 8)
        # Flip bit inside the stream
        r = self.c.post("/api/corrupt", json={"encoded": enc, "position": 10})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["flipped_position"], 10)
        self.assertIn("flipped_bit", data)
        self.assertIn("success", data)

    def test_new_endpoints_validation_errors(self):
        # /api/corrupt out of bounds
        r = self.c.post("/api/corrupt", json={"encoded": "101", "position": 99})
        self.assertEqual(r.status_code, 400)

        # /api/sweep invalid density
        r = self.c.post("/api/sweep", json={"density": 1.5})
        self.assertEqual(r.status_code, 400)

        # /api/sweep negative length
        r = self.c.post("/api/sweep", json={"length": -10})
        self.assertEqual(r.status_code, 400)

        # /api/trace invalid block
        r = self.c.post("/api/trace", json={"bits": "101", "block": 100})
        self.assertEqual(r.status_code, 400)


class TestGoldenVectors(unittest.TestCase):
    def setUp(self):
        golden_path = os.path.join(os.path.dirname(__file__), "..", "tests", "golden.json")
        with open(golden_path, "r", encoding="utf-8") as f:
            self.golden = json.load(f)

    def test_all_golden_vectors_python(self):
        for v in self.golden:
            raw_bits = v["raw_bits"]
            block = v["block"]
            expected_enc = v["encoded"]

            enc = encode(raw_bits, block)
            self.assertEqual(enc, expected_enc, f"Encoding mismatch on {v['name']}")

            dec = decode(enc)
            self.assertEqual(dec, raw_bits, f"Decoding mismatch on {v['name']}")

    def test_devanagari_golden_roundtrip(self):
        dev = next(v for v in self.golden if v["name"] == "devanagari_text")
        dec_bits = decode(dev["encoded"])
        text = core.bits_to_text(dec_bits)
        self.assertEqual(text, dev["text"])

    def test_block_64_golden_roundtrip(self):
        b64 = next(v for v in self.golden if v["name"] == "block_64_alternating")
        self.assertEqual(decode(b64["encoded"]), b64["raw_bits"])


class TestFrontendParity(unittest.TestCase):
    def test_1000_random_vectors_match_js_codec(self):
        node_path = shutil.which("node")
        if not node_path:
            self.skipTest("node.js not available on system PATH; skipping cross-language parity test")

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        rnd = core.mulberry32(2026)

        cases = []
        for i in range(1000):
            # lengths from 0 to 200 bits
            length = int(rnd() * 200)
            block = int(rnd() * 64) + 1
            density = rnd()
            bits = "".join("1" if rnd() < density else "0" for _ in range(length))
            py_enc = encode(bits, block)
            cases.append({
                "bits": bits,
                "block": block,
                "py_encoded": py_enc
            })

        cases_path = os.path.join(repo_root, "tests", "random_cases.json")
        with open(cases_path, "w", encoding="utf-8") as f:
            json.dump(cases, f)

        try:
            parity_script = os.path.join(repo_root, "tests", "parity_test.js")
            res = subprocess.run([node_path, parity_script], cwd=repo_root, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node parity test failed with stderr:\n{res.stderr}\nstdout:\n{res.stdout}")
            self.assertIn("PASS: Verified 1000/1000 random vectors", res.stdout)
        finally:
            if os.path.exists(cases_path):
                os.remove(cases_path)


class TestHypothesisProperties(unittest.TestCase):
    @settings(max_examples=50, deadline=None)
    @given(st.text(alphabet="01", min_size=0, max_size=200), st.integers(min_value=1, max_value=64))
    def test_hypothesis_roundtrip(self, bits, block):
        enc = encode(bits, block)
        dec = decode(enc)
        self.assertEqual(dec, bits)

    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=1, max_value=64), st.data())
    def test_hypothesis_rank_unrank_inverse(self, n, data):
        k = data.draw(st.integers(min_value=0, max_value=n))
        limit = core.fast_comb(n, k)
        r = data.draw(st.integers(min_value=0, max_value=limit - 1)) if limit > 0 else 0
        pattern = unrank_block(n, k, r)
        self.assertEqual(len(pattern), n)
        self.assertEqual(pattern.count("1"), k)
        calc_k, calc_r = rank_block(pattern)
        self.assertEqual((calc_k, calc_r), (k, r))

    @settings(max_examples=40, deadline=None)
    @given(st.text(alphabet="01", min_size=1, max_size=150), st.integers(min_value=1, max_value=32))
    def test_hypothesis_size_formula_exactness(self, bits, block):
        enc, rows = encode(bits, block, detail=True)
        expected_size = core.HEADER_BITS + sum(r["bits_used"] for r in rows)
        self.assertEqual(len(enc), expected_size)

    @settings(max_examples=60, deadline=None)
    @given(st.text(alphabet="01", min_size=0, max_size=200))
    def test_hypothesis_decode_safety(self, stream):
        try:
            res = decode(stream)
            self.assertIsInstance(res, str)
        except MeruError:
            pass


class TestExhaustiveBlocks(unittest.TestCase):
    def test_exhaustive_all_blocks_up_to_12_bits(self):
        # Exhaustively check all 8,190 block patterns from block 1 to 12
        for n in range(1, 13):
            for i in range(1 << n):
                pattern = format(i, f"0{n}b")
                k, r = rank_block(pattern)
                reconstructed = unrank_block(n, k, r)
                self.assertEqual(reconstructed, pattern)

    def test_block_sizes_13_to_16_boundary_and_samples(self):
        rnd = random.Random(999)
        for n in range(13, 17):
            # Boundary cases: all 0s, all 1s, single 1 at each position
            all_zeros = "0" * n
            self.assertEqual(unrank_block(n, *rank_block(all_zeros)), all_zeros)

            all_ones = "1" * n
            self.assertEqual(unrank_block(n, *rank_block(all_ones)), all_ones)

            for pos in range(n):
                single_one = "0" * pos + "1" + "0" * (n - pos - 1)
                self.assertEqual(unrank_block(n, *rank_block(single_one)), single_one)

            # Random sample of 100 patterns
            for _ in range(100):
                pat = "".join(rnd.choice("01") for _ in range(n))
                self.assertEqual(unrank_block(n, *rank_block(pat)), pat)


class TestMutationSanity(unittest.TestCase):
    def test_off_by_one_mutation_breaks_codec(self):
        orig_rank_block = core.rank_block
        try:
            # Introduce intentional off-by-one mutation in rank_block
            def broken_rank_block(block):
                k, r = orig_rank_block(block)
                return k, r + 1

            core.rank_block = broken_rank_block

            # Verify that encode-decode roundtrip FAILS with the mutant
            test_bits = "10011010"
            failed = False
            try:
                mutated_stream = encode(test_bits, block=8)
                decoded = decode(mutated_stream)
                if decoded != test_bits:
                    failed = True
            except MeruError:
                failed = True

            self.assertTrue(failed, "Mutation sanity test failed: off-by-one bug was not caught!")
        finally:
            core.rank_block = orig_rank_block


class TestApiErrorsExhaustive(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_404_not_found(self):
        r = self.c.get("/api/nonexistent_route")
        self.assertEqual(r.status_code, 404)
        data = r.get_json()
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_405_method_not_allowed(self):
        r = self.c.get("/api/encode")
        self.assertEqual(r.status_code, 405)
        data = r.get_json()
        self.assertEqual(data["error"]["code"], "METHOD_NOT_ALLOWED")

        r2 = self.c.post("/api/info", json={})
        self.assertEqual(r2.status_code, 405)
        self.assertEqual(r2.get_json()["error"]["code"], "METHOD_NOT_ALLOWED")

    def test_400_bad_json_or_types(self):
        # Non-JSON data
        r = self.c.post("/api/encode", data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_JSON")

        # Missing input
        r = self.c.post("/api/encode", json={})
        self.assertEqual(r.status_code, 400)

        # Unexpected fields
        r = self.c.post("/api/encode", json={"text": "hello", "unknown_field": 123})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "UNEXPECTED_FIELD")

        # Boolean passed as integer
        r = self.c.post("/api/generate", json={"preset": "sparse", "length": True})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_TYPE")

        # NaN/Infinity passed to float
        r = self.c.post("/api/sweep", json={"density": "NaN"})
        self.assertEqual(r.status_code, 400)

        # Invalid pattern for uddishta
        r = self.c.get("/api/uddishta?pattern=012")
        self.assertEqual(r.status_code, 400)

        # Missing param for nashta
        r = self.c.get("/api/nashta?n=4")
        self.assertEqual(r.status_code, 400)

    def test_all_api_endpoints_respond_200(self):
        # Check every GET endpoint
        self.assertEqual(self.c.get("/api/health").status_code, 200)
        self.assertEqual(self.c.get("/api/info").status_code, 200)
        self.assertEqual(self.c.get("/api/docs").status_code, 200)
        self.assertEqual(self.c.get("/api/prastara?n=4").status_code, 200)
        self.assertEqual(self.c.get("/api/meru?rows=5").status_code, 200)
        self.assertEqual(self.c.get("/api/matra?m=4").status_code, 200)
        self.assertEqual(self.c.get("/api/nashta?n=4&index=5").status_code, 200)
        self.assertEqual(self.c.get("/api/uddishta?pattern=0101").status_code, 200)
        self.assertEqual(self.c.get("/api/presets").status_code, 200)


class TestGranularUnits(unittest.TestCase):
    def test_fast_comb_properties(self):
        self.assertEqual(core.fast_comb(0, 0), 1)
        self.assertEqual(core.fast_comb(5, 0), 1)
        self.assertEqual(core.fast_comb(5, 5), 1)
        self.assertEqual(core.fast_comb(5, 2), 10)
        self.assertEqual(core.fast_comb(5, 6), 0)
        self.assertEqual(core.fast_comb(5, -1), 0)
        self.assertEqual(core.fast_comb(64, 32), 1832624140942590534)

    def test_k_width_powers(self):
        self.assertEqual(core.k_width(1), 1)
        self.assertEqual(core.k_width(2), 2)
        self.assertEqual(core.k_width(3), 2)
        self.assertEqual(core.k_width(4), 3)
        self.assertEqual(core.k_width(8), 4)
        self.assertEqual(core.k_width(16), 5)
        self.assertEqual(core.k_width(64), 7)

    def test_rank_width_values(self):
        self.assertEqual(core.rank_width(4, 0), 0)
        self.assertEqual(core.rank_width(4, 4), 0)
        self.assertEqual(core.rank_width(4, 1), 2)
        self.assertEqual(core.rank_width(4, 2), 3)

    def test_text_to_bits_utf8(self):
        s = "Hello World"
        b = core.text_to_bits(s)
        self.assertEqual(len(b), len(s) * 8)
        self.assertEqual(core.bits_to_text(b), s)

    def test_text_to_bits_invalid_type(self):
        with self.assertRaises(core.MeruError):
            core.text_to_bits(123)

    def test_bits_to_text_non_multiple_of_8(self):
        with self.assertRaises(core.MeruError):
            core.bits_to_text("10101")

    def test_bits_to_bytes_padding_and_roundtrip(self):
        bits = "101"
        b = core.bits_to_bytes(bits)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0], 0b10100000)

    def test_encode_block_size_1(self):
        bits = "1011001"
        enc = encode(bits, block=1)
        self.assertEqual(decode(enc), bits)

    def test_encode_block_size_64(self):
        bits = "01" * 32
        enc = encode(bits, block=64)
        self.assertEqual(decode(enc), bits)

    def test_encode_empty_bitstring(self):
        enc = encode("", block=8)
        self.assertEqual(decode(enc), "")

    def test_encode_all_zeros_various_lengths(self):
        for length in [1, 7, 8, 9, 15, 16, 17, 63, 64, 65]:
            bits = "0" * length
            self.assertEqual(decode(encode(bits, block=8)), bits)

    def test_encode_all_ones_various_lengths(self):
        for length in [1, 7, 8, 9, 15, 16, 17, 63, 64, 65]:
            bits = "1" * length
            self.assertEqual(decode(encode(bits, block=8)), bits)

    def test_compare_various_presets(self):
        for preset in ["sparse", "all_zeros", "mostly_ones"]:
            bits = core.make_preset(preset, 1024, 1)
            res = compare(bits, block=8)
            self.assertTrue(res["compresses"], f"Preset {preset} should compress")

    def test_compare_balanced_expands(self):
        bits = core.make_preset("balanced", 1024, 1)
        res = compare(bits, block=8)
        self.assertFalse(res["compresses"], "Balanced preset should expand")

    def test_trace_binomial_terms_sum_equals_rank(self):
        block = "10110"
        t = core.trace_block(block)
        sum_vals = sum(item["value"] for item in t["binomial_terms"])
        self.assertEqual(sum_vals, t["rank"])

    def test_sweep_bounds(self):
        with self.assertRaises(core.MeruError):
            core.sweep_ratios(density=-0.1)
        with self.assertRaises(core.MeruError):
            core.sweep_ratios(length=5)

    def test_calculate_entropy_bounds(self):
        res_zero = core.calculate_entropy("00000000", block=8)
        self.assertEqual(res_zero["shannon_entropy_per_bit"], 0.0)
        res_one = core.calculate_entropy("11111111", block=8)
        self.assertEqual(res_one["shannon_entropy_per_bit"], 0.0)

    def test_cors_headers(self):
        c = app.test_client()
        r = c.get("/api/health", headers={"Origin": "http://localhost:5000"})
        self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "http://localhost:5000")

    def test_prastara_invalid_n_out_of_range(self):
        c = app.test_client()
        r = c.get("/api/prastara?n=99")
        self.assertEqual(r.status_code, 400)

    def test_matra_invalid_m_out_of_range(self):
        c = app.test_client()
        r = c.get("/api/matra?m=99")
        self.assertEqual(r.status_code, 400)

    def test_meru_invalid_rows_out_of_range(self):
        c = app.test_client()
        r = c.get("/api/meru?rows=999")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()




