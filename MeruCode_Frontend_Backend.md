# MeruCode: Frontend and Backend, in detail

**Problem:** CSE-03 (Intermediate), *Turn Pingala's patterns into a digital encoding system*.

**Method note (important):** the (k, rank) block codec described here is **this team's own implementation**. It is *inspired by* Pingala's Prastara, Meru Prastara, Uddishta and Nashta. It is **not** a historical Indian compression system, and this document never claims that it is. It also does **not** always compress. Section 9 shows where it helps and where it does not.

---

## Table of contents

1. What the problem asks and how this project answers it
2. Pingala vocabulary mapped to code
3. The encoding scheme (the exact bit format)
4. Worked example: encoding `saket`
5. Project structure and how to run it
6. Backend in detail (codec, benchmark, Flask API, error handling, tests)
7. Frontend in detail (tabs, features, data flow, design)
8. Correctness and test results
9. Honest comparison: does it compress or only encode?
10. Limitations and possible improvements
11. Demo script and final checklist
12. Full source code

---

## 1. What the problem asks and how this project answers it

| Problem statement requirement | How it is answered | Where |
|---|---|---|
| Program inspired by Pingala's binary patterns and combinatorial arrangements | Prastara generator, Meru Prastara (Pascal's triangle), Uddishta / Nashta as rank / unrank | `core.py`, Tab 1 |
| Generate patterns and use them to encode and decode a short text or binary sequence | (k, rank) block codec for text (UTF-8) or raw bits | `core.py`, Tab 2 |
| Define the team's own encoding scheme | Section 3 gives the exact bit layout | Section 3 |
| Reconstruct the original input correctly | Roundtrip check on every encode, plus 28 backend tests and 14 browser tests | Section 8 |
| Compare storage size and execution time with a simple baseline | Raw bits and zlib, sizes in bits and times in milliseconds | `bench.py`, Tab 3 |
| Show whether it compresses or merely encodes | A verdict line, "COMPRESSES" or "ONLY ENCODES", computed from real sizes | Tab 2, Tab 3, Section 9 |
| Interactive pattern generator, encoder/decoder, correctness tests, comparison results | Four-tab web app plus a REST API | Sections 6 and 7 |
| Label the method as the team's, not historical | Banner on the page, and this document | Header, Section 1 |

---

## 2. Pingala vocabulary mapped to code

L (laghu, short) is written as `0` and G (guru, long) as `1`.

| Term | Meaning | Code |
|---|---|---|
| **Prastara** | The list of all 2^n patterns of n syllables in a fixed order | `prastara(n)` |
| **Meru Prastara** | The triangle where each number is the sum of the two above it. Row n, position k is C(n, k) = number of n-syllable patterns with k gurus | `meru_rows(rows)` |
| **Uddishta** | Pattern in, index out (ranking). This is **encoding** | `uddishta(pattern)` for whole lists, `rank_block(block)` inside a k-group |
| **Nashta** | Index in, pattern out (unranking). This is **decoding** | `nashta(n, index)` for whole lists, `unrank_block(n, k, rank)` inside a k-group |
| **Sankhya** | Total number of patterns, 2^n | shown in Tab 1 |
| **Matra-vritta** | Meters with a fixed total matra (L = 1, G = 2). The counts are Fibonacci numbers | `matra_vritta(m)` |

The codec uses Meru Prastara, Uddishta and Nashta *inside each block*. A block is first placed in the row of the triangle that matches its number of gurus (k), then Uddishta gives its position inside that group.

---

## 3. The encoding scheme (the exact bit format)

### 3.1 Why k and rank both are needed

Think of an address: **k is the building, rank is the flat number**. Every building has a flat number 1, so the flat number alone does not identify anything. The decoder reads k first (which group), then rank (which pattern inside the group).

For 3-bit blocks:

| k | patterns in the group | rank |
|---|---|---|
| 1 | `001`, `010`, `100` | 0, 1, 2 |
| 2 | `011`, `101`, `110` | 0, 1, 2 |

"rank 1" alone could mean `010` or `101`. "k = 2, rank 1" is only `101`.

### 3.2 Stream layout

```
| header (40 bits)                 | block 1        | block 2        | ... |
| length (32) | block size n (8)   | k | rank       | k | rank       |     |
```

| Field | Width | Meaning |
|---|---|---|
| length | 32 bits | number of **input bits** (so padding can be removed on decode) |
| block size n | 8 bits | 1 to 64 |
| k | `bit_length(n)` bits (4 bits for n = 8) | number of 1s in the block, 0 to n |
| rank | `bit_length(C(n,k) - 1)` bits (0 bits if the group has one pattern) | 0-based position of the block among all n-bit patterns with the same k |

### 3.3 Rank definition (Uddishta inside a group)

Patterns with the same k are ordered as binary strings with `0 < 1`. Walk the block from left to right with `left` = ones still to place. At each position `i` that holds a `1`, add `C(n - i - 1, left)` (the number of patterns that have `0` here and the same ones remaining later), then decrement `left`.

Unrank (Nashta) reverses it: at each position compute `c = C(n - i - 1, left)`. If `rank >= c`, output `1`, subtract `c`, decrement `left`. Otherwise output `0`.

### 3.4 Padding

If the input length is not a multiple of n, zeros are appended to the last block. The 32-bit length in the header lets the decoder cut them off again.

### 3.5 Text input

Text is converted to UTF-8 bytes, then to 8 bits per byte. So Devanagari or emoji text works too.

### 3.6 Size formula

```
total bits = 40 + sum over blocks of ( bit_length(n) + bit_length(C(n, k) - 1) )
```

A block saves bits only when `bit_length(C(n,k)-1) + bit_length(n)` is smaller than `n`. That happens when k is near 0 or near n (very few 1s or very few 0s), and not when k is near n/2.

---

## 4. Worked example: encoding `saket`

Block size 8, input 40 bits.

| letter | block | k | rank | group size C(8,k) | k bits | rank bits | bits used |
|---|---|---|---|---|---|---|---|
| `s` | `01110011` | 5 | 15 | 56 | `0101` | `001111` | 10 |
| `a` | `01100001` | 3 | 30 | 56 | `0011` | `011110` | 10 |
| `k` | `01101011` | 5 | 12 | 56 | `0101` | `001100` | 10 |
| `e` | `01100101` | 4 | 26 | 70 | `0100` | `0011010` | 11 |
| `t` | `01110100` | 4 | 33 | 70 | `0100` | `0100001` | 11 |

- Header (40 bits): `0000000000000000000000000010100000001000`
- First 32 bits are the length 40, next 8 bits are the block size 8.
- Payload: 52 bits. Total: **92 bits**.
- Full stream: `00000000000000000000000000101000000010000101001111001101111001010011000100001101001000100001`

