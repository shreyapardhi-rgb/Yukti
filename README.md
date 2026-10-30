# Yukti (युक्ति)

> **Turning Acharya Pingala's Combinatorics into a Digital Encoding System**  
> *Problem Category: CSE-03 (Intermediate) &bull; Indian Knowledge Systems &bull; Chhandas-Shastra*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Backend-Flask-green?logo=flask)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Unit%20Tests-28%2F28%20Passing-brightgreen)](#correctness--test-suite)
[![Theme](https://img.shields.io/badge/UI-Light%20%2F%20Dark%20Adaptive-gold)](#user-interface--features)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 📌 Method Note & Historical Context

The $(k, \text{rank})$ block codec implemented in **Yukti** is **this team's own modern computer science design**, directly inspired by Acharya Pingala's *Chhandas-Shastra* (~3rd–2nd century BCE):
- **Prastara** (exhaustive binary enumeration)
- **Meru Prastara** (Pascal's triangle / binomial coefficients)
- **Uddishta** (ranking: pattern $\to$ index)
- **Nashta** (unranking: index $\to$ pattern)
- **Matra-vritta** (meter partitions constrained by total syllable weight $\to$ Fibonacci numbers)

> **Important Disclaimer:** This codec is **not** an ancient Indian compression algorithm, and this repository makes no claim that Pingala invented digital file compression. It is a scientifically rigorous demonstration of how Pingala's combinatorial concepts translate into modern digital bitstream serialization and combinatorial number systems (combinadics).

---

## 🏛️ Pingala Vocabulary Mapped to Digital Code

In Sanskrit metrics, **Laghu (L)** denotes a short syllable (1 Matra) and **Guru (G)** denotes a long syllable (2 Matras). In digital computing, we represent $L = \text{`0`}$ and $G = \text{`1`}$.

| Classical Sanskrit Term | Mathematical Definition | Digital Computer Science Equivalent | Implementation |
| :--- | :--- | :--- | :--- |
| **Laghu (L) / Guru (G)** | Short (1 matra) / Long (2 matras) | Binary digits `0` and `1` | `core.py` |
| **Prastara** (प्रस्तार) | Ordered expansion of all $2^n$ permutations | Complete truth table / $n$-bit state space | [`prastara(n)`](backend/core.py) |
| **Meru Prastara** (मेरु प्रस्तार) | "Staircase of Mount Meru" (Pascal's Triangle) | Binomial coefficients $C(n, k)$ grouping patterns with $k$ ones | [`meru_rows(rows)`](backend/core.py) |
| **Uddishta** (उद्दिष्ट) | Pattern $\to$ Index (Ranking) | **Encoding**: Combinadic rank inside the $k$-group | [`rank_block(block)`](backend/core.py) |
| **Nashta** (नष्ट) | Index $\to$ Pattern (Unranking) | **Decoding**: Reconstructing block from $(n, k, \text{rank})$ | [`unrank_block(n, k, r)`](backend/core.py) |
| **Matra-vritta** (मात्रावृत्त) | Meters with fixed total weight ($L=1, G=2$) | Sum-constrained partitions $\to$ Fibonacci counts | [`matra_vritta(m)`](backend/core.py) |
| **Sankhya** (संख्या) | Total count of all possible patterns | Cardinality of state space ($2^n$) | UI Tab 1 |

---

## ⚙️ The Encoding Scheme (Exact Bit Layout)

Yukti breaks input bitstreams into blocks of size $n$ ($1 \le n \le 64$) and encodes each block by its guru count $k$ and its combinadic rank within that $k$-group:

```text
|---------------------- 40-bit Header ----------------------|------------------- Block Payload -------------------|
|   Input Length (32 bits)   |   Block Size n (8 bits)   | Block 1 (k, rank) | Block 2 (k, rank) | ...             |
```

### 1. Header (40 bits)
- **Length (32 bits)**: Exact bit length of the unpadded input (enables 100% lossless trimming of padding bits).
- **Block size $n$ (8 bits)**: $1 \le n \le 64$ (default $n=8$).

### 2. Per-Block Payload
For each $n$-bit block:
- **$k$ field**: Bit width $= \lceil \log_2(n + 1) \rceil$ (e.g., 4 bits for $n=8$).
- **$\text{rank}$ field**: Bit width $= \lceil \log_2(C(n, k)) \rceil$ bits (uses 0 bits when $C(n, k) = 1$, i.e., all zeros or all ones).
- **Total bitstream formula**:
  $$\text{Total Bits} = 40 + \sum_{\text{blocks}} \left( \lceil \log_2(n + 1) \rceil + \lceil \log_2(C(n, k)) \rceil \right)$$

---

## 🔬 Scientific Comparison: Compression vs. Expansion

Information theory (Shannon entropy) dictates that no lossless algorithm can compress every possible input string. Yukti provides an honest, measured analysis:

| Data Type / Distribution | Characteristic | Yukti Result | Why? |
| :--- | :--- | :--- | :--- |
| **Sparse (e.g. 5% ones)** | Skewed ($p \approx 0.05$) | **COMPRESSES** | Most blocks have $k=0$ or $k=1$. $C(8, 0)=1$ (0 rank bits) and $C(8, 1)=8$ (3 rank bits). Total per block is much less than 8 bits. |
| **Dense (e.g. 95% ones)** | Skewed ($p \approx 0.95$) | **COMPRESSES** | Symmetric to sparse data; very few rank bits required. |
| **All Zeros / All Ones** | Extreme skew ($p=0$ or $1$) | **COMPRESSES** | Only needs 4 bits per 8-bit block ($50\%$ compression). |
| **Standard Text (`"saket"`)** | Balanced / Mixed ($k \approx 4$) | **ONLY ENCODES (Expands)** | For $n=8, k=4$, $C(8, 4)=70$, requiring 7 rank bits $+ 4$ $k$-bits $= 11$ bits/block, plus 40-bit header. |
| **Random Data (50% ones)** | Maximum Entropy ($H(p) = 1.0$) | **ONLY ENCODES (Expands)** | Shannon limit prevents compression of incompressible white noise. |

---

## 📁 Repository Structure

```text
Yukti/
├── backend/
│   ├── app.py                     # Flask REST API + static file server
│   ├── bench.py                   # Benchmarking against raw bits and zlib (Deflate level 9)
│   ├── core.py                    # Core codec, Pingala combinadics, PRNG presets
│   ├── requirements.txt           # Python dependencies (Flask >= 3.0)
│   └── test_meru.py               # 28 automated unit tests (codec, stream, API)
├── frontend/
│   └── index.html                 # Single-file modern UI with Light/Dark themes and Web Audio API
├── MeruCode_Frontend_Backend.md   # Detailed mathematical & architectural documentation (1,442 lines)
└── README.md                      # Project overview and quickstart guide
```

---

## 🚀 Quickstart & How to Run Locally

### Prerequisites
- Python 3.10 or higher
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Install Dependencies
```powershell
cd backend
pip install -r requirements.txt
```

### 2. Run the Local Server
```powershell
python app.py
```
Open **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)** in your web browser.

> **Offline Mode Note:** The frontend ([`frontend/index.html`](frontend/index.html)) is completely self-contained. You can double-click and open it directly in any browser without Python running; the full encoding, decoding, and audio synthesizer run client-side using built-in JavaScript and Web Audio API!

---

## 🎨 User Interface & Features

- **Light & Dark Themes**: High-contrast, Vedic parchment theme enabled by default, with an instant toggle for dark mode.
- **Tab 1 — Pattern Generator**:
  - Interactive *Prastara* list for $n \le 8$.
  - Interactive *Meru Prastara* pyramid with real-time $k$-group highlighting.
  - *Matra-vritta* partition generator displaying Fibonacci sequence growth.
  - **Acoustic Chhandas Engine**: Synthesizes classical rhythmic prosody using Web Audio API oscillators (Laghu = 1 beat, Guru = 2 beats).
  - Classical Vedic meter presets (*Gayatri*, *Anushtubh*, *Trishtubh*, *Jagati*).
- **Tab 2 — Encode / Decode & Files**:
  - Real-time text (UTF-8) and binary bitstream encoding.
  - Step-by-step block trace table showing $(k, \text{rank})$ and bit allocation.
  - Drag-and-drop file encoder and `.meru` container archive export.
- **Tab 3 — Scientific Comparison**:
  - Benchmarks execution time (ms) and storage against Raw bits and `zlib` (Deflate level 9).
  - Real-time HTML5 Canvas plotting data density against the Shannon Entropy curve $H(p)$.
  - Automatic optimal block size finder ($n \in \{2, 4, 8, 12, 16, 24, 32\}$).
- **Tab 4 — In-Browser Correctness Tests**:
  - 14 client-side unit tests verifying roundtrips, edge cases, and golden test vectors.

---

## 🧪 Correctness & Test Suite

The test suite covers:
- Pingala combinatorial counts ($2^n$) and Fibonacci Matra-vritta verification
- All 256 8-bit blocks roundtrip validation
- Saket golden vector verification ($40 \to 92$ bits)
- Multilingual Unicode UTF-8 roundtrips (e.g., Sanskrit Devanagari `संस्कृत`, emojis `café 😀`)
- Corrupt and truncated bitstream rejection

Run the backend unit test suite:
```powershell
cd backend
python -m unittest test_meru.py
```
```text
............................
----------------------------------------------------------------------
Ran 28 tests in 0.13s

OK
```

---

## 🔌 REST API Reference

| Endpoint | Method | Parameters / Body | Description |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | — | Server health check and header specification |
| `/api/prastara` | `GET` | `?n=3` | Returns all $2^n$ binary syllable patterns |
| `/api/meru` | `GET` | `?rows=9` | Returns Pascal's triangle binomial rows $C(r, k)$ |
| `/api/matra` | `GET` | `?m=5` | Returns meters with $m$ total matras (Fibonacci) |
| `/api/uddishta` | `GET` | `?pattern=101` | Computes index/rank from binary pattern |
| `/api/nashta` | `GET` | `?n=3&index=5` | Computes pattern from syllable length and index |
| `/api/presets` | `GET` | — | Returns available PRNG benchmark presets |
| `/api/generate`| `POST`| `{"preset": "sparse", "length": 256}` | Generates deterministic synthetic bitstream |
| `/api/encode` | `POST` | `{"text": "saket", "block": 8}` | Returns encoded stream and per-block $(k, \text{rank})$ |
| `/api/decode` | `POST` | `{"encoded": "...", "as_text": true}` | Decodes bitstream back to text or raw bits |
| `/api/compare`| `POST` | `{"bits": "...", "block": 8}` | Benchmarks vs raw bits and zlib |

---

## 🎮 Interactive Features Guide (90-Second Judge Experience)

Yukti transforms what used to be a static form-and-table app into a tactile, exploratory scientific demonstration:

1. **⚡ 90-Second Judge Tour (`Start Tour` in header)**:
   - A guided 6-step walkthrough taking evaluators from Pingala's prosodic metrics to live combinadic block ranking, reverse unranking, density sweep against the Shannon limit, and a final plain-language results card.
2. **🎭 Encoding Theatre (Signature Feature)**:
   - Block-by-block visual animation lifting syllables into Laghu/Guru tiles, ticking Guru counts $k$, and walking through the Mount Meru staircase to highlight active binomial terms $C(n-1-i, \text{left})$ in real-time.
   - Includes transport controls (Play, Pause, Step forward/back, scrubber, speed), live Bits-In vs Bits-Out ratio gauge, and reverse Nashta decoding playback.
3. **🔺 Interactive Mount Meru Playground**:
   - Hover any cell to observe Pascal's parent addition rule ($C(n,k) = C(n-1, k-1) + C(n-1, k)$).
   - Toggle overlays for Fibonacci diagonals (Matra-vritta), row sums ($2^n$), and the symmetry axis.
   - Click any cell to inspect all $C(n, k)$ patterns in rank order and perform live Uddishta/Nashta unranking.
4. **🧪 Bitstream Corruption Lab**:
   - Flip any single bit in the 40-bit header or block payloads to observe mathematical syntax errors or corrupted decodes in real time.
   - Highlights how combinadics inherently detect boundary violations without dedicated parity bits.
5. **📊 Density Playground & Block-Size Heatmap**:
   - Live Guru density slider $p \in [0, 1]$ generates dynamic synthetic streams and plots an animated tracer dot along Shannon's theoretical entropy curve $H(p)$.
   - Interactive 2D heatmap ($p \times n$) displays compression ratios across block sizes $n \in [4..64]$. Clicking any cell instantly configures the codec.
6. **🎵 Acoustic Pattern Composer**:
   - Tappable Laghu and Guru pads (plus keyboard keys <kbd>L</kbd> and <kbd>G</kbd>) with real-time syllable counts, matras, Uddishta index, and synchronized Web Audio playhead animations.
   - "Chant Encoded Stream" mode sonifies the compressed bitstream.
7. **📸 Export & URL State Sync**:
   - URL hash state (`#tab=...&input=...&blk=...&p=...`) allows deep-linking and state preservation.
   - Export high-resolution PNG snapshots of the Theatre frame or test verification suite for report submission.

---

## 📝 CHANGELOG

### Version 2.0.0 — Hackathon Interactive Overhaul
- **Project Rebranding**: Renamed from MeruCode to **Yukti** across backend, frontend, API, and documentation.
- **Design System & Theme**: Warm ivory / terracotta / Vedic gold color palette with dual-mode CSS tokens and persistent Light/Dark theme toggle.
- **Encoding Theatre**: Introduced block carousel, animated syllable tiles, Guru counter, combinadic formula display, and mini-Meru walk synchronization.
- **Live Mode**: Integrated 150ms debounced auto-encoding with real-time compression verdict chip and entropy explanation.
- **Corruption Lab**: Added interactive bit flipper grid with combinadic boundary error detection and byte diff viewer.
- **Density Playground**: Added Shannon entropy canvas with live tracer dot and interactive block-size sweep heatmap.
- **Pattern Composer**: Built Web Audio prosodic synthesizer with synchronized playhead animation, Vedic presets, and keyboard controls.
- **Judge Tour**: Built 90-second automated interactive tour dock and final evaluation modal.
- **Verification**: Verified 100% pass rate on all 28 Python unit tests and 14 in-browser automated tests.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).

