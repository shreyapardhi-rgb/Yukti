/**
 * Yukti / MeruCode - Cross-Language Parity Test (Node.js)
 * Verifies that the Frontend JS Codec produces identical bitstreams to the Backend Python Codec.
 */
const fs = require("fs");
const path = require("path");

// Load JS core module (either from frontend/js/core.js or extracted from index.html)
const jsCorePath = path.join(__dirname, "..", "frontend", "js", "core.js");
let jsCodec;

if (fs.existsSync(jsCorePath)) {
  jsCodec = require(jsCorePath);
} else {
  const htmlPath = path.join(__dirname, "..", "frontend", "index.html");
  const html = fs.readFileSync(htmlPath, "utf-8");
  const coreMatch = html.match(/\/\/ ==CORE==([\s\S]*?)\/\/ ==\/CORE==/);
  if (!coreMatch) {
    console.error("FATAL: Could not locate // ==CORE== in frontend/index.html or frontend/js/core.js");
    process.exit(1);
  }
  const fn = new Function(
    coreMatch[1] + `
    return { C, bw, kWidth, rankWidth, pad, prastara, meruRows, matraVritta, textToBits, bitsToText, rankBlock, unrankBlock, encode, decode, mulberry32, makePreset };
  `
  );
  jsCodec = fn();
}

// 1. Verify Golden Vectors
const goldenPath = path.join(__dirname, "golden.json");
const goldenVectors = JSON.parse(fs.readFileSync(goldenPath, "utf-8"));

let passedGolden = 0;
for (const v of goldenVectors) {
  const jsEnc = jsCodec.encode(v.raw_bits, v.block).encoded;
  if (jsEnc !== v.encoded) {
    console.error(`BUG: Golden mismatch on '${v.name}' (block ${v.block})`);
    console.error(`  Expected (Python): ${v.encoded}`);
    console.error(`  Got (JavaScript):  ${jsEnc}`);
    process.exit(1);
  }
  const jsDec = jsCodec.decode(jsEnc);
  if (jsDec !== v.raw_bits) {
    console.error(`BUG: Decode mismatch on '${v.name}'`);
    process.exit(1);
  }
  passedGolden++;
}
console.log(`PASS: All ${passedGolden} golden vectors verified with JS codec`);

// 2. 1,000 Random Inputs Parity
// If random test inputs are passed as json file or via stdin, verify
const randomInputPath = path.join(__dirname, "random_cases.json");
if (fs.existsSync(randomInputPath)) {
  const randomCases = JSON.parse(fs.readFileSync(randomInputPath, "utf-8"));
  let passedRandom = 0;
  for (let i = 0; i < randomCases.length; i++) {
    const item = randomCases[i];
    const jsEnc = jsCodec.encode(item.bits, item.block).encoded;
    if (jsEnc !== item.py_encoded) {
      console.error(`BUG: Parity mismatch at random vector #${i} (block ${item.block}, length ${item.bits.length})`);
      console.error(`  Python: ${item.py_encoded}`);
      console.error(`  JS:     ${jsEnc}`);
      process.exit(1);
    }
    const jsDec = jsCodec.decode(jsEnc);
    if (jsDec !== item.bits) {
      console.error(`BUG: JS roundtrip failed at random vector #${i}`);
      process.exit(1);
    }
    passedRandom++;
  }
  console.log(`PASS: Verified ${passedRandom}/1000 random vectors match Python bit-for-bit!`);
} else {
  console.log("No random_cases.json found, skipping random batch test.");
}