Decoding reads the header, then for each of the 5 blocks reads k, reads rank, unranks, and joins the blocks. The 40 bits become `saket` again.

**Result:** 40 bits became 92 bits. This input is **encoded, not compressed**. The 40-bit header is most of the extra cost, and text blocks usually have k near 4, which is where the groups are biggest.

---

## 5. Project structure and how to run it

```
merucode/
  backend/
    core.py            codec, Pingala vocabulary, Mulberry32 presets
    bench.py           size and time comparison with raw bits and zlib
    app.py             Flask REST API (also serves the frontend at /)
    test_meru.py       28 tests (codec + API)
    requirements.txt
  frontend/
    index.html         single-file web app (HTML + CSS + JS, no build step)
```

### Run the backend and frontend together

```bash
cd merucode/backend
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

The page shows `backend: connected` in the header when the API answers.

### Run only the frontend

Open `frontend/index.html` directly in a browser. The page shows `backend: offline (frontend still works)`. Everything except Python's zlib works, because the JavaScript has its own copy of the codec. The zlib baseline then uses the browser's `CompressionStream` when it exists.

### Run the tests

```bash
cd merucode/backend
python -m unittest -v        # 28 tests
```

Frontend tests run in the browser from Tab 4 (14 tests).

Requirements: Python 3.9+ and Flask 3. No other package is needed. The Python tests use only the standard library `unittest` plus Flask's test client.

---

## 6. Backend in detail

### 6.1 Modules

| File | Role |
|---|---|
| `core.py` | Pure Python, no I/O. Block rank/unrank, stream encode/decode, text/bits helpers, Pingala vocabulary functions, Mulberry32 and presets, `MeruError` |
| `bench.py` | `compare(bits, block)` returns sizes, times, verdict and best block size |
| `app.py` | Flask routes, JSON validation, error handler, CORS headers, static serving |
| `test_meru.py` | Unit and API tests |

### 6.2 Main functions in `core.py`

| Function | What it does |
|---|---|
| `rank_block(block)` | `"01110011"` gives `(5, 15)` |
| `unrank_block(n, k, r)` | `(8, 5, 15)` gives `"01110011"`, raises on invalid k or rank |
| `encode(bits, block=8, detail=False)` | Bits string to encoded bits string. With `detail=True` it also returns a per-block table |
| `decode(stream)` | Encoded bits to original bits. Validates length, block size, k, rank, truncation and trailing bits |
| `text_to_bits`, `bits_to_text`, `bits_to_bytes` | Text and byte conversions |
| `prastara(n)`, `meru_rows(r)`, `matra_vritta(m)`, `uddishta(p)`, `nashta(n, i)` | Pingala vocabulary |
| `mulberry32(seed)`, `make_preset(name, length, seed)` | Seeded random generator and the test-data presets |

Python integers are unbounded, so `math.comb` is exact for any block size up to 64.

### 6.3 Presets and Mulberry32

Mulberry32 is a small 32-bit seeded random number generator. The same seed always produces the same bits, so every comparison can be repeated. The JavaScript version in the frontend is a port of the same algorithm, and a cross-check showed that **both produce identical numbers and identical bit strings** for the tested seeds.

| Preset | Content |
|---|---|
| `sparse` | each bit is 1 with probability 0.05 |
| `mostly_ones` | each bit is 1 with probability 0.95 |
| `balanced` | each bit is 1 with probability 0.5 |
| `all_zeros` | only zeros |
| `alternating` | `0101...` |

### 6.4 REST API reference

Base URL: `http://127.0.0.1:5000`. All bodies are JSON. All errors return HTTP 400 (or 404 for an unknown path) with `{"error": "..."}`.

| Method | Path | Input | Output |
|---|---|---|---|
| GET | `/api/health` | none | status and header size |
| GET | `/api/prastara?n=3` | n, 0 to 16 | all 2^n patterns, plus L/G display form |
| GET | `/api/meru?rows=9` | rows, 1 to 64 | Pascal triangle rows |
| GET | `/api/matra?m=5` | m, 1 to 16 | matra-vritta patterns and count |
| GET | `/api/uddishta?pattern=101` | pattern | index |
| GET | `/api/nashta?n=3&index=5` | n, index | pattern |
| GET | `/api/presets` | none | preset names and labels |
| POST | `/api/generate` | `{"preset","length","seed"}` | generated bits and number of ones |
| POST | `/api/encode` | `{"text"` or `"bits","block"}` | header, per-block table, encoded stream |
| POST | `/api/decode` | `{"encoded","as_text"}` | original bits, and text if `as_text` is true |
| POST | `/api/compare` | `{"text"` or `"bits","block"}` | sizes, times, verdict, best block |
| GET | `/` | none | the frontend page |

Limits: input up to 200000 bits, block size 1 to 64, JSON object required.

**Example: `POST /api/encode`** with `{"text": "saket", "block": 8}`

```json
{
  "mode": "text",
  "input_bits": 40,
  "block": 8,
  "header": "0000000000000000000000000010100000001000",
  "blocks": [
    {
      "block": "01110011",
      "k": 5,
      "rank": 15,
      "group_size": 56,
      "k_bits": "0101",
      "rank_bits": "001111",
      "bits_used": 10
    },
    "..."
  ],
  "encoded": "00000000000000000000000000101000000010000101001111...",
  "encoded_bits": 92
}
```

**Example: `POST /api/compare`** with `{"text": "saket", "block": 8}`

```json
{
  "input_bits": 40,
  "raw_bits": 40,
  "zlib_bits": 104,
  "meru_bits": 92,
  "meru_payload_bits": 52,
  "block": 8,
  "roundtrip_ok": true,
  "ratio_vs_raw": 2.3,
  "compresses": false,
  "compresses_without_header": false,
  "time_ms": {
    "meru_encode": "...",
    "meru_decode": "...",
    "zlib_compress": "...",
    "zlib_decompress": "..."
  },
  "best_block": {
    "block": 12,
    "meru_bits": 90
  },
  "verdict": "ONLY ENCODES: 40 bits -> 92 bits (230.0% of original, larger)"
}
```

**Example: error** from `POST /api/encode` with `{"bits": "12"}` (HTTP 400)

```json
{
  "error": "bits must be a string of 0 and 1"
}
```

**Example: `GET /api/meru?rows=5`**

```json
{
  "rows": [
    [
      1
    ],
    [
      1,
      1
    ],
    [
      1,
      2,
      1
    ],
    [
      1,
      3,
      3,
      1
    ],
    [
      1,
      4,
      6,
      4,
      1
    ]
  ]
}
```

