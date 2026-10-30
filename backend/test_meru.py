import random
import unittest
import zlib

import core
from core import encode, decode, rank_block, unrank_block, MeruError
from bench import compare
from app import app


class TestPingalaVocabulary(unittest.TestCase):
    def test_prastara_counts(self):
        for n in range(0, 9):
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


if __name__ == "__main__":
    unittest.main()

