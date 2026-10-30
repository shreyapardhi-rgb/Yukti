"""Size and time comparison against simple baselines."""
import time
import zlib

from core import encode, decode, bits_to_bytes, MeruError, HEADER_BITS


def _avg_ms(fn, repeats):
    t = time.perf_counter()
    for _ in range(repeats):
        fn()
    return (time.perf_counter() - t) * 1000.0 / repeats


def compare(bits, block=8, repeats=20):
    raw_bits = len(bits)
    raw_bytes = bits_to_bytes(bits)
    enc = encode(bits, block)
    ok = decode(enc) == bits
    z_bits = len(zlib.compress(raw_bytes, 9)) * 8
    meru_bits = len(enc)
    best = best_block(bits)
    return {
        "input_bits": raw_bits,
        "raw_bits": raw_bits,
        "zlib_bits": z_bits,
        "meru_bits": meru_bits,
        "meru_payload_bits": meru_bits - HEADER_BITS,
        "block": block,
        "roundtrip_ok": ok,
        "ratio_vs_raw": round(meru_bits / raw_bits, 4) if raw_bits else None,
        "compresses": meru_bits < raw_bits,
        "compresses_without_header": (meru_bits - HEADER_BITS) < raw_bits,
        "time_ms": {
            "meru_encode": round(_avg_ms(lambda: encode(bits, block), repeats), 4),
            "meru_decode": round(_avg_ms(lambda: decode(enc), repeats), 4),
            "zlib_compress": round(_avg_ms(lambda: zlib.compress(raw_bytes, 9), repeats), 4),
            "zlib_decompress": round(_avg_ms(lambda: zlib.decompress(zlib.compress(raw_bytes, 9)), repeats), 4),
        },
        "best_block": best,
        "verdict": verdict(raw_bits, meru_bits),
    }


def best_block(bits, sizes=(2, 4, 8, 12, 16, 24, 32)):
    best = None
    for s in sizes:
        n = len(encode(bits, s))
        if best is None or n < best["meru_bits"]:
            best = {"block": s, "meru_bits": n}
    return best


def verdict(raw_bits, meru_bits):
    if raw_bits == 0:
        return "empty input"
    if meru_bits < raw_bits:
        return "COMPRESSES: %d bits -> %d bits (%.1f%% of original)" % (raw_bits, meru_bits, 100.0 * meru_bits / raw_bits)
    return "ONLY ENCODES: %d bits -> %d bits (%.1f%% of original, larger)" % (raw_bits, meru_bits, 100.0 * meru_bits / raw_bits)