### 6.5 Error handling

| Situation | Behaviour |
|---|---|
| Characters other than 0 and 1 in bits | `MeruError`, HTTP 400 |
| Block size outside 1..64 | `MeruError`, HTTP 400 |
| Decode input shorter than the header | `MeruError` |
| Header block size invalid | `MeruError` |
| k larger than the block size, or rank outside the group | `MeruError` |
| Stream ends early, or has extra bits | `MeruError` |
| Text bits that are not valid UTF-8 | `MeruError` |
| Body not a JSON object | HTTP 400 |

The decoder never crashes on a corrupt stream and never returns wrong data silently.

### 6.6 Timing method

`bench.compare` runs each operation `repeats` times (default 20) with `time.perf_counter` and reports the average in milliseconds. The baseline is `zlib.compress(raw_bytes, 9)`. Sizes are in bits, and the zlib size is `len(compressed) * 8`.

---

## 7. Frontend in detail

A single file, `frontend/index.html`, with no framework and no build step. It has a clean light and dark theme (follows the system setting), works on phone widths, and keeps all codec logic in plain functions so they can be tested.

### 7.1 Header

Title, the problem tag, a **backend status pill** (`connected` or `offline`), and the method note banner stating that the encoding is the team's own implementation.

### 7.2 Tab 1: Pattern generator (Prastara and Meru Prastara)

| Control | Effect |
|---|---|
| Syllables n (1 to 8) | Lists all 2^n patterns in order, each drawn as coloured L (blue) and G (orange) cells |
| Highlight k | Shows only patterns with exactly k gurus, and the count C(n, k) |
| Click a pattern | Shows Uddishta (pattern gives index) and Nashta (index gives pattern) |
| Pascal triangle | Row n is highlighted, and the selected k cell inside it |
| Matra total + "Show Matra-vritta" | Lists the L(1)/G(2) meters for the total and shows that the count is a Fibonacci number |

### 7.3 Tab 2: Encode / Decode

| Control | Effect |
|---|---|
| Text area | Text or a bit string |
| Input is | `text` (UTF-8) or `bits` |
| Block size | 1 to 64 |
| Preset | Fills the box with a Mulberry32 bit string |
| Encode and decode | Shows the table of blocks (k, rank, group size, k bits, rank bits, bits used), the colour-coded stream (header in gold), the decoded result with an identical / mismatch flag, and the COMPRESSES / ONLY ENCODES verdict |

The first 60 blocks are shown for long inputs. Errors appear in red below the controls and never break the page.

### 7.4 Tab 3: Compare

Five one-click inputs: the text "saket", and the Sparse, Dense, Random and All zeros presets, plus inputs for length and block size.

For each run the page shows:

- Bar chart of **raw bits, MeruCode and zlib** (all on the same scale)
- Roundtrip OK / FAILED
- Verdict line
- Time table: encode and decode averaged over 20 runs, plus zlib compress time
- Best block size found among 2, 4, 8, 12, 16, 24, 32

zlib comes from the Python backend when connected, otherwise from the browser's `CompressionStream("deflate")`, otherwise a note says it is not available.

### 7.5 Tab 4: Tests

Runs 14 in-browser checks: the `saket` golden values (92 bits, ranks 15, 30, 12, 26, 33), decode equals input, all 256 8-bit blocks, 200 random roundtrips with many block sizes, Unicode text, empty input, Fibonacci counts, Pascal row 5, Mulberry32 determinism, sparse data compresses, random data does not, corrupt streams throw, bad input throws. Each line shows PASS or FAIL and a final `n / 14` count.

### 7.6 Data flow

```
User input --> textToBits --> encode(bits, n) --> encoded stream + block rows --> table / bit view
                                         |
                                         +--> decode(stream) --> compare with input --> identical / mismatch
Compare tab --> encode, decode (timed) + zlib (backend or browser) --> bars + verdict
```

### 7.7 Frontend JavaScript functions

| Function | Role |
|---|---|
| `C(n, k)` | Binomial with memo, uses `BigInt` so block sizes up to 64 are exact |
| `rankBlock`, `unrankBlock` | Uddishta and Nashta inside a block |
| `encode(bits, block)`, `decode(stream)` | Same format as the Python codec |
| `prastara`, `meruRows`, `matraVritta` | Pattern generation |
| `mulberry32`, `makePreset` | Same presets as the backend |
| `verdict(raw, meru)` | Builds the COMPRESSES / ONLY ENCODES text |
| `renderGen`, event handlers | Draw each tab |

The code between `// ==CORE==` and `// ==/CORE==` in the HTML has no DOM calls, so it can be loaded in Node for testing.

### 7.8 Why the codec is duplicated in JavaScript

- The demo works with no server (open the file).
- Encode and decode feel instant while typing.
- The Python backend is the reference and the place for zlib, the API and the heavier tests.

Both implementations were checked against each other (Section 8).

---

## 8. Correctness and test results

### 8.1 Backend: 28 tests, all passing

| Group | What it checks |
|---|---|
| Pingala vocabulary | Prastara has 2^n entries, Pascal rows sum to 2^n, Uddishta and Nashta are inverses, Matra-vritta counts are 1, 2, 3, 5, 8, 13, 21, 34 |
| Block rank | `saket` ranks match the hand calculation, every one of the 256 8-bit blocks roundtrips, (k, rank) pairs are unique, bad k and bad rank raise |
| Stream codec | Golden `saket` (40 to 92 bits, first block bits `0101001111`), empty input, 300 random inputs with block sizes 1 to 64, Unicode text, corrupt streams raise, padding is removed |
| Honest compression | Text does not compress, sparse and dense data compress, random data does not |
| Mulberry32 | Deterministic, always in [0, 1), preset densities as expected |
| API | health, encode and decode roundtrip, compare, 400 errors, pattern endpoints, generate |

### 8.2 Frontend: 14 tests, all passing

The same list from Tab 4 was also run under Node.js and gave 14 / 14.

### 8.3 Cross-check between JavaScript and Python

The JavaScript codec and the Python codec produced **identical** output for: the `saket` stream, the first Mulberry32 values for seeds 1, 42 and 123456, the sparse and balanced presets, and the encodings of those presets at block sizes 16 and 5.

### 8.4 Live server check

With `python app.py` running, `curl` confirmed: health returns `ok`, `/api/encode` returns 92 bits for `saket`, `/api/compare` returns the verdict, `/` returns HTTP 200, and a bad request returns HTTP 400.

---

## 9. Honest comparison: does it compress or only encode?

