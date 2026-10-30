# Yukti (MeruCode) - Architecture & Scientific Basis

> **Formal Mathematical and Engineering Specification**  
> *Lossless Combinatorial Bitstream Codec Inspired by Pingala's Chhandas-Shastra*

---

## 1. Classical Sanskrit Combinatorics to Computer Science Mapping

Acharya Pingala's *Chhandas-Shastra* (~3rd–2nd century BCE) investigated combinatorial patterns in Sanskrit prosodic meters. In Indian metrics, syllables are categorized as **Laghu (L)** (light/short, metric weight 1) or **Guru (G)** (heavy/long, metric weight 2).

In **Yukti**, this foundational taxonomy maps directly to digital binary computing:

$$\text{Laghu (L)} \equiv \mathtt{0}, \quad \text{Guru (G)} \equiv \mathtt{1}$$

| Classical Sanskrit Term | Classical Definition | Modern Combinatorial Definition | Yukti Implementation |
| :--- | :--- | :--- | :--- |
| **Prastara (प्रस्तार)** | Systematic enumeration of all combinations of $n$ syllables | Complete enumeration of the $2^n$ boolean hypercube $\{0, 1\}^n$ | [`prastara(n)`](file:///backend/core.py) |
| **Meru Prastara (मेरु प्रस्तार)** | "Staircase of Mount Meru" (Pascal's triangle) | Binomial coefficients $\binom{n}{k} = \frac{n!}{k!(n-k)!}$ | [`meru_rows(r)`](file:///backend/core.py), `_BINOMIAL_TABLE` |
| **Uddishta (उद्दिष्ट)** | Given a syllable pattern, find its ordinal serial position | **Encoding / Ranking**: Combinadic bijection $\{0,1\}^n \to [0, \binom{n}{k}-1]$ | [`rank_block(block)`](file:///backend/core.py) |
| **Nashta (नष्ट)** | Given an ordinal position, reconstruct the syllable pattern | **Decoding / Unranking**: Inverse combinadic map $[0, \binom{n}{k}-1] \to \{0,1\}^n$ | [`unrank_block(n, k, r)`](file:///backend/core.py) |
| **Matra-vritta (मात्रावृत्त)** | Syllabic meters constrained by total moraic weight $\sum w_i = M$ | Restricted partitions into parts $\{1, 2\}$, counted by Fibonacci sequence | [`matra_vritta(m)`](file:///backend/core.py) |
| **Sankhya (संख्या)** | Total count of all possible patterns of length $n$ | Cardinality of state space: $\sum_{k=0}^n \binom{n}{k} = 2^n$ | UI State & Info metadata |

---

## 2. Mathematical Foundation of the Codec

### 2.1 Combinadic Ranking (Uddishta Algorithm)
For an $n$-bit block $b = (b_0, b_1, \dots, b_{n-1}) \in \{0, 1\}^n$ containing $k = \sum_{i=0}^{n-1} b_i$ ones:

The rank $r \in \left[0, \binom{n}{k}-1\right]$ represents the lexicographic position of the block among all $\binom{n}{k}$ patterns with exactly $k$ ones. When iterating through the block from left to right ($i = 0, \dots, n-1$), if bit $b_i = 1$:
$$r = \sum_{i=0, \, b_i=1}^{n-1} \binom{n - 1 - i}{\text{remaining ones}}$$

Because $\sum_{j=0}^{\text{remaining}} \binom{m}{j}$ uniquely partitions the remaining permutations, this map is an exact, injective bijection.

### 2.2 Combinadic Unranking (Nashta Algorithm)
Given $(n, k, r)$, the exact bit pattern is reconstructed deterministically without ambiguity:
For each position $i \in [0, n-1]$:
1. Let $c = \binom{n - 1 - i}{\text{left}}$, where $\text{left}$ is the count of remaining ones to place.
2. If $\text{left} > 0$ and $r \ge c$:
   - Emit bit $\mathtt{1}$
   - $r \leftarrow r - c$
   - $\text{left} \leftarrow \text{left} - 1$
3. Otherwise:
   - Emit bit $\mathtt{0}$

---

## 3. Information Theory & Shannon Entropy Analysis

### 3.1 Why Does MeruCode Compress Skewed Data?
Consider a memoryless binary source emitting symbols from Bernoulli distribution $X \sim \text{Bernoulli}(p)$ where $p = P(X = 1)$.
Shannon's Source Coding Theorem establishes that the minimum expected number of bits required to represent each symbol is bounded by the Shannon entropy:
$$H(p) = -p \log_2(p) - (1-p) \log_2(1-p) \quad \text{bits/symbol}$$

For an $n$-bit block with $k \approx p \cdot n$ ones, MeruCode stores:
1. $k$-field: $\lceil \log_2(n + 1) \rceil$ bits
2. Rank-field: $\lceil \log_2 \binom{n}{k} \rceil$ bits

Using Stirling's approximation $\ln(m!) \approx m \ln m - m + \frac{1}{2}\ln(2\pi m)$:
$$\log_2 \binom{n}{pn} = n \cdot H(p) - \frac{1}{2} \log_2(2\pi n p(1-p)) + O(1/n)$$

Dividing by block length $n$:
$$\lim_{n \to \infty} \frac{\log_2 \binom{n}{pn} + \lceil \log_2(n+1) \rceil}{n} = H(p)$$

**Theoretical Implication:** As block size $n$ increases, the per-bit encoding overhead of MeruCode approaches the empirical Shannon entropy $H(p)$ of the source!

### 3.2 Why Does MeruCode Expand Random Noise and Standard Text?
1. **White Noise / Random Bitstreams ($p = 0.5$):**
   - $H(0.5) = 1.0$ bit/symbol.
   - For $n=8, k=4$: $\binom{8}{4} = 70 \implies \lceil \log_2 70 \rceil = 7$ bits.
   - The $k$ field requires $\lceil \log_2 9 \rceil = 4$ bits.
   - Total payload $= 4 + 7 = 11$ bits for an 8-bit block (a 37.5% expansion), plus the 40-bit header!
   - By the pigeonhole principle, no lossless compression algorithm can compress all inputs; if some inputs compress, others must expand.

2. **Standard Text (`"saket"`):**
   - UTF-8 text exhibits byte values between $0x20$ and $0x7E$, with 3 to 5 ones per 8-bit byte ($k \approx 4$).
   - Because $k \approx n/2$ for ASCII text, each byte encodes to 11 bits in MeruCode, expanding text files. Text compression algorithms (like DEFLATE/zlib) rely on string repetition (LZ77) and frequency prefix trees (Huffman), not isolated Bernoulli block combinatorics.

### 3.3 Amortized Header Overhead
The legacy header is fixed at 40 bits ($32$ bits length $+ 8$ bits block size).
For an input stream of $N$ bits:
$$\text{Header Overhead per Bit} = \frac{40}{N}$$
- For $N = 40$ bits: header overhead is $100\%$.
- For $N = 65,536$ bits: header overhead is $0.06\%$.
- $\lim_{N \to \infty} \frac{40}{N} = 0$.

---

## 4. Container Architecture (.meru v2)

To prevent silent data corruption, the `.meru v2` container bundles verification metadata into a 19-byte binary header:

```text
+-------------------+---------+---------+--------------------+------------+--------------------+--------------------+
| Magic: "MERU"     | Version | Flags   | Original Bit Length| Block Size | Payload Bit Length | CRC-32 (Original)  |
| 4 Bytes (ASCII)   | 1 Byte  | 1 Byte  | 4 Bytes (uint32 BE)| 1 Byte     | 4 Bytes (uint32 BE)| 4 Bytes (uint32 BE)|
+-------------------+---------+---------+--------------------+------------+--------------------+--------------------+
| 0x4D 0x45 0x52 0x55| 0x02    | 0x00    | e.g. 0x00 0x00 0x04 0x00 | 0x08 | e.g. 0x00 0x00 0x02 0x30 | e.g. 0x8A 0x3F 0x12 0x90|
+-------------------+---------+---------+--------------------+------------+--------------------+--------------------+
                                      |
                                      +--> Followed by Variable-Length Packed Payload Bytes
```

### 4.1 Auto-Detection
The decoder detects the container type automatically:
- If first 4 bytes are `b"MERU"` $\implies$ Decodes v2 container with CRC32 verification.
- Otherwise $\implies$ Decodes legacy v1 raw bitstream.
