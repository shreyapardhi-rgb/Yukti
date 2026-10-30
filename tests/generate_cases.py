"""Generate random test cases for cross-language parity testing."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import core  # noqa: E402


def rnd(state):
    state = (state + 0x6D2B79F5) & 0xFFFFFFFF
    z = (state ^ (state >> 15)) * ((state | 1)) & 0xFFFFFFFF
    z = (z ^ (z + ((z ^ (z >> 7)) * ((z | 61)) & 0xFFFFFFFF))) & 0xFFFFFFFF
    return (z ^ (z >> 14)) / 4294967296.0, state


def main():
    seed = 1337
    cases = []
    for _ in range(1000):
        p_len, seed = rnd(seed)
        length = int(p_len * 200)
        p_blk, seed = rnd(seed)
        block = 1 + int(p_blk * 64)
        p_den, seed = rnd(seed)
        density = p_den
        bits = ""
        for _ in range(length):
            p_bit, seed = rnd(seed)
            bits += "1" if p_bit < density else "0"
        cases.append({
            "bits": bits,
            "block": block,
            "py_encoded": core.encode(bits, block)
        })

    cases_path = os.path.join(os.path.dirname(__file__), "random_cases.json")
    with open(cases_path, "w", encoding="utf-8") as f:
        json.dump(cases, f)
    print(f"Generated {len(cases)} cases in {cases_path}")


if __name__ == "__main__":
    main()