Measured with the real code. Sizes are in bits. MeruCode sizes include the 40-bit header. Times are the average of 30 runs in milliseconds (Python).

| Input | Raw bits | Block | MeruCode | zlib | MeruCode with best block | Verdict | Meru encode ms | zlib ms |
|---|---|---|---|---|---|---|---|---|
| Text "saket" | 40 | 8 | 92 | 104 | 90 (block 12) | ONLY ENCODES | 0.0123 | 0.0338 |
| Text "Pingala Chhandas Shastra" | 192 | 8 | 278 | 256 | 248 (block 32) | ONLY ENCODES | 0.0882 | 0.0516 |
| All zeros, 1024 bits | 1024 | 16 | 360 | 96 | 232 (block 32) | COMPRESSES | 0.228 | 0.0515 |
| Sparse 5% ones, 1024 bits | 1024 | 16 | 550 | 656 | 461 (block 32) | COMPRESSES | 0.2586 | 0.0417 |
| Dense 95% ones, 1024 bits | 1024 | 16 | 553 | 632 | 459 (block 32) | COMPRESSES | 0.2701 | 0.0778 |
| Random 50% ones, 1024 bits | 1024 | 8 | 1297 | 1112 | 1160 (block 32) | ONLY ENCODES | 0.3458 | 0.0665 |
| Alternating 0101, 1024 bits | 1024 | 16 | 1256 | 96 | 1192 (block 32) | ONLY ENCODES | 0.2536 | 0.0372 |

**What the table says:**

1. **Short text is not compressed.** `saket` goes from 40 to 92 bits. Even the best block size (12) gives 90 bits. The method only encodes it.
2. **Sparse and dense data are compressed.** 1024 bits with 5% ones drop to 550 bits (about 54%), and 461 bits with block 32. Blocks with very few 1s (or very few 0s) fall in small k-groups, so their rank needs few bits.
3. **Random data is not compressed.** Blocks of random bits land near k = n/2 where the groups are largest. Output is larger than input.
4. **zlib is usually better, with exceptions.** zlib wins on the longer text (256 against 278 bits), on all zeros (96 against 360) and on alternating patterns (96 against 1256), and on random data (1112 against 1297). MeruCode is smaller on the 5% and 95% data (550 and 553 bits against 656 and 632), and also on the 5-letter `saket` (92 against 104 bits), where zlib's fixed overhead dominates. Both of its wins on tiny inputs are about overhead, not about a better method. Note that on `saket` MeruCode is smaller than zlib but still **larger than the raw 40 bits**, so it is not compression.
5. **Speed.** MeruCode in pure Python is slower than zlib, which is C code. For the sizes tested both finish in well under a millisecond.

**Conclusion for the problem statement:** the scheme is a correct, lossless *encoding*. It *compresses only skewed data* (mostly 0s or mostly 1s). It does not compress normal text, and it is not claimed to be better than standard compressors.

Why: the number of n-bit patterns is 2^n, and no scheme can give every pattern a shorter code. Grouping by k is useful only when the data is not uniform, so that small groups appear often.

---

## 10. Limitations and possible improvements

| Limitation | Possible improvement |
|---|---|
| The 40-bit header is large for short inputs | Use a variable-length header (for example, a length coded in 1 to 4 bytes) |
| k always costs `bit_length(n)` bits, even for all-zero blocks (visible in the "All zeros" row) | Code k with a shorter code for common values (Huffman or run-length of k) |
| Alternating `0101` has k = n/2 every time, so it does not compress although it is very regular | Add a delta or run-length step before the codec |
| Uses a single block size per stream | Choose the best block size automatically, then store it (the page already finds it, the encoder does not yet) |
| Python implementation is not optimised | Cache binomials, or use lookup tables for small n |
| Flask development server | Use gunicorn or waitress for deployment |

None of these change the correctness of the format described in Section 3.

---

## 11. Demo script and final checklist

**Demo (about 3 minutes)**

1. Tab 1: set n = 3 and show 8 patterns. Click `101` and show index 5. Highlight k = 2 and show C(3,2) = 3. Show the triangle row.
2. Tab 2: encode `saket` with block 8. Point to k = 5, rank 15 for `s`. Show 40 to 92 bits and the "ONLY ENCODES" verdict.
3. Tab 3: press **Sparse**. Show "COMPRESSES" and the bars. Press **Random** and show that it does not.
4. Tab 4: run the tests and show 14 / 14.
5. Say clearly: "This is our implementation inspired by Pingala. It is not a historical compression system, and it only compresses skewed data."

**Final checklist**

- [ ] Backend tests pass (`python -m unittest`, 28 tests)
- [ ] Frontend tests pass (Tab 4, 14 tests)
- [ ] `saket` shows 40 to 92 bits with ranks 15, 30, 12, 26, 33
- [ ] Sparse data shows COMPRESSES, random data shows ONLY ENCODES
- [ ] Banner about "team's implementation" is visible
- [ ] Size and time comparison against raw bits and zlib is shown

---

## 12. Full source code

All code below was run and tested as shown in Section 8.

### 12.1 `backend/requirements.txt`

```text
Flask>=3.0
```

### 12.2 `backend/core.py`

```python
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
```

### 12.3 `backend/bench.py`

```python
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
```

### 12.4 `backend/app.py`

