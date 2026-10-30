"""Yukti core: (k, rank) block codec built on the Meru Prastara (Pascal triangle).

Team implementation inspired by Pingala's patterns. NOT a historical compression system.
L (laghu) = 0, G (guru) = 1.
"""
import math
from math import comb
import struct
import zlib

HEADER_LEN_BITS = 32   # total input length in bits
HEADER_BLK_BITS = 8    # block size
HEADER_BITS = HEADER_LEN_BITS + HEADER_BLK_BITS  # 40
MAX_BLOCK = 64
MAX_OUTPUT_BITS = 500000
MAX_INPUT_BITS = 200000

# Precomputed binomial coefficient table up to MAX_BLOCK (64)
_BINOMIAL_TABLE = [[comb(n, k) for k in range(n + 1)] for n in range(MAX_BLOCK + 1)]


def fast_comb(n, k):
    """Fast binomial coefficient lookup from precomputed matrix."""
    if k < 0 or k > n:
        return 0
    if n <= MAX_BLOCK:
        return _BINOMIAL_TABLE[n][k]
    return comb(n, k)


class MeruError(ValueError):
    """Raised for any invalid input / corrupt stream.

    Attributes:
        message (str): Human-readable error description.
        code (str): Machine-readable error code.
        field (str, optional): The name of the invalid input field, if applicable.
        position (int, optional): The bit/byte offset where the error occurred.
    """
    def __init__(self, message, code="BAD_INPUT", field=None, position=None):
        super().__init__(message)
        self.message = str(message)
        self.code = str(code)
        self.field = field
        self.position = position

    def to_dict(self):
        d = {"code": self.code, "message": self.message}
        if self.field is not None:
            d["field"] = self.field
        if self.position is not None:
            d["position"] = self.position
        return d


# ---------- Pingala vocabulary ----------
def prastara(n):
    """Prastara: all 2^n patterns of n syllables in a fixed order (L < G)."""
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 16:
        raise MeruError("n must be an integer between 0 and 16 for listing", code="BAD_PRASTARA_N", field="n")
    return [format(i, "0%db" % n) if n else "" for i in range(2 ** n)]


def meru_rows(rows):
    """Meru Prastara: Pascal's triangle, row r holds C(r, 0..r)."""
    if not isinstance(rows, int) or isinstance(rows, bool) or not 1 <= rows <= 64:
        raise MeruError("rows must be an integer between 1 and 64", code="BAD_MERU_ROWS", field="rows")
    return [list(_BINOMIAL_TABLE[r]) for r in range(rows)]


def uddishta(pattern):
    """Pattern -> index in the prastara order (ranking)."""
    _check_bits(pattern, field="pattern")
    return int(pattern, 2) if pattern else 0


def nashta(n, index):
    """Index -> pattern in the prastara order (unranking)."""
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 64:
        raise MeruError("n must be an integer between 0 and 64", code="BAD_NASHTA_N", field="n")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < 2 ** n:
        raise MeruError("index out of range for n=%d" % n, code="INDEX_OUT_OF_RANGE", field="index")
    return format(index, "0%db" % n) if n else ""


def matra_vritta(total_matra):
    """Patterns of L(=1 matra) / G(=2 matra) that add up to total_matra. Count is Fibonacci."""
    if not isinstance(total_matra, int) or isinstance(total_matra, bool) or not 1 <= total_matra <= 16:
        raise MeruError("matra must be an integer between 1 and 16", code="BAD_MATRA", field="total_matra")
    out = []

    def go(left, acc):
        if left == 0:
            out.append(acc)
            return
        go(left - 1, acc + "L")
        if left >= 2:
            go(left - 2, acc + "G")

    go(total_matra, "")
    return out


# ---------- helpers ----------
def _check_bits(bits, field="bits"):
    if not isinstance(bits, str) or any(c not in "01" for c in bits):
        raise MeruError("bits must be a string of 0 and 1", code="INVALID_BITS", field=field)


