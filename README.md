# Yukti (युक्ति)

> **Turning Acharya Pingala's Combinatorics into a Safe, Fast, and Hardened Digital Bitstream Codec**  
> *Problem Category: CSE-03 (Intermediate) &bull; Indian Knowledge Systems &bull; Chhandas-Shastra*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Backend-Flask%203.0%2B-green?logo=flask)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Unit%20Tests-82%20Passing-brightgreen)](#-correctness--test-suite)
[![Parity](https://img.shields.io/badge/Node.js%20Parity-1000%2F1000%20Verified-blueviolet)](#-cross-language-parity-verification)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue?logo=githubactions)](#-ci--github-actions)
[![Container](https://img.shields.io/badge/Container-.meru%20v2%20CRC32-gold)](#-versioned-container-format-meru-v2)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 📌 Method Note & Historical Context

The $(k, \text{rank})$ block codec implemented in **Yukti** is **this team's own modern computer science design**, directly inspired by Acharya Pingala's *Chhandas-Shastra* (~3rd–2nd century BCE):
- **Prastara** (exhaustive binary enumeration)
- **Meru Prastara** (Pascal's triangle / binomial coefficients)
- **Uddishta** (ranking: pattern $\to$ index)
- **Nashta** (unranking: index $\to$ pattern)
- **Matra-vritta** (meter partitions constrained by total syllable weight $\to$ Fibonacci numbers)

> **Important Disclaimer:** This codec is **not** an ancient Indian compression algorithm, and this repository makes no claim that Pingala invented digital file compression. It is a scientifically rigorous demonstration of how Pingala's combinatorial concepts translate into modern digital bitstream serialization and combinatorial number systems (combinadics). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full proofs and entropy bounds.

---

## 🏛️ Pingala Vocabulary Mapped to Digital Code

In Sanskrit metrics, **Laghu (L)** denotes a short syllable (1 Matra) and **Guru (G)** denotes a long syllable (2 Matras). In digital computing, we represent $L = \text{`0`}$ and $G = \text{`1`}$.

| Classical Sanskrit Term | Mathematical Definition | Digital Computer Science Equivalent | Implementation |
| :--- | :--- | :--- | :--- |
| **Laghu (L) / Guru (G)** | Short (1 matra) / Long (2 matras) | Binary digits `0` and `1` | [`core.py`](backend/core.py) |
| **Prastara** (प्रस्तार) | Ordered expansion of all $2^n$ permutations | Complete truth table / $n$-bit state space | [`prastara(n)`](backend/core.py) |
| **Meru Prastara** (मेरु प्रस्तार) | "Staircase of Mount Meru" (Pascal's Triangle) | Precomputed binomial matrix $C(n, k)$ | [`meru_rows(rows)`](backend/core.py) |
| **Uddishta** (उद्दिष्ट) | Pattern $\to$ Index (Ranking) | **Encoding**: Combinadic rank inside the $k$-group | [`rank_block(block)`](backend/core.py) |
| **Nashta** (नष्ट) | Index $\to$ Pattern (Unranking) | **Decoding**: Reconstructing block from $(n, k, \text{rank})$ | [`unrank_block(n, k, r)`](backend/core.py) |
| **Matra-vritta** (मात्रावृत्त) | Meters with fixed total weight ($L=1, G=2$) | Sum-constrained partitions $\to$ Fibonacci counts | [`matra_vritta(m)`](backend/core.py) |
| **Sankhya** (संख्या) | Total count of all possible patterns | Cardinality of state space ($2^n$) | [`/api/info`](backend/app.py) |

---

## 📦 Versioned Container Format (.meru v2)

To ensure cryptographic-grade verification and protect against silent bitstream corruption, Yukti introduces the **.meru v2 container format**. The container prepends a 19-byte fixed verification header ahead of the packed combinadic payload.

### Binary Header Layout (19 Bytes)

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Magic "MERU" (4B)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Version (1B) |   Flags (1B)  |     Original Bit Length (4B)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ... (cont.)  | BlockSize(1B) |     Payload Bit Length (4B)   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ... (cont.)  |                 CRC-32 (4B)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ... (cont.)  |          Packed Bitstream Payload ...         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| Offset | Field Name | Type / Size | Value / Description |
| :--- | :--- | :--- | :--- |
| `0..3` | **Magic** | `char[4]` (4 bytes) | Fixed ASCII `b"MERU"` (`0x4D 0x45 0x52 0x55`) |
| `4` | **Version** | `uint8` (1 byte) | Container version (`0x02`) |
| `5` | **Flags** | `uint8` (1 byte) | Reserved feature flags (`0x00`) |
| `6..9` | **Original Bit Length** | `uint32` Big-Endian (4B) | Exact unpadded input bit count |
| `10` | **Block Size $n$** | `uint8` (1 byte) | Block size used for encoding ($1 \le n \le 64$) |
| `11..14`| **Payload Bit Length** | `uint32` Big-Endian (4B) | Total bit count of the combinadic stream |
| `15..18`| **Original CRC-32** | `uint32` Big-Endian (4B) | IEEE 802.3 standard CRC32 of original data |
| `19..` | **Payload** | `byte[]` (variable) | Byte-packed $(k, \text{rank})$ bitstream |

### Backward Compatibility & Auto-Detection
The decoder automatically differentiates between legacy v1 raw bitstreams and v2 containers:
- If stream starts with `b"MERU"`: decodes as v2 container and verifies CRC-32.
- Otherwise: parses as legacy 40-bit raw stream (`32-bit length + 8-bit block size`). Existing `.meru` files and endpoints work without changes.

---

## 🔒 Security, Guardrails & System Limits

All inputs are validated through central bounds checkers before memory allocation or execution.

| Parameter / Resource | Hard Limit | Enforcement Mechanism | Failure Response |
| :--- | :--- | :--- | :--- |
| **Max Request Body** | 1 MB ($1,048,576$ bytes) | `MAX_CONTENT_LENGTH` in Flask | `HTTP 413 Payload Too Large` |
| **Max Input Bits** | 200,000 bits | `_input_bits` validator | `HTTP 400 INPUT_TOO_LONG` |
| **Max Claimed Decode Bits** | 500,000 bits | Pre-allocation header guard | `HTTP 400 CLAIMED_LENGTH_TOO_LARGE` |
| **Block Size $n$** | $1 \le n \le 64$ | `_block` validator & `_check_bits` | `HTTP 400 BAD_BLOCK_SIZE` |
| **Max Matra $M$** | $1 \le M \le 16$ | `matra_vritta` bound | `HTTP 400 BAD_MATRA` |
| **Max Prastara $n$** | $0 \le n \le 16$ | `prastara` bound | `HTTP 400 VALUE_OUT_OF_RANGE` |
| **Rate Limit (Expensive)** | 120 req / min per IP | In-memory sliding window (`/api/compare`, `/api/sweep`, `/api/analyze`) | `HTTP 429 RATE_LIMIT_EXCEEDED` (`Retry-After: 60`) |
| **CORS Origins** | Configurable | `ALLOWED_ORIGINS` env var (default: localhost & same origin) | Restricted headers |

---

## ⚠️ Structured Machine-Readable Error Codes

All errors return JSON in the standardized schema:
```json
{
  "error": {
    "code": "BAD_BLOCK_SIZE",
    "message": "block size must be between 1 and 64",
    "field": "block",
    "position": 32
  }
}
```

| Error Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `BAD_BLOCK_SIZE` | 400 | Block size outside $[1, 64]$ |
| `CLAIMED_LENGTH_TOO_LARGE` | 400 | Header claimed length exceeds `MAX_OUTPUT_BITS` (fails before allocating) |
| `STREAM_TRUNCATED` | 400 | Stream is shorter than minimum required for claimed blocks |
| `HEADER_TOO_SHORT` | 400 | Stream is shorter than 40-bit header |
| `K_EXCEEDS_BLOCK` | 400 | Decoded $k > n$ for a block |
| `RANK_OUT_OF_RANGE` | 400 | Decoded rank $r \ge \binom{n}{k}$ |
| `TRAILING_BITS` | 400 | Stream contains unparsed trailing garbage after all blocks |
| `CHECKSUM_MISMATCH` | 400 | Decoded data CRC32 does not match container header |
| `CONTAINER_TOO_SHORT` | 400 | Container data shorter than 19-byte header |
| `UNSUPPORTED_VERSION` | 400 | Container version not supported |
| `INVALID_BITS` | 400 | String contains characters other than `'0'` and `'1'` |
| `INVALID_TYPE` | 400 | Invalid JSON type (e.g. boolean passed as integer) |
| `MISSING_PARAMETER` | 400 | Required query or JSON parameter omitted |
| `NOT_FOUND` | 404 | Endpoint does not exist |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not permitted on endpoint |
| `PAYLOAD_TOO_LARGE` | 413 | Request body exceeds 1 MB limit |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Content-Type is not `application/json` |
| `RATE_LIMIT_EXCEEDED` | 429 | IP request rate exceeded for expensive endpoint |
| `INTERNAL_ERROR` | 500 | Unhandled generic error (no stack trace leaked) |

---

## 🔬 Benchmark Results

Full benchmarks comparing Yukti against raw stream, DEFLATE (`zlib -9`), Gzip, Bzip2, LZMA, and Run-Length Encoding (RLE). Reproduced from [`docs/benchmarks.md`](docs/benchmarks.md):

| Scale | Distribution | Raw (bits) | Yukti (bits) | Ratio | zlib (bits) | RLE (bits) | Best Block | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Kbit** | Sparse (5% ones) | 1,024 | 550 | **53.7%** | 656 | 1,632 | Block 64 | **COMPRESSES** |
| **1 Kbit** | Dense (95% ones) | 1,024 | 553 | **54.0%** | 632 | 1,552 | Block 64 | **COMPRESSES** |
| **1 Kbit** | Random (50% ones) | 1,024 | 1,209 | **118.1%** | 1,112 | 8,224 | Block 64 | **EXPANDS** |
| **1 Kbit** | All Zeros | 1,024 | 360 | **35.2%** | 96 | 16 | Block 64 | **COMPRESSES** |
| **64 Kbit** | Sparse (5% ones) | 65,536 | 32,416 | **49.5%** | 24,296 | 98,512 | Block 64 | **COMPRESSES** |
| **64 Kbit** | Dense (95% ones) | 65,536 | 32,601 | **49.8%** | 24,768 | 100,112 | Block 64 | **COMPRESSES** |
| **64 Kbit** | Random (50% ones) | 65,536 | 75,236 | **114.8%** | 65,624 | 526,736 | Block 64 | **EXPANDS** |
| **64 Kbit** | All Zeros | 65,536 | 20,520 | **31.3%** | 248 | 16 | Block 64 | **COMPRESSES** |

> **Scientific Finding:** MeruCode compresses low-entropy distributions (sparse, dense, run-heavy) down to ~35%–53% of original size. On random noise ($p=0.5$), it provably expands by ~15% due to header and combinadic representation bounds.

---

## 🔌 Complete REST API Reference

Interactive HTML docs available at `GET /api/docs`. Machine-readable schema at `GET /api/info`.

### Core Codec Endpoints

#### `POST /api/encode`
Encodes a bitstring or UTF-8 text into a MeruCode stream.
- **Request:**
  ```json
  {"text": "saket", "block": 8}
  ```
- **Response:**
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
      {
        "block": "01100001",
        "k": 3,
        "rank": 30,
        "group_size": 56,
        "k_bits": "0011",
        "rank_bits": "011110",
        "bits_used": 10
      },
      {
        "block": "01101011",
        "k": 5,
        "rank": 12,
        "group_size": 56,
        "k_bits": "0101",
        "rank_bits": "001100",
        "bits_used": 10
      },
      {
        "block": "01100101",
        "k": 4,
        "rank": 26,
        "group_size": 70,
        "k_bits": "0100",
        "rank_bits": "0011010",
        "bits_used": 11
      },
      {
        "block": "01110100",
        "k": 4,
        "rank": 33,
        "group_size": 70,
        "k_bits": "0100",
        "rank_bits": "0100001",
        "bits_used": 11
      }
    ],
    "encoded": "00000000000000000000000000101000000010000101001111001101111001010011000100001101001000100001",
    "encoded_bits": 92
  }
  ```

#### `POST /api/decode`
Decodes an encoded bitstream back into raw bits or text.
- **Request:**
  ```json
  {"encoded": "00000000000000000000000000101000000010000101001111001101111001010011000100001101001000100001", "as_text": true}
  ```
- **Response:**
  ```json
  {
    "bits": "0111001101100001011010110110010101110100",
    "bit_length": 40,
    "text": "saket"
  }
  ```

#### `POST /api/pack`
Creates a `.meru v2` container with CRC-32 integrity validation.
- **Request:**
  ```json
  {"text": "saket", "block": 8}
  ```
- **Response:**
  ```json
  {
    "version": 2,
    "container_base64": "TUVSVQIAAAAAKAgAAAA08KrzYlPN5TENIhA=",
    "container_bytes": 26,
    "original_bits": 40,
    "block": 8,
    "crc32": "0xf0aaf362"
  }
  ```

#### `POST /api/unpack`
Decodes a `.meru v2` container, verifying CRC-32 integrity.
- **Request:**
  ```json
  {"container_base64": "TUVSVQIAAAAAKAgAAAA08KrzYlPN5TENIhA=", "as_text": true}
  ```
- **Response:**
  ```json
  {
    "bits": "0111001101100001011010110110010101110100",
    "bit_length": 40,
    "version": 2,
    "crc_verified": true,
    "crc32": "0xf0aaf362",
    "text": "saket"
  }
  ```

### Analysis & Interactive UI Endpoints

#### `POST /api/trace`
Step-by-step block ranking walk with active binomial terms.
- **Request:**
  ```json
  {"bits": "10110", "block": 5}
  ```
- **Response:**
  ```json
  {
    "total_bits": 5,
    "block_size": 5,
    "total_blocks": 1,
    "traced_blocks": 1,
    "blocks": [
      {
        "block": "10110",
        "k": 3,
        "rank": 6,
        "k_bits": 3,
        "rank_bits": 4,
        "binomial_terms": [
          {"pos": 0, "bit": "1", "n": 4, "left": 3, "value": 4, "running_sum": 4},
          {"pos": 1, "bit": "0", "n": 3, "left": 2, "value": 0, "running_sum": 4},
          {"pos": 2, "bit": "1", "n": 2, "left": 2, "value": 1, "running_sum": 5},
          {"pos": 3, "bit": "1", "n": 1, "left": 1, "value": 1, "running_sum": 6},
          {"pos": 4, "bit": "0", "n": 0, "left": 0, "value": 0, "running_sum": 6}
        ],
        "running_sum": 6
      }
    ],
    "mode": "bits"
  }
  ```

#### `POST /api/sweep`
Generates block size vs. compression ratio grid for heatmaps.
- **Request:**
  ```json
  {"density": 0.05, "length": 1024, "block_min": 4, "block_max": 16, "step": 4}
  ```
- **Response:**
  ```json
  {
    "density": 0.05,
    "length": 1024,
    "seed": 42,
    "points": [
      {"block": 4, "encoded_bits": 908, "ratio": 0.8867, "compresses": true},
      {"block": 8, "encoded_bits": 696, "ratio": 0.6797, "compresses": true},
      {"block": 12, "encoded_bits": 572, "ratio": 0.5586, "compresses": true},
      {"block": 16, "encoded_bits": 550, "ratio": 0.5371, "compresses": true}
    ]
  }
  ```

#### `POST /api/analyze`
Computes empirical Shannon entropy $H(p)$ and theoretical minimum size.
- **Request:**
  ```json
  {"bits": "00000000000000000000000010000000", "block": 8}
  ```
- **Response:**
  ```json
  {
    "n_bits": 32,
    "ones": 1,
    "zeros": 31,
    "p1": 0.03125,
    "p0": 0.96875,
    "shannon_entropy_per_bit": 0.20062,
    "theoretical_min_bits": 7,
    "meru_bits": 59,
    "meru_block": 8,
    "meru_gap_bits": 52,
    "meru_gap_pct": 819.02,
    "zlib_bits": 96,
    "zlib_gap_bits": 89,
    "explanation": "Shannon entropy H(p) = 0.2006 bits/symbol. MeruCode encodes each block of size 8 using k_bits + log2(C(n,k)). As block size grows, log2(C(n, pn)) / n -> H(p). For low entropy (sparse/dense), MeruCode compresses toward the Shannon limit. For Bernoulli(0.5) random noise, H(p) = 1.0 and any lossless code with headers expands."
  }
  ```

#### `POST /api/corrupt`
Simulates bit-flip corruption and returns structured error or diff.
- **Request:**
  ```json
  {"encoded": "00000000000000000000000000101000000010000101001111001101111001010011000100001101001000100001", "position": 10}
  ```
- **Response (on error detection):**
  ```json
  {
    "flipped_position": 10,
    "original_bit": "0",
    "flipped_bit": "1",
    "success": false,
    "error": {
      "code": "CLAIMED_LENGTH_TOO_LARGE",
      "message": "claimed output bit length exceeds maximum limit",
      "position": 0
    }
  }
  ```

#### `POST /api/compare`
Benchmarks input against zlib, gzip, bzip2, lzma, and RLE.
- **Request:**
  ```json
  {"text": "saket", "block": 8}
  ```

### Classical Pingala Combinatorics Endpoints

- `GET /api/prastara?n=4`: Returns all $2^n$ binary syllable permutations.
- `GET /api/meru?rows=9`: Returns Pascal triangle binomial rows.
- `GET /api/matra?m=5`: Returns meter combinations for total weight $m$ (Fibonacci).
- `GET /api/nashta?n=4&index=5`: Unranks index $\to$ pattern.
- `GET /api/uddishta?pattern=0101`: Ranks pattern $\to$ index.
- `GET /api/presets`: Returns available PRNG preset names and labels.
- `POST /api/generate`: Generates deterministic PRNG bitstreams (`preset`, `length`, `seed`).
- `GET /api/health`: Uptime, version, and server health.
- `GET /api/info`: Machine-readable endpoint catalog, limits, and header specifications.
- `GET /api/docs`: Interactive HTML documentation.

---

## 🧪 Correctness & Test Suite

The test suite contains **82 comprehensive unit, property, and parity tests**:
- **Classical Metrics**: Prastara $2^n$ growth, Meru symmetry, Matra Fibonacci counts.
- **Combinadics**: Invertibility of Uddishta/Nashta across all block sizes $1 \le n \le 64$.
- **Exhaustive Block Testing**: All 8,190 patterns exhaustively verified for $n \in [1, 12]$, plus boundary testing for $n \in [13, 16]$.
- **Hypothesis Property Tests**: Roundtrip on arbitrary bit strings, block sizes $1..64$, size formula exactness, and crash-proof decode safety.
- **Fuzz Testing**: 700 iterations of random bitstream garbage, truncations, and bit-flips; asserts `decode()` always raises `MeruError` or succeeds, never hanging or leaking unbounded memory.
- **Golden Vectors (`tests/golden.json`)**: Verifies saket, empty string, 1-bit, all zeros, all ones, Devanagari Sanskrit text, and 64-bit blocks.
- **Cross-Language Parity (`tests/parity_test.js`)**: 1,000 random test vectors verified bit-for-bit between Python backend and vanilla JavaScript frontend.
- **Mutation Sanity**: Off-by-one intentional mutation on `rank_block` verified to fail tests.

### Running Tests Locally

Run the all-in-one verification suite in a single command:
```powershell
python run_tests.py
```
Output:
```text
============================================================
Yukti - Unified Quality & Parity Test Harness
============================================================

[1/3] Running Ruff Linter...
PASS: Ruff check clean (0.23s)

[2/3] Running Python Unit & Hypothesis Tests (82 tests)...
PASS: 82/82 Python unit tests passed (4.75s)

[3/3] Running Cross-Language JS/Python Parity Tests (1,000 cases)...
PASS: 1,000/1,000 random vectors & 10 golden vectors verified (0.52s)

============================================================
PASS: 82/82 Python tests | 1,000/1,000 JS parity | Ruff clean
============================================================
```

Or run individual test suites:
```powershell
# Python unit & hypothesis tests
cd backend && python -m unittest test_meru.py -v

# Cross-language bit-for-bit parity
node tests/parity_test.js

# Ruff code style
python -m ruff check .
```

---

## 🚀 Deployment & Operations

### Local Execution
```powershell
pip install -r requirements.txt
python backend/app.py
```
Open **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)** in your browser.

### Docker
```bash
docker build -t yukti .
docker run -p 5000:5000 yukti
```

### Production Host (Render, Railway, Heroku)
The project includes a `Procfile` (`web: python backend/app.py`) and reads `HOST`, `PORT`, and `ALLOWED_ORIGINS` from environment variables with safe defaults.

---

## 🛡️ What This Does and Does Not Guarantee

### Guarantees
1. **100% Lossless Reconstruction**: For any bitstream encoded by Yukti, the decoder reconstructs the exact original bitstream without loss.
2. **Accidental Corruption Detection**: The `.meru v2` container guarantees detection of unintentional bit flips, header truncations, and data transmission errors via CRC-32 verification.
3. **Bounded Memory & Crash Safety**: Untrusted inputs can never trigger an uncaught exception, a 500 status code, or unbounded memory allocations. Claimed lengths are validated prior to allocation.
4. **Deterministic Cross-Platform Parity**: The Python backend and JavaScript frontend produce bit-for-bit identical bitstreams for all inputs.

### Non-Guarantees
1. **Not a Cryptographic System**: CRC-32 does NOT provide cryptographic authentication or tamper resistance against malicious adversaries who can recompute the CRC.
2. **Universal Compression is Mathematically Impossible**: In accordance with Shannon's Source Coding Theorem, random noise and balanced ASCII text will expand. Compression is achieved only on low-entropy and skewed distributions.

---

## 📄 License
MIT License. Open-source for academic and competition evaluation.