```python
"""Flask API for MeruCode. Run: python app.py  ->  http://127.0.0.1:5000"""
import os
from flask import Flask, jsonify, request, send_from_directory

import core
from bench import compare

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.join(HERE, "..", "frontend")
app = Flask(__name__)
app.json.sort_keys = False
MAX_INPUT_BITS = 200000


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.errorhandler(core.MeruError)
def meru_error(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise core.MeruError("send a JSON object")
    return data


def _input_bits(data):
    """Accepts {"text": "..."} or {"bits": "0101"}; returns (bits, mode)."""
    if "bits" in data:
        bits, mode = data["bits"], "bits"
    elif "text" in data:
        if not isinstance(data["text"], str):
            raise core.MeruError("text must be a string")
        bits, mode = core.text_to_bits(data["text"]), "text"
    else:
        raise core.MeruError("give either text or bits")
    core._check_bits(bits)
    if len(bits) > MAX_INPUT_BITS:
        raise core.MeruError("input too long (max %d bits)" % MAX_INPUT_BITS)
    return bits, mode


def _block(data):
    b = data.get("block", 8)
    if not isinstance(b, int) or isinstance(b, bool):
        raise core.MeruError("block must be an integer")
    return b


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "name": "MeruCode", "header_bits": core.HEADER_BITS})


@app.get("/api/prastara")
def prastara():
    n = request.args.get("n", default=3, type=int)
    pats = core.prastara(n)
    return jsonify({"n": n, "count": len(pats), "patterns": pats,
                    "display": [p.replace("0", "L").replace("1", "G") for p in pats]})


@app.get("/api/meru")
def meru():
    rows = request.args.get("rows", default=9, type=int)
    return jsonify({"rows": core.meru_rows(rows)})


@app.get("/api/matra")
def matra():
    m = request.args.get("m", default=5, type=int)
    pats = core.matra_vritta(m)
    return jsonify({"matra": m, "count": len(pats), "patterns": pats})


@app.get("/api/uddishta")
def uddishta():
    p = request.args.get("pattern", "")
    return jsonify({"pattern": p, "index": core.uddishta(p)})


@app.get("/api/nashta")
def nashta():
    n = request.args.get("n", type=int)
    i = request.args.get("index", type=int)
    if n is None or i is None:
        raise core.MeruError("n and index are required")
    return jsonify({"n": n, "index": i, "pattern": core.nashta(n, i)})


@app.get("/api/presets")
def presets():
    return jsonify({k: v["label"] for k, v in core.PRESETS.items()})


@app.post("/api/generate")
def generate():
    d = _body()
    bits = core.make_preset(d.get("preset", "sparse"), int(d.get("length", 256)), int(d.get("seed", 42)))
    return jsonify({"bits": bits, "ones": bits.count("1"), "length": len(bits)})


@app.post("/api/encode")
def encode():
    d = _body()
    bits, mode = _input_bits(d)
    block = _block(d)
    enc, rows = core.encode(bits, block, detail=True)
    return jsonify({"mode": mode, "input_bits": len(bits), "block": block,
                    "header": enc[:core.HEADER_BITS], "blocks": rows,
                    "encoded": enc, "encoded_bits": len(enc)})


@app.post("/api/decode")
def decode():
    d = _body()
    enc = d.get("encoded", "")
    bits = core.decode(enc)
    out = {"bits": bits, "bit_length": len(bits)}
    if d.get("as_text"):
        out["text"] = core.bits_to_text(bits)
    return jsonify(out)


@app.post("/api/compare")
def compare_route():
    d = _body()
    bits, _ = _input_bits(d)
    return jsonify(compare(bits, _block(d)))


@app.get("/")
def index():
    return send_from_directory(FRONT, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
```

### 12.5 `backend/test_meru.py`

```python
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
```