def k_width(n):
    """Bits needed to store k in 0..n."""
    return n.bit_length()


def rank_width(n, k):
    """Bits needed to store rank in 0..C(n,k)-1 (0 bits if only one pattern)."""
    return (fast_comb(n, k) - 1).bit_length()


def text_to_bits(text):
    if not isinstance(text, str):
        raise MeruError("text must be a string", code="INVALID_TEXT", field="text")
    try:
        return "".join(format(b, "08b") for b in text.encode("utf-8"))
    except UnicodeEncodeError as e:
        raise MeruError("text encoding failed: %s" % e, code="INVALID_UNICODE", field="text")


def bits_to_text(bits):
    _check_bits(bits)
    if len(bits) % 8:
        raise MeruError("bit length is not a multiple of 8, cannot read as text", code="BAD_TEXT_BIT_LENGTH")
    try:
        return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)).decode("utf-8")
    except UnicodeDecodeError:
        raise MeruError("bits are not valid UTF-8 text", code="INVALID_UTF8")


def bits_to_bytes(bits):
    _check_bits(bits)
    pad = (-len(bits)) % 8
    b = bits + "0" * pad
    return bytes(int(b[i:i + 8], 2) for i in range(0, len(b), 8))


# ---------- block rank / unrank ----------
def rank_block(block):
    """Uddishta inside one block: returns (k, rank). Rank is 0-based, lexicographic with 0 < 1."""
    _check_bits(block, field="block")
    n = len(block)
    k = block.count("1")
    left, r = k, 0
    for i, b in enumerate(block):
        if b == "1":
            r += fast_comb(n - i - 1, left)
            left -= 1
    return k, r


def unrank_block(n, k, r):
    """Nashta inside one block: (n, k, rank) -> pattern."""
    if not 0 <= k <= n:
        raise MeruError("k=%d is invalid for block size %d" % (k, n), code="BAD_K_VALUE")
    limit = fast_comb(n, k)
    if not 0 <= r < limit:
        raise MeruError("rank %d is invalid for C(%d,%d)" % (r, n, k), code="RANK_OUT_OF_RANGE")
    out, left = [], k
    for i in range(n):
        c = fast_comb(n - i - 1, left)
        if left > 0 and r >= c:
            out.append("1")
            r -= c
            left -= 1
        else:
            out.append("0")
    return "".join(out)


# ---------- stream codec ----------
def encode(bits, block=8, detail=False):
    """bits string -> encoded bit string (header + per-block k and rank)."""
    _check_bits(bits)
    if not isinstance(block, int) or isinstance(block, bool) or not 1 <= block <= MAX_BLOCK:
        raise MeruError("block size must be between 1 and %d" % MAX_BLOCK, code="BAD_BLOCK_SIZE", field="block")
    if len(bits) >= 2 ** HEADER_LEN_BITS:
        raise MeruError("input too long", code="INPUT_TOO_LONG", field="bits")
    padded = bits + "0" * ((-len(bits)) % block)
    parts = [format(len(bits), "0%db" % HEADER_LEN_BITS), format(block, "0%db" % HEADER_BLK_BITS)]
    rows = []
    kw = k_width(block)
    for i in range(0, len(padded), block):
        blk = padded[i:i + block]
        k, r = rank_block(blk)
        rw = rank_width(block, k)
        kb = format(k, "0%db" % kw)
        rb = format(r, "0%db" % rw) if rw else ""
        parts.append(kb)
        if rb:
            parts.append(rb)
        if detail:
            rows.append({"block": blk, "k": k, "rank": r, "group_size": fast_comb(block, k),
                         "k_bits": kb, "rank_bits": rb, "bits_used": kw + rw})
    out = "".join(parts)
    return (out, rows) if detail else out


