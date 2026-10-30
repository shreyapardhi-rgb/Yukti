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


if __name__ == "__main__":
    unittest.main()