### 12.6 `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeruCode - Pingala pattern encoder</title>
<style>
:root{--bg:#faf7f2;--card:#fff;--ink:#2b2118;--mute:#7a6a5a;--line:#e6dccd;--gold:#8a5a00;--acc:#b3541e;--ok:#2e7d32;--bad:#b3261e;--L:#dfeaf5;--G:#f6dcc8}
@media (prefers-color-scheme:dark){:root{--bg:#1a1511;--card:#241d17;--ink:#f1e8dc;--mute:#a8998a;--line:#3a2f26;--gold:#e0a84a;--acc:#e8814a;--ok:#6fcf7a;--bad:#ff8a80;--L:#26384a;--G:#4a3020}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 20px 8px;max-width:1000px;margin:auto}
h1{margin:0;font:700 28px Georgia,serif}
.sub{color:var(--mute);margin:2px 0 8px}
.note{border:1px solid var(--line);background:var(--card);border-radius:8px;padding:8px 12px;color:var(--mute);font-size:13px}
nav{display:flex;gap:6px;flex-wrap:wrap;max-width:1000px;margin:10px auto 0;padding:0 20px}
nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:8px 14px;border-radius:999px;cursor:pointer;font-size:14px}
nav button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
main{max-width:1000px;margin:12px auto 40px;padding:0 20px}
section{display:none;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}
section.on{display:block}
h2{margin:0 0 4px;font:600 18px Georgia,serif}
.hint{color:var(--mute);font-size:13px;margin:0 0 12px}
label{font-size:13px;color:var(--mute);margin-right:6px}
input,select,textarea{background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 9px;font:inherit}
textarea{width:100%;font-family:ui-monospace,Menlo,Consolas,monospace}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:8px 0}
button.go{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:8px 16px;cursor:pointer;font-size:14px}
button.alt{background:transparent;color:var(--acc);border:1px solid var(--acc);border-radius:8px;padding:7px 14px;cursor:pointer}
.grid{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.pat{font:13px ui-monospace,Menlo,monospace;padding:4px 8px;border-radius:6px;border:1px solid var(--line);display:flex;gap:1px;align-items:center}
.pat small{color:var(--mute);margin-right:6px;font-size:11px}
.s{display:inline-block;width:18px;text-align:center;border-radius:3px}
.s.L{background:var(--L)}.s.G{background:var(--G)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;font-family:ui-monospace,Menlo,monospace}
th{color:var(--mute);font-weight:600;font-family:system-ui}
.tri{text-align:center;margin-top:10px;overflow-x:auto}
.tri div{white-space:nowrap}
.tri span{display:inline-block;min-width:44px;padding:2px 4px;margin:1px;border-radius:5px;font:13px ui-monospace,monospace}
.tri span.hl{background:var(--G);font-weight:700}
.bits{word-break:break-all;font:13px ui-monospace,Menlo,monospace;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px;margin-top:6px}
.bits b.h{color:var(--gold)}.bits b.k{color:var(--acc)}.bits b.r{color:var(--ok)}
.verdict{margin-top:12px;padding:10px 12px;border-radius:8px;font-weight:600;border:1px solid}
.verdict.good{color:var(--ok)}.verdict.bad{color:var(--bad)}
.bar{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.bar .nm{width:110px;color:var(--mute)}
.bar .tr{flex:1;background:var(--bg);border-radius:6px;height:20px;overflow:hidden;border:1px solid var(--line)}
.bar .fl{height:100%;background:var(--acc)}
.bar .v{width:130px;font-family:ui-monospace,monospace}
.pass{color:var(--ok)}.fail{color:var(--bad)}
.err{color:var(--bad);font-size:13px;margin-top:6px}
.pill{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--mute)}
@media(max-width:600px){.bar .nm{width:70px}.bar .v{width:90px}}
</style>
</head>
<body>
<header>
  <h1>MeruCode</h1>
  <p class="sub">CSE-03 - Turn Pingala's patterns into a digital encoding system <span id="srv" class="pill">backend: checking</span></p>
  <div class="note">Method note: the (k, rank) block codec is <b>this team's own implementation</b>, inspired by Prastara, Meru Prastara, Uddishta and Nashta. It is not a historical Indian compression system, and it does not always compress.</div>
</header>
<nav id="tabs">
  <button data-t="gen" class="on">1. Pattern generator</button>
  <button data-t="enc">2. Encode / Decode</button>
  <button data-t="cmp">3. Compare</button>
  <button data-t="tst">4. Tests</button>
</nav>
<main>

<section id="gen" class="on">
  <h2>Prastara and Meru Prastara</h2>
  <p class="hint">L (laghu) = 0, G (guru) = 1. Click a pattern to see its Uddishta index. Row n of the triangle shows how many patterns have k gurus.</p>
  <div class="row">
    <label for="gn">Syllables n</label><input id="gn" type="number" min="1" max="8" value="4" style="width:70px">
    <label for="gk">Highlight k</label><select id="gk"></select>
    <label for="gm">Matra total</label><input id="gm" type="number" min="1" max="10" value="5" style="width:70px">
    <button class="alt" id="gmv">Show Matra-vritta</button>
  </div>
  <div id="gcount" class="hint"></div>
  <div id="ggrid" class="grid"></div>
  <div id="gsel" class="hint" style="margin-top:8px"></div>
  <h2 style="margin-top:16px">Meru Prastara (Pascal's triangle)</h2>
  <div id="gtri" class="tri"></div>
  <div id="gmatra"></div>
</section>

<section id="enc">
  <h2>Encode and decode</h2>
  <p class="hint">Each block of n bits becomes (k, rank). k = number of guru (1s). rank = position inside the group of patterns that have the same k.</p>
  <textarea id="ein" rows="3" placeholder="Type text or bits">saket</textarea>
  <div class="row">
    <label for="emode">Input is</label>
    <select id="emode"><option value="text">text</option><option value="bits">bits (0/1)</option></select>
    <label for="eblk">Block size</label><input id="eblk" type="number" min="1" max="64" value="8" style="width:70px">
    <label for="epre">Preset</label><select id="epre"></select>
    <button class="go" id="ego">Encode and decode</button>
  </div>
  <div id="eout"></div>
</section>

<section id="cmp">
  <h2>Does it compress, or only encode?</h2>
  <p class="hint">Baselines: raw bits and zlib (zlib comes from the Python backend, or the browser if it supports CompressionStream).</p>
  <div class="row">
    <button class="alt" data-p="text">Text "saket"</button>
    <button class="alt" data-p="sparse">Sparse</button>
    <button class="alt" data-p="mostly_ones">Dense</button>
    <button class="alt" data-p="balanced">Random</button>
    <button class="alt" data-p="all_zeros">All zeros</button>
    <label for="clen">Length (bits)</label><input id="clen" type="number" min="8" max="20000" value="1024" style="width:90px">
    <label for="cblk">Block</label><input id="cblk" type="number" min="1" max="64" value="16" style="width:70px">
  </div>
  <div id="cout"></div>
</section>

<section id="tst">
  <h2>Correctness tests (run in your browser)</h2>
  <p class="hint">Checks the JavaScript codec: roundtrips, golden vector for "saket", Mulberry32 values, corrupt-stream errors.</p>
  <button class="go" id="trun">Run tests</button>
  <div id="tout"></div>
</section>

</main>
<script>
// ==CORE==
// pure functions, no DOM; also unit-tested from node
const HEADER_BITS = 40;
const C = (() => { const memo = new Map();
  return (n, k) => { if (k < 0 || k > n) return 0n; if (k === 0 || k === n) return 1n;
    const key = n * 100 + k; if (memo.has(key)) return memo.get(key);
    const v = C(n - 1, k - 1) + C(n - 1, k); memo.set(key, v); return v; }; })();
const bw = (x) => x === 0n ? 0 : x.toString(2).length;           // bit width of a BigInt
const kWidth = (n) => n.toString(2).length;                       // bits to store k in 0..n
const rankWidth = (n, k) => bw(C(n, k) - 1n);
const pad = (v, w) => w === 0 ? "" : BigInt(v).toString(2).padStart(w, "0");
function prastara(n) { const out = []; for (let i = 0; i < 2 ** n; i++) out.push(i.toString(2).padStart(n, "0")); return out; }
function meruRows(r) { const rows = []; for (let i = 0; i < r; i++) { const row = []; for (let k = 0; k <= i; k++) row.push(C(i, k)); rows.push(row); } return rows; }
function matraVritta(m) { const out = []; (function go(left, acc) { if (left === 0) { out.push(acc); return; } go(left - 1, acc + "L"); if (left >= 2) go(left - 2, acc + "G"); })(m, ""); return out; }
function textToBits(t) { return Array.from(new TextEncoder().encode(t), b => b.toString(2).padStart(8, "0")).join(""); }
function bitsToText(b) { if (b.length % 8) throw new Error("bit length is not a multiple of 8"); const a = new Uint8Array(b.length / 8);
  for (let i = 0; i < a.length; i++) a[i] = parseInt(b.slice(i * 8, i * 8 + 8), 2);
  try { return new TextDecoder("utf-8", { fatal: true }).decode(a); } catch (e) { throw new Error("bits are not valid UTF-8 text"); } }
function rankBlock(blk) { const n = blk.length; let left = 0; for (const c of blk) if (c === "1") left++; const k = left; let r = 0n;
  for (let i = 0; i < n; i++) if (blk[i] === "1") { r += C(n - i - 1, left); left--; } return { k, r }; }
function unrankBlock(n, k, r) { if (k < 0 || k > n) throw new Error("invalid k " + k); if (r < 0n || r >= C(n, k)) throw new Error("invalid rank");
  let out = "", left = k; for (let i = 0; i < n; i++) { const c = C(n - i - 1, left); if (left > 0 && r >= c) { out += "1"; r -= c; left--; } else out += "0"; } return out; }
function encode(bits, block) {
  if (!/^[01]*$/.test(bits)) throw new Error("bits must contain only 0 and 1");
  if (!Number.isInteger(block) || block < 1 || block > 64) throw new Error("block size must be 1..64");
  const padded = bits + "0".repeat((block - bits.length % block) % block);
  let out = pad(bits.length, 32) + pad(block, 8); const rows = []; const kw = kWidth(block);
  for (let i = 0; i < padded.length; i += block) { const blk = padded.slice(i, i + block); const { k, r } = rankBlock(blk);
    const rw = rankWidth(block, k); const kb = pad(k, kw), rb = pad(r, rw); out += kb + rb;
    rows.push({ block: blk, k, rank: r, group: C(block, k), kb, rb, used: kw + rw }); }
  return { encoded: out, rows }; }
function decode(s) {
  if (!/^[01]*$/.test(s)) throw new Error("stream must contain only 0 and 1");
  if (s.length < HEADER_BITS) throw new Error("stream shorter than the 40-bit header");
  const total = parseInt(s.slice(0, 32), 2), block = parseInt(s.slice(32, 40), 2);
  if (block < 1 || block > 64) throw new Error("header has invalid block size");
  let pos = 40; const kw = kWidth(block); const nb = Math.ceil(total / block); let out = "";
  for (let i = 0; i < nb; i++) { if (pos + kw > s.length) throw new Error("stream ended while reading k");
    const k = parseInt(s.slice(pos, pos + kw), 2); pos += kw; if (k > block) throw new Error("k is larger than block size");
    const rw = rankWidth(block, k); if (pos + rw > s.length) throw new Error("stream ended while reading rank");
    const r = rw ? BigInt("0b" + s.slice(pos, pos + rw)) : 0n; pos += rw; out += unrankBlock(block, k, r); }
  if (pos !== s.length) throw new Error("extra bits after the last block");
  return out.slice(0, total); }
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const PRESETS = { sparse: 0.05, mostly_ones: 0.95, balanced: 0.5, all_zeros: 0 };
const PRESET_LABEL = { sparse: "Sparse (5% ones)", mostly_ones: "Dense (95% ones)", balanced: "Random (50% ones)", all_zeros: "All zeros", alternating: "Alternating 0101" };
function makePreset(name, length, seed) { if (name === "alternating") return "01".repeat(length).slice(0, length);
  const rnd = mulberry32(seed), d = PRESETS[name]; let s = ""; for (let i = 0; i < length; i++) s += rnd() < d ? "1" : "0"; return s; }
function verdict(raw, meru) { if (!raw) return { good: false, text: "empty input" };
  const pct = (100 * meru / raw).toFixed(1);
  return meru < raw ? { good: true, text: `COMPRESSES: ${raw} bits -> ${meru} bits (${pct}% of original)` }
                    : { good: false, text: `ONLY ENCODES: ${raw} bits -> ${meru} bits (${pct}% of original, larger)` }; }
// ==/CORE==

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
let API = null;                               // set to "" when same-origin backend answers
const spans = (p) => [...p].map(c => `<span class="s ${c === "1" ? "G" : "L"}">${c === "1" ? "G" : "L"}</span>`).join("");

// ---- tabs
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x === b));
  document.querySelectorAll("main section").forEach(s => s.classList.toggle("on", s.id === b.dataset.t)); });