def encode_bytes(data: bytes, block=8) -> bytes:
    """Fast-path encoding directly from raw bytes to .meru v2 container bytes."""
    if not isinstance(data, (bytes, bytearray)):
        raise MeruError("data must be bytes", code="INVALID_TYPE")
    bits = "".join(format(b, "08b") for b in data)
    return pack_container(bits, block=block)


def decode_bytes(container_data: bytes) -> bytes:
    """Fast-path decoding directly from container bytes to raw bytes."""
    bits, _ = unpack_container(container_data)
    return bits_to_bytes(bits)


def decode(stream, max_output_bits=MAX_OUTPUT_BITS):
    """encoded bit string -> original bits. Raises MeruError on corrupt input."""
    _check_bits(stream, field="stream")
    if len(stream) < HEADER_BITS:
        raise MeruError("stream shorter than the %d-bit header" % HEADER_BITS, code="HEADER_TOO_SHORT", position=len(stream))
    total = int(stream[:HEADER_LEN_BITS], 2)
    block = int(stream[HEADER_LEN_BITS:HEADER_BITS], 2)

    if total > max_output_bits:
        raise MeruError(f"claimed output bit length {total} exceeds maximum limit of {max_output_bits} bits", code="CLAIMED_LENGTH_TOO_LARGE", position=0)
    if not 1 <= block <= MAX_BLOCK:
        raise MeruError("header has invalid block size %d" % block, code="BAD_BLOCK_SIZE", position=HEADER_LEN_BITS)
    pos, kw = HEADER_BITS, k_width(block)
    nblocks = -(-total // block) if block else 0

    # Pre-allocation safety check: every block requires AT LEAST kw bits for k
    min_required_bits = HEADER_BITS + nblocks * kw
    if len(stream) < min_required_bits:
        raise MeruError("stream shorter than minimum required for %d blocks" % nblocks, code="STREAM_TRUNCATED", position=len(stream))

    out = []
    for blk_idx in range(nblocks):
        if pos + kw > len(stream):
            raise MeruError("stream ended while reading k", code="STREAM_TRUNCATED", position=pos)
        k = int(stream[pos:pos + kw], 2)
        pos += kw
        if k > block:
            raise MeruError("k=%d is larger than block size" % k, code="K_EXCEEDS_BLOCK", position=pos - kw)
        rw = rank_width(block, k)
        if pos + rw > len(stream):
            raise MeruError("stream ended while reading rank", code="STREAM_TRUNCATED", position=pos)
        r = int(stream[pos:pos + rw], 2) if rw else 0
        pos += rw
        out.append(unrank_block(block, k, r))
    if pos != len(stream):
        raise MeruError("extra bits after the last block", code="TRAILING_BITS", position=pos)
    return "".join(out)[:total]


# ---------- Mulberry32 presets (same generator as the frontend) ----------
def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def nxt():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (a | 1)) & 0xFFFFFFFF
        t = (((t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t)
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return nxt


PRESETS = {
    "sparse":      {"label": "Sparse (5% ones)",  "density": 0.05},
    "mostly_ones": {"label": "Dense (95% ones)",  "density": 0.95},
    "balanced":    {"label": "Random (50% ones)", "density": 0.50},
    "all_zeros":   {"label": "All zeros",         "density": 0.0},
    "alternating": {"label": "Alternating 0101",  "density": None},
}


def make_preset(name, length=256, seed=42):
    if not isinstance(name, str) or name not in PRESETS:
        raise MeruError("unknown preset", code="UNKNOWN_PRESET", field="preset")
    if not isinstance(length, int) or isinstance(length, bool) or not 1 <= length <= 100000:
        raise MeruError("length must be between 1 and 100000", code="BAD_PRESET_LENGTH", field="length")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise MeruError("seed must be an integer", code="BAD_SEED", field="seed")
    if name == "alternating":
        return ("01" * length)[:length]
    d = PRESETS[name]["density"]
    rnd = mulberry32(seed)
    return "".join("1" if rnd() < d else "0" for _ in range(length))


# ---------- Versioned Container (.meru v2) with CRC32 ----------
CONTAINER_MAGIC = b"MERU"
CONTAINER_VERSION_2 = 2
CONTAINER_HEADER_SIZE = 19  # 4 + 1 + 1 + 4 + 1 + 4 + 4


def pack_container(bits, block=8):
    """Packs bits into versioned .meru v2 binary container with CRC32 integrity check.

    Binary Layout:
      Offset  Length  Type     Description
      0       4       bytes    Magic bytes: b"MERU" (ASCII)
      4       1       uint8    Container format version (0x02)
      5       1       uint8    Flags (0x00 reserved)
      6       4       uint32BE Original input bit length
      10      1       uint8    Block size n (1..64)
      11      4       uint32BE Payload bit length
      15      4       uint32BE CRC32 of original data (IEEE 802.3 standard)
      19      var     bytes    Serialized combinadic (k, rank) payload bytes

    What CRC32 DOES protect against:
      - Transmission noise, accidental bit flips, incomplete downloads, and truncation.
    What CRC32 DOES NOT protect against:
      - Intentional cryptographic forgery or tampering.
    """
    _check_bits(bits)
    if not isinstance(block, int) or isinstance(block, bool) or not 1 <= block <= MAX_BLOCK:
        raise MeruError("block size must be between 1 and %d" % MAX_BLOCK, code="BAD_BLOCK_SIZE", field="block")

    enc_stream = encode(bits, block=block)
    payload_bits = enc_stream[HEADER_BITS:]
    payload_bytes = bits_to_bytes(payload_bits)
    orig_bytes = bits_to_bytes(bits)
    crc = zlib.crc32(orig_bytes) & 0xFFFFFFFF

    header = struct.pack(
        ">4sBBIBII",
        CONTAINER_MAGIC,
        CONTAINER_VERSION_2,
        0,  # flags
        len(bits),
        block,
        len(payload_bits),
        crc
    )
    return header + payload_bytes


def unpack_container(data):
    """Unpacks a .meru container (v2 binary with CRC or v1 raw bits/bytes).

    Returns:
        tuple (bits, metadata_dict)
    """
    if isinstance(data, str):
        # Legacy v1 string of '0' and '1'
        bits = decode(data)
        return bits, {"version": 1, "crc_verified": False}

    if not isinstance(data, (bytes, bytearray)):
        raise MeruError("container data must be bytes or bit string", code="INVALID_TYPE")

    data = bytes(data)
    if data.startswith(CONTAINER_MAGIC):
        # Versioned .meru v2 container
        if len(data) < CONTAINER_HEADER_SIZE:
            raise MeruError("container data shorter than v2 header", code="CONTAINER_TOO_SHORT")

        magic, version, flags, orig_len, block, payload_bit_len, expected_crc = struct.unpack(
            ">4sBBIBII", data[:CONTAINER_HEADER_SIZE]
        )
        if version != CONTAINER_VERSION_2:
            raise MeruError(f"unsupported container version {version}", code="UNSUPPORTED_VERSION")
        if not 1 <= block <= MAX_BLOCK:
            raise MeruError(f"container has invalid block size {block}", code="BAD_BLOCK_SIZE")

        expected_payload_bytes = (-(-payload_bit_len // 8)) if payload_bit_len else 0
        actual_payload_bytes = len(data) - CONTAINER_HEADER_SIZE
        if actual_payload_bytes < expected_payload_bytes:
            raise MeruError("container payload truncated", code="PAYLOAD_TRUNCATED")

        raw_payload = data[CONTAINER_HEADER_SIZE:CONTAINER_HEADER_SIZE + expected_payload_bytes]
        payload_bits = "".join(format(b, "08b") for b in raw_payload)[:payload_bit_len]

        stream = format(orig_len, "032b") + format(block, "08b") + payload_bits
        bits = decode(stream)

        actual_crc = zlib.crc32(bits_to_bytes(bits)) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise MeruError(
                f"checksum mismatch: expected {hex(expected_crc)}, got {hex(actual_crc)}",
                code="CHECKSUM_MISMATCH"
            )

        return bits, {
            "version": 2,
            "crc_verified": True,
            "crc32": hex(expected_crc),
            "original_bits": orig_len,
            "block": block
        }
    else:
        # Legacy v1 binary bytes format (direct byte encoding of raw 40-bit stream)
        stream = "".join(format(b, "08b") for b in data)
        bits = decode(stream)
        return bits, {"version": 1, "crc_verified": False}


# ---------- analysis, trace, corruption, and sweep helpers ----------
def trace_block(block):
    """Detailed ranking walk for a single block."""
    _check_bits(block, field="block")
    n = len(block)
    k = block.count("1")
    left = k
    running_sum = 0
    terms = []
    for i, b in enumerate(block):
        rem = n - i - 1
        if b == "1":
            val = fast_comb(rem, left)
            running_sum += val
            terms.append({
                "pos": i,
                "bit": b,
                "n": rem,
                "left": left,
                "value": val,
                "running_sum": running_sum
            })
            left -= 1
        else:
            terms.append({
                "pos": i,
                "bit": b,
                "n": rem,
                "left": left,
                "value": 0,
                "running_sum": running_sum
            })
    return {
        "block": block,
        "k": k,
        "rank": running_sum,
        "k_bits": k_width(n),
        "rank_bits": rank_width(n, k),
        "binomial_terms": terms,
        "running_sum": running_sum
    }


def trace_stream(bits, block=8, max_blocks=32):
    """Trace multiple blocks up to max_blocks for UI visualization."""
    _check_bits(bits)
    if not isinstance(block, int) or isinstance(block, bool) or not 1 <= block <= MAX_BLOCK:
        raise MeruError(f"block size must be between 1 and {MAX_BLOCK}", code="BAD_BLOCK_SIZE", field="block")
    padded = bits + "0" * ((-len(bits)) % block)
    blocks_out = []
    for i in range(0, min(len(padded), max_blocks * block), block):
        blk = padded[i:i + block]
        blocks_out.append(trace_block(blk))
    return {
        "total_bits": len(bits),
        "block_size": block,
        "total_blocks": -(-len(padded) // block) if block else 0,
        "traced_blocks": len(blocks_out),
        "blocks": blocks_out
    }


def calculate_entropy(bits, block=8):
    """Calculate empirical Shannon entropy H(p), theoretical minimum size, and MeruCode gap."""
    _check_bits(bits)
    n = len(bits)
    if n == 0:
        return {
            "n_bits": 0,
            "ones": 0,
            "zeros": 0,
            "p1": 0.0,
            "p0": 0.0,
            "shannon_entropy_per_bit": 0.0,
            "theoretical_min_bits": 0,
            "meru_bits": HEADER_BITS,
            "meru_block": block,
            "meru_gap_bits": HEADER_BITS,
            "meru_gap_pct": 0.0,
            "zlib_bits": 0,
            "zlib_gap_bits": 0,
            "explanation": "Empty bitstream."
        }

    k = bits.count("1")
    p1 = k / n
    p0 = 1.0 - p1

    if p1 == 0.0 or p1 == 1.0:
        h = 0.0
    else:
        h = - (p0 * math.log2(p0) + p1 * math.log2(p1))

    theoretical_min = n * h
    ceil_theo_min = math.ceil(theoretical_min)

    encoded_bits = encode(bits, block)
    meru_bits = len(encoded_bits)
    meru_gap = meru_bits - ceil_theo_min
    meru_gap_pct = round(((meru_bits - theoretical_min) / theoretical_min * 100), 2) if theoretical_min > 0 else 0.0

    raw_bytes = bits_to_bytes(bits)
    zlib_bits = len(zlib.compress(raw_bytes, 9)) * 8
    zlib_gap = zlib_bits - ceil_theo_min

    explanation = (
        f"Shannon entropy H(p) = {h:.4f} bits/symbol. MeruCode encodes each block of size {block} using "
        f"k_bits + log2(C(n,k)). As block size grows, log2(C(n, pn)) / n -> H(p). "
        f"For low entropy (sparse/dense), MeruCode compresses toward the Shannon limit. "
        f"For Bernoulli(0.5) random noise, H(p) = 1.0 and any lossless code with headers expands."
    )

    return {
        "n_bits": n,
        "ones": k,
        "zeros": n - k,
        "p1": round(p1, 5),
        "p0": round(p0, 5),
        "shannon_entropy_per_bit": round(h, 5),
        "theoretical_min_bits": ceil_theo_min,
        "meru_bits": meru_bits,
        "meru_block": block,
        "meru_gap_bits": meru_gap,
        "meru_gap_pct": meru_gap_pct,
        "zlib_bits": zlib_bits,
        "zlib_gap_bits": zlib_gap,
        "explanation": explanation
    }


def corrupt_and_decode(encoded, position):
    """Given an encoded bitstream and a bit position, flip that bit and return decode result or structured error."""
    _check_bits(encoded, field="encoded")
    if not (0 <= position < len(encoded)):
        raise MeruError(f"position {position} is out of bounds for stream of length {len(encoded)}",
                        code="POSITION_OUT_OF_BOUNDS", field="position")

    flipped_char = "0" if encoded[position] == "1" else "1"
    corrupted_stream = encoded[:position] + flipped_char + encoded[position + 1:]

    try:
        orig_decoded = decode(encoded)
    except MeruError:
        orig_decoded = None

    try:
        corrupted_decoded = decode(corrupted_stream)
        diff_count = 0
        min_len = min(len(orig_decoded) if orig_decoded else 0, len(corrupted_decoded))
        for j in range(min_len):
            if orig_decoded and orig_decoded[j] != corrupted_decoded[j]:
                diff_count += 1
        diff_count += abs((len(orig_decoded) if orig_decoded else 0) - len(corrupted_decoded))

        return {
            "flipped_position": position,
            "original_bit": encoded[position],
            "flipped_bit": flipped_char,
            "success": True,
            "error": None,
            "diff_summary": {
                "orig_length": len(orig_decoded) if orig_decoded else 0,
                "new_length": len(corrupted_decoded),
                "bit_errors": diff_count,
                "bit_error_rate": round(diff_count / max(len(orig_decoded) if orig_decoded else 1, 1), 4)
            },
            "decoded_preview": corrupted_decoded[:200]
        }
    except MeruError as exc:
        return {
            "flipped_position": position,
            "original_bit": encoded[position],
            "flipped_bit": flipped_char,
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
                "position": exc.position
            },
            "diff_summary": None,
            "decoded_preview": None
        }


def sweep_ratios(density=0.05, length=1024, seed=42, block_min=4, block_max=64, step=2):
    """Sweep block sizes for a given density and return compression ratios."""
    if not (0.0 <= density <= 1.0):
        raise MeruError("density must be between 0.0 and 1.0", code="BAD_DENSITY", field="density")
    if not (16 <= length <= 20000):
        raise MeruError("length must be between 16 and 20000", code="BAD_LENGTH", field="length")

    rnd = mulberry32(seed)
    bits = "".join("1" if rnd() < density else "0" for _ in range(length))

    results = []
    for b in range(block_min, block_max + 1, step):
        enc = encode(bits, block=b)
        ratio = round(len(enc) / len(bits), 4)
        results.append({
            "block": b,
            "encoded_bits": len(enc),
            "ratio": ratio,
            "compresses": len(enc) < len(bits)
        })

    return {
        "density": density,
        "length": length,
        "seed": seed,
        "points": results
    }

