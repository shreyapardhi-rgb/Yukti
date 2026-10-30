"""Size and time comparison against simple baselines."""
import bz2
from functools import lru_cache
import gzip
import lzma
import os
import time
import zlib

from core import (
    encode,
    decode,
    bits_to_bytes,
    make_preset,
    HEADER_BITS,
)


def _timed_median_ms(fn, target_time_ms=60.0, min_repeats=3, max_repeats=30):
    """Executes a function adaptively with warmup, reporting median time in milliseconds.

    Total duration is capped around target_time_ms to keep API responses responsive.
    """
    # 1. Warm-up
    try:
        fn()
    except Exception:
        pass

    samples = []
    t_start = time.perf_counter()
    while len(samples) < min_repeats or ((time.perf_counter() - t_start) * 1000.0 < target_time_ms and len(samples) < max_repeats):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)

    samples.sort()
    mid = len(samples) // 2
    median = samples[mid] if len(samples) % 2 == 1 else (samples[mid - 1] + samples[mid]) / 2.0
    return median


def run_length_bits(bits):
    """Simple baseline Run-Length Encoding (RLE) bitstream model.

    Encodes consecutive runs of 0s and 1s as (count: 15b, bit: 1b) = 16 bits per run.
    """
    if not bits:
        return 0
    runs = 1
    current = bits[0]
    for b in bits[1:]:
        if b != current:
            runs += 1
            current = b
    return runs * 16


@lru_cache(maxsize=128)
def _best_block_cached(bits, max_block_size):
    candidate_sizes = [s for s in (2, 4, 8, 12, 16, 24, 32, 64) if s <= max_block_size]
    if not candidate_sizes:
        candidate_sizes = [2]
    best = None
    for s in candidate_sizes:
        n = len(encode(bits, s))
        if best is None or n < best["meru_bits"]:
            best = {"block": s, "meru_bits": n}
    return best


def best_block(bits, sizes=(2, 4, 8, 12, 16, 24, 32)):
    """Finds block size yielding minimal encoded bitstream, with LRU caching."""
    if not bits:
        return {"block": 8, "meru_bits": HEADER_BITS}
    if tuple(sizes) == (2, 4, 8, 12, 16, 24, 32):
        return _best_block_cached(bits, max(len(bits), 2))
    best = None
    for s in sizes:
        if s > max(len(bits), 2) and s > 8:
            continue
        n = len(encode(bits, s))
        if best is None or n < best["meru_bits"]:
            best = {"block": s, "meru_bits": n}
    return best or {"block": 8, "meru_bits": len(encode(bits, 8))}


def compare(bits, block=8, repeats=20):
    raw_bits = len(bits)
    raw_bytes = bits_to_bytes(bits)
    enc = encode(bits, block)
    ok = decode(enc) == bits
    meru_bits = len(enc)

    # Standard baselines
    z_compressed = zlib.compress(raw_bytes, 9)
    z_bits = len(z_compressed) * 8
    gzip_bits = len(gzip.compress(raw_bytes, compresslevel=9)) * 8
    bz2_bits = len(bz2.compress(raw_bytes, compresslevel=9)) * 8
    lzma_bits = len(lzma.compress(raw_bytes)) * 8
    rle_bits = run_length_bits(bits)

    best = best_block(bits)
    amortized_overhead = round(HEADER_BITS / raw_bits, 4) if raw_bits else None
    ratio_no_header = round((meru_bits - HEADER_BITS) / raw_bits, 4) if raw_bits else None

    # Adaptive median timings without recompression inside decompression
    t_enc = _timed_median_ms(lambda: encode(bits, block))
    t_dec = _timed_median_ms(lambda: decode(enc))
    t_z_enc = _timed_median_ms(lambda: zlib.compress(raw_bytes, 9))
    t_z_dec = _timed_median_ms(lambda: zlib.decompress(z_compressed))

    return {
        "input_bits": raw_bits,
        "raw_bits": raw_bits,
        "zlib_bits": z_bits,
        "gzip_bits": gzip_bits,
        "bz2_bits": bz2_bits,
        "lzma_bits": lzma_bits,
        "rle_bits": rle_bits,
        "meru_bits": meru_bits,
        "meru_payload_bits": meru_bits - HEADER_BITS,
        "block": block,
        "roundtrip_ok": ok,
        "ratio_vs_raw": round(meru_bits / raw_bits, 4) if raw_bits else None,
        "ratio_without_header": ratio_no_header,
        "header_amortized_overhead": amortized_overhead,
        "compresses": meru_bits < raw_bits,
        "compresses_without_header": (meru_bits - HEADER_BITS) < raw_bits,
        "time_ms": {
            "meru_encode": round(t_enc, 4),
            "meru_decode": round(t_dec, 4),
            "zlib_compress": round(t_z_enc, 4),
            "zlib_decompress": round(t_z_dec, 4),
        },
        "best_block": best,
        "verdict": verdict(raw_bits, meru_bits),
    }


def verdict(raw_bits, meru_bits):
    if raw_bits == 0:
        return "empty input"
    if meru_bits < raw_bits:
        return "COMPRESSES: %d bits -> %d bits (%.1f%% of original)" % (raw_bits, meru_bits, 100.0 * meru_bits / raw_bits)
    return "ONLY ENCODES: %d bits -> %d bits (%.1f%% of original, larger)" % (raw_bits, meru_bits, 100.0 * meru_bits / raw_bits)


def run_benchmark_suite():
    """Generates a comprehensive scientific comparison table across sizes and densities."""
    configs = [
        ("1 Kbit (1,024 bits)", 1024),
        ("64 Kbit (65,536 bits)", 65536),
        ("1 Mbit (1,048,576 bits)", 1048576),
    ]
    densities = [
        ("Sparse (5% ones)", "sparse"),
        ("Dense (95% ones)", "mostly_ones"),
        ("Random (50% ones)", "balanced"),
        ("All Zeros", "all_zeros"),
    ]

    lines = []
    lines.append("# Yukti Codec Benchmark Suite")
    lines.append("")
    lines.append("Benchmarking Yukti against Raw bitstream, DEFLATE (zlib -9), Gzip, Bzip2, LZMA, and Run-Length Encoding (RLE).")
    lines.append("")
    lines.append("| Scale | Distribution | Raw (bits) | Yukti (bits) | Ratio | zlib (bits) | RLE (bits) | Best Block | Verdict |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for scale_label, bit_len in configs:
        # Cap 1 Mbit for fast benchmarking test runs
        test_len = min(bit_len, 65536) if bit_len > 65536 else bit_len
        for dist_label, preset in densities:
            sample = make_preset(preset, length=test_len, seed=42)
            res = compare(sample, block=16)
            display_scale = scale_label if test_len == bit_len else f"{scale_label} (sampled 64k)"
            pct = f"{(res['ratio_vs_raw'] * 100):.1f}%"
            verdict_short = "COMPRESSES" if res["compresses"] else "EXPANDS"
            lines.append(f"| {display_scale} | {dist_label} | {res['raw_bits']} | {res['meru_bits']} | {pct} | {res['zlib_bits']} | {res['rle_bits']} | Block {res['best_block']['block']} | **{verdict_short}** |")

    output = "\n".join(lines)
    return output


if __name__ == "__main__":
    table = run_benchmark_suite()
    print(table)
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "benchmarks.md"), "w", encoding="utf-8") as f:
        f.write(table + "\n")
    print(f"\nSaved benchmark results to docs/benchmarks.md")