// ---- 1. generator
function renderGen() {
  const n = Math.min(8, Math.max(1, +$("gn").value || 1));
  const ks = $("gk"); if (ks.options.length !== n + 2) { ks.innerHTML = `<option value="-1">all</option>` + Array.from({ length: n + 1 }, (_, i) => `<option value="${i}">${i}</option>`).join(""); }
  const k = +ks.value, all = prastara(n);
  const shown = all.map((p, i) => ({ p, i })).filter(o => k < 0 || [...o.p].filter(c => c === "1").length === k);
  $("gcount").textContent = `Sankhya: 2^${n} = ${2 ** n} patterns` + (k >= 0 ? `, ${shown.length} with exactly ${k} guru = C(${n},${k})` : "");
  $("ggrid").innerHTML = shown.map(o => `<div class="pat" data-i="${o.i}" style="cursor:pointer"><small>${o.i}</small>${spans(o.p)}</div>`).join("");
  $("ggrid").querySelectorAll(".pat").forEach(e => e.onclick = () => { const i = +e.dataset.i, p = all[i];
    $("gsel").textContent = `Uddishta: ${p} -> index ${i}.  Nashta: (n=${n}, index ${i}) -> ${p}`; });
  const rows = meruRows(Math.max(n + 1, 6));
  $("gtri").innerHTML = rows.map((r, ri) => `<div>${r.map((v, ki) => `<span class="${ri === n && (k < 0 || ki === k) ? "hl" : ""}">${v}</span>`).join("")}</div>`).join(""); }
$("gn").oninput = () => { $("gk").innerHTML = ""; renderGen(); }; $("gk").onchange = renderGen;
$("gmv").onclick = () => { const m = Math.min(10, Math.max(1, +$("gm").value || 1)), p = matraVritta(m);
  $("gmatra").innerHTML = `<h2 style="margin-top:16px">Matra-vritta, total ${m} matra: ${p.length} patterns (Fibonacci)</h2><div class="grid">` +
    p.map(x => `<div class="pat">${[...x].map(c => `<span class="s ${c}">${c}</span>`).join("")}</div>`).join("") + "</div>"; };

// ---- 2. encode / decode
$("epre").innerHTML = `<option value="">(none)</option>` + Object.entries(PRESET_LABEL).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
$("epre").onchange = () => { if (!$("epre").value) return; $("ein").value = makePreset($("epre").value, 96, 42); $("emode").value = "bits"; };
$("ego").onclick = () => { const out = $("eout");
  try {
    const raw = $("ein").value, mode = $("emode").value, block = +$("eblk").value;
    const bits = mode === "text" ? textToBits(raw) : raw.replace(/\s/g, "");
    const { encoded, rows } = encode(bits, block); const back = decode(encoded);
    const ok = back === bits, v = verdict(bits.length, encoded.length);
    const shownRows = rows.slice(0, 60);
    out.innerHTML = `<p class="hint">Input: ${bits.length} bits. Header (40 bits) = length (32) + block size (8). Per block: k (${kWidth(block)} bits) + rank (bits depend on C(${block},k)).</p>
      <table><tr><th>#</th><th>block</th><th>k</th><th>rank</th><th>group size</th><th>k bits</th><th>rank bits</th><th>used</th></tr>` +
      shownRows.map((r, i) => `<tr><td>${i + 1}</td><td>${r.block}</td><td>${r.k}</td><td>${r.rank}</td><td>${r.group}</td><td>${r.kb}</td><td>${r.rb || "-"}</td><td>${r.used}</td></tr>`).join("") +
      `</table>${rows.length > 60 ? `<p class="hint">Showing first 60 of ${rows.length} blocks.</p>` : ""}
      <div class="hint" style="margin-top:10px">Encoded stream (${encoded.length} bits)</div>
      <div class="bits"><b class="h">${encoded.slice(0, 40)}</b>${esc(encoded.slice(40))}</div>
      <div class="hint" style="margin-top:10px">Decoded: ${ok ? '<span class="pass">identical to input</span>' : '<span class="fail">MISMATCH</span>'}${mode === "text" && ok ? " -> " + esc(bitsToText(back)) : ""}</div>
      <div class="verdict ${v.good ? "good" : "bad"}">${v.text}</div>`;
  } catch (e) { out.innerHTML = `<div class="err">${esc(e.message)}</div>`; } };

