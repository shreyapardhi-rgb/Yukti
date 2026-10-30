"""MeruCode core: (k, rank) block codec built on the Meru Prastara (Pascal triangle).

Team implementation inspired by Pingala's patterns. NOT a historical compression system.
L (laghu) = 0, G (guru) = 1.
"""
from math import comb

HEADER_LEN_BITS = 32   # total input length in bits
HEADER_BLK_BITS = 8    # block size
HEADER_BITS = HEADER_LEN_BITS + HEADER_BLK_BITS  # 40
MAX_BLOCK = 64


class MeruError(ValueError):
    """Raised for any invalid input / corrupt stream."""


# ---------- Pingala vocabulary ----------
def prastara(n):
    """Prastara: all 2^n patterns of n syllables in a fixed order (L < G)."""
    if not 0 <= n <= 16:
        raise MeruError("n must be between 0 and 16 for listing")
    return [format(i, "0%db" % n) if n else "" for i in range(2 ** n)]


def meru_rows(rows):
    """Meru Prastara: Pascal's triangle, row r holds C(r, 0..r)."""
    if not 1 <= rows <= 64:
        raise MeruError("rows must be between 1 and 64")
    return [[comb(r, k) for k in range(r + 1)] for r in range(rows)]


def uddishta(pattern):
    """Pattern -> index in the prastara order (ranking)."""
    _check_bits(pattern)
    return int(pattern, 2) if pattern else 0


def nashta(n, index):
    """Index -> pattern in the prastara order (unranking)."""
    if not 0 <= index < 2 ** n:
        raise MeruError("index out of range for n=%d" % n)
    return format(index, "0%db" % n) if n else ""


def matra_vritta(total_matra):
    """Patterns of L(=1 matra) / G(=2 matra) that add up to total_matra. Count is Fibonacci."""
    if not 1 <= total_matra <= 16:
        raise MeruError("matra must be between 1 and 16")
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
def _check_bits(bits):
    if not isinstance(bits, str) or any(c not in "01" for c in bits):
        raise MeruError("bits must be a string of 0 and 1")


def k_width(n):
    """Bits needed to store k in 0..n."""
    return n.bit_length()


def rank_width(n, k):
    """Bits needed to store rank in 0..C(n,k)-1 (0 bits if only one pattern)."""
    return (comb(n, k) - 1).bit_length()


def text_to_bits(text):
    return "".join(format(b, "08b") for b in text.encode("utf-8"))


def bits_to_text(bits):
    if len(bits) % 8:
        raise MeruError("bit length is not a multiple of 8, cannot read as text")
    try:
        return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)).decode("utf-8")
    except UnicodeDecodeError:
        raise MeruError("bits are not valid UTF-8 text")


def bits_to_bytes(bits):
    pad = (-len(bits)) % 8
    b = bits + "0" * pad
    return bytes(int(b[i:i + 8], 2) for i in range(0, len(b), 8))


# ---------- block rank / unrank ----------
def rank_block(block):
    """Uddishta inside one block: returns (k, rank). Rank is 0-based, lexicographic with 0 < 1."""
    n = len(block)
    k = block.count("1")
    left, r = k, 0
    for i, b in enumerate(block):
        if b == "1":
            r += comb(n - i - 1, left)
            left -= 1
    return k, r


def unrank_block(n, k, r):
    """Nashta inside one block: (n, k, rank) -> pattern."""
    if not 0 <= k <= n:
        raise MeruError("k=%d is invalid for block size %d" % (k, n))
    if not 0 <= r < comb(n, k):
        raise MeruError("rank %d is invalid for C(%d,%d)" % (r, n, k))
    out, left = [], k
    for i in range(n):
        c = comb(n - i - 1, left)
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
    if not 1 <= block <= MAX_BLOCK:
        raise MeruError("block size must be between 1 and %d" % MAX_BLOCK)
    if len(bits) >= 2 ** HEADER_LEN_BITS:
        raise MeruError("input too long")
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
        parts += [kb, rb]
        if detail:
            rows.append({"block": blk, "k": k, "rank": r, "group_size": comb(block, k),
                         "k_bits": kb, "rank_bits": rb, "bits_used": kw + rw})
    out = "".join(parts)
    return (out, rows) if detail else out


def decode(stream):
    """encoded bit string -> original bits. Raises MeruError on corrupt input."""
    _check_bits(stream)
    if len(stream) < HEADER_BITS:
        raise MeruError("stream shorter than the %d-bit header" % HEADER_BITS)
    total = int(stream[:HEADER_LEN_BITS], 2)
    block = int(stream[HEADER_LEN_BITS:HEADER_BITS], 2)
    if not 1 <= block <= MAX_BLOCK:
        raise MeruError("header has invalid block size %d" % block)
    pos, kw = HEADER_BITS, k_width(block)
    nblocks = -(-total // block)
    out = []
    for _ in range(nblocks):
        if pos + kw > len(stream):
            raise MeruError("stream ended while reading k")
        k = int(stream[pos:pos + kw], 2)
        pos += kw
        if k > block:
            raise MeruError("k=%d is larger than block size" % k)
        rw = rank_width(block, k)
        if pos + rw > len(stream):
            raise MeruError("stream ended while reading rank")
        r = int(stream[pos:pos + rw], 2) if rw else 0
        pos += rw
        out.append(unrank_block(block, k, r))
    if pos != len(stream):
        raise MeruError("extra bits after the last block")
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
    if name not in PRESETS:
        raise MeruError("unknown preset")
    if not 1 <= length <= 100000:
        raise MeruError("length must be between 1 and 100000")
    if name == "alternating":
        return ("01" * length)[:length]
    d = PRESETS[name]["density"]
    rnd = mulberry32(seed)
    return "".join("1" if rnd() < d else "0" for _ in range(length))
