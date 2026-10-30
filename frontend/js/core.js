// ==CORE==
// Yukti Core Codec & Pingala Combinatorics (Pure Functions, zero DOM dependencies)
const HEADER_BITS = 40;

// Binomial coefficient C(n, k) with BigInt memoization
const C = (() => {
  const memo = new Map();
  return (n, k) => {
    if (k < 0 || k > n) return 0n;
    if (k === 0 || k === n) return 1n;
    const key = n * 100 + k;
    if (memo.has(key)) return memo.get(key);
    const v = C(n - 1, k - 1) + C(n - 1, k);
    memo.set(key, v);
    return v;
  };
})();

const bw = (x) => x === 0n ? 0 : x.toString(2).length;           // bit width of a BigInt
const kWidth = (n) => n.toString(2).length;                       // bits to store k in 0..n
const rankWidth = (n, k) => bw(C(n, k) - 1n);
const pad = (v, w) => w === 0 ? "" : BigInt(v).toString(2).padStart(w, "0");

// Classical Pingala Combinatorics
function prastara(n) {
  const out = [];
  for (let i = 0; i < 2 ** n; i++) {
    out.push(i.toString(2).padStart(n, "0"));
  }
  return out;
}

function meruRows(r) {
  const rows = [];
  for (let i = 0; i < r; i++) {
    const row = [];
    for (let k = 0; k <= i; k++) row.push(C(i, k));
    rows.push(row);
  }
  return rows;
}

function matraVritta(m) {
  const out = [];
  (function go(left, acc) {
    if (left === 0) { out.push(acc); return; }
    go(left - 1, acc + "L");
    if (left >= 2) go(left - 2, acc + "G");
  })(m, "");
  return out;
}

function textToBits(t) {
  return Array.from(new TextEncoder().encode(t), b => b.toString(2).padStart(8, "0")).join("");
}

function bitsToText(b) {
  if (b.length % 8) throw new Error("bit length is not a multiple of 8");
  const a = new Uint8Array(b.length / 8);
  for (let i = 0; i < a.length; i++) a[i] = parseInt(b.slice(i * 8, i * 8 + 8), 2);
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(a);
  } catch (e) {
    throw new Error("bits are not valid UTF-8 text");
  }
}

// Block Uddishta (Ranking)
function rankBlock(blk) {
  const n = blk.length;
  let left = 0;
  for (const c of blk) if (c === "1") left++;
  const k = left;
  let r = 0n;
  for (let i = 0; i < n; i++) {
    if (blk[i] === "1") {
      r += C(n - i - 1, left);
      left--;
    }
  }
  return { k, r };
}

// Block Nashta (Unranking)
function unrankBlock(n, k, r) {
  if (k < 0 || k > n) throw new Error("invalid k " + k);
  if (r < 0n || r >= C(n, k)) throw new Error("invalid rank");
  let out = "";
  let left = k;
  for (let i = 0; i < n; i++) {
    const c = C(n - i - 1, left);
    if (left > 0 && r >= c) {
      out += "1";
      r -= c;
      left--;
    } else {
      out += "0";
    }
  }
  return out;
}

// Full Stream Encode
function encode(bits, block) {
  if (!/^[01]*$/.test(bits)) throw new Error("bits must contain only 0 and 1");
  if (!Number.isInteger(block) || block < 1 || block > 64) throw new Error("block size must be 1..64");
  const padded = bits + "0".repeat((block - bits.length % block) % block);
  let out = pad(bits.length, 32) + pad(block, 8);
  const rows = [];
  const kw = kWidth(block);
  for (let i = 0; i < padded.length; i += block) {
    const blk = padded.slice(i, i + block);
    const { k, r } = rankBlock(blk);
    const rw = rankWidth(block, k);
    const kb = pad(k, kw);
    const rb = pad(r, rw);
    out += kb + rb;
    rows.push({ block: blk, k, rank: r, group: C(block, k), kb, rb, used: kw + rw });
  }
  return { encoded: out, rows };
}

// Full Stream Decode
function decode(s) {
  if (!/^[01]*$/.test(s)) throw new Error("stream must contain only 0 and 1");
  if (s.length < HEADER_BITS) throw new Error("stream shorter than the 40-bit header");
  const total = parseInt(s.slice(0, 32), 2);
  const block = parseInt(s.slice(32, 40), 2);
  if (block < 1 || block > 64) throw new Error("header has invalid block size");
  let pos = 40;
  const kw = kWidth(block);
  const nb = Math.ceil(total / block);
  let out = "";
  for (let i = 0; i < nb; i++) {
    if (pos + kw > s.length) throw new Error("stream ended while reading k");
    const k = parseInt(s.slice(pos, pos + kw), 2);
    pos += kw;
    if (k > block) throw new Error("k is larger than block size");
    const rw = rankWidth(block, k);
    if (pos + rw > s.length) throw new Error("stream ended while reading rank");
    const r = rw ? BigInt("0b" + s.slice(pos, pos + rw)) : 0n;
    pos += rw;
    out += unrankBlock(block, k, r);
  }
  if (pos !== s.length) throw new Error("extra bits after the last block");
  return out.slice(0, total);
}

// Mulberry32 Deterministic PRNG
function mulberry32(a) {
  return function () {
    a |= 0;
    a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const PRESETS = { sparse: 0.05, mostly_ones: 0.95, balanced: 0.5, all_zeros: 0 };
const PRESET_LABEL = {
  sparse: "Sparse (5% ones)",
  mostly_ones: "Dense (95% ones)",
  balanced: "Random (50% ones)",
  all_zeros: "All zeros",
  alternating: "Alternating 0101"
};

function makePreset(name, length, seed) {
  if (name === "alternating") return "01".repeat(length).slice(0, length);
  const rnd = mulberry32(seed);
  const d = PRESETS[name];
  let s = "";
  for (let i = 0; i < length; i++) s += rnd() < d ? "1" : "0";
  return s;
}

function verdict(raw, meru) {
  if (!raw) return { good: false, text: "empty input" };
  const pct = (100 * meru / raw).toFixed(1);
  return meru < raw
    ? { good: true, text: `COMPRESSES: ${raw} bits -> ${meru} bits (${pct}% of original)` }
    : { good: false, text: `ONLY ENCODES: ${raw} bits -> ${meru} bits (${pct}% of original, larger)` };
}

// CommonJS export for Node parity testing
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    C, bw, kWidth, rankWidth, pad, prastara, meruRows, matraVritta,
    textToBits, bitsToText, rankBlock, unrankBlock, encode, decode,
    mulberry32, makePreset, verdict
  };
}
// ==/CORE==