// ---- 3. compare
async function zlibBits(bits) {
  if (API !== null) { try { const r = await fetch(API + "/api/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bits, block: 8 }) }); const j = await r.json(); return { bits: j.zlib_bits, t: j.time_ms.zlib_compress, src: "python zlib" }; } catch (e) { } }
  if (typeof CompressionStream === "undefined") return null;
  const bytes = new Uint8Array(Math.ceil(bits.length / 8)); for (let i = 0; i < bits.length; i++) if (bits[i] === "1") bytes[i >> 3] |= 128 >> (i & 7);
  const t0 = performance.now(); const cs = new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"));
  const buf = await new Response(cs).arrayBuffer(); return { bits: buf.byteLength * 8, t: performance.now() - t0, src: "browser deflate" }; }
function bar(name, val, max, extra) { return `<div class="bar"><span class="nm">${name}</span><span class="tr"><span class="fl" style="display:block;width:${Math.max(1, 100 * val / max)}%"></span></span><span class="v">${val} bits${extra || ""}</span></div>`; }
async function runCompare(preset) {
  const out = $("cout"); try {
    const len = Math.min(20000, Math.max(8, +$("clen").value || 1024)), block = +$("cblk").value || 8;
    const bits = preset === "text" ? textToBits("saket") : makePreset(preset, len, 42);
    const reps = 20; let t = performance.now(); let enc; for (let i = 0; i < reps; i++) enc = encode(bits, block).encoded; const te = (performance.now() - t) / reps;
    t = performance.now(); let dec; for (let i = 0; i < reps; i++) dec = decode(enc); const td = (performance.now() - t) / reps;
    const z = await zlibBits(bits), v = verdict(bits.length, enc.length);
    let best = null; for (const b of [2, 4, 8, 12, 16, 24, 32]) { const n = encode(bits, b).encoded.length; if (!best || n < best.n) best = { b, n }; }
    const max = Math.max(bits.length, enc.length, z ? z.bits : 0);
    out.innerHTML = `<p class="hint">Input: ${preset === "text" ? '"saket"' : PRESET_LABEL[preset]}, ${bits.length} bits, block ${block}. Roundtrip: ${dec === bits ? '<span class="pass">OK</span>' : '<span class="fail">FAILED</span>'}</p>` +
      bar("Raw bits", bits.length, max) + bar("MeruCode", enc.length, max, ` (${(100 * enc.length / bits.length).toFixed(0)}%)`) +
      (z ? bar("zlib", z.bits, max, "") : `<div class="hint">zlib not available (start the backend)</div>`) +
      `<div class="verdict ${v.good ? "good" : "bad"}">${v.text}</div>
      <table><tr><th>operation</th><th>time (ms, avg of ${reps})</th></tr><tr><td>MeruCode encode</td><td>${te.toFixed(3)}</td></tr><tr><td>MeruCode decode</td><td>${td.toFixed(3)}</td></tr>
      ${z ? `<tr><td>zlib compress (${z.src})</td><td>${z.t.toFixed(3)}</td></tr>` : ""}</table>
      <p class="hint">Best block size for this input: ${best.b} gives ${best.n} bits. The 40-bit header is included in every MeruCode number above.</p>`;
  } catch (e) { out.innerHTML = `<div class="err">${esc(e.message)}</div>`; } }
document.querySelectorAll("#cmp button[data-p]").forEach(b => b.onclick = () => runCompare(b.dataset.p));

// ---- 4. tests
const TESTS = [
  ["saket golden: 40 -> 92 bits", () => encode(textToBits("saket"), 8).encoded.length === 92],
  ["saket ranks 15,30,12,26,33", () => encode(textToBits("saket"), 8).rows.map(r => Number(r.rank)).join() === "15,30,12,26,33"],
  ["saket decodes to saket", () => bitsToText(decode(encode(textToBits("saket"), 8).encoded)) === "saket"],
  ["all 256 blocks roundtrip", () => { for (let v = 0; v < 256; v++) { const b = v.toString(2).padStart(8, "0"); const { k, r } = rankBlock(b); if (unrankBlock(8, k, r) !== b) return false; } return true; }],
  ["random roundtrip, many block sizes", () => { const rnd = mulberry32(5); for (let i = 0; i < 200; i++) { const n = Math.floor(rnd() * 200), bits = Array.from({ length: n }, () => rnd() < 0.5 ? "1" : "0").join(""), b = [1, 2, 3, 5, 8, 13, 16, 32, 64][Math.floor(rnd() * 9)]; if (decode(encode(bits, b).encoded) !== bits) return false; } return true; }],
  ["unicode text roundtrip", () => ["संस्कृत", "café 😀"].every(s => bitsToText(decode(encode(textToBits(s), 8).encoded)) === s)],
  ["empty input", () => decode(encode("", 8).encoded) === ""],
  ["Matra-vritta counts are Fibonacci", () => [1, 2, 3, 4, 5, 6].map(m => matraVritta(m).length).join() === "1,2,3,5,8,13"],
  ["Meru row 5 = 1,5,10,10,5,1", () => meruRows(6)[5].join() === "1,5,10,10,5,1"],
  ["Mulberry32 is deterministic", () => { const a = mulberry32(9), b = mulberry32(9); return a() === b() && a() === b(); }],
  ["sparse data compresses", () => encode(makePreset("sparse", 2048, 1), 16).encoded.length < 2048],
  ["random data does not compress", () => encode(makePreset("balanced", 2048, 1), 8).encoded.length >= 2048],
  ["corrupt stream throws", () => { const e = encode(textToBits("abc"), 8).encoded; for (const bad of [e.slice(0, -3), e + "0", e.slice(0, 20)]) { try { decode(bad); return false; } catch (x) { } } return true; }],
  ["bad input throws", () => { try { encode("012", 8); return false; } catch (e) { } try { encode("01", 0); return false; } catch (e) { } return true; }],
];
$("trun").onclick = () => { let pass = 0; $("tout").innerHTML = "<table>" + TESTS.map(([name, fn]) => { let ok = false; try { ok = fn(); } catch (e) { } if (ok) pass++;
  return `<tr><td class="${ok ? "pass" : "fail"}">${ok ? "PASS" : "FAIL"}</td><td>${name}</td></tr>`; }).join("") + `</table><p class="hint">${pass} / ${TESTS.length} passed</p>`; };

// ---- start
renderGen();
fetch("/api/health").then(r => r.json()).then(() => { API = ""; $("srv").textContent = "backend: connected"; }).catch(() => { $("srv").textContent = "backend: offline (frontend still works)"; });
</script>
</body>
</html>
```
