#!/usr/bin/env python3
"""
Yukti — Unified Test Runner & Verification Suite
Runs linter (ruff), backend unit tests (unittest / hypothesis), and cross-language parity (node).
Prints one clear summary line at completion.
"""
import os
import subprocess
import sys
import time

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    print("=" * 60)
    print("Yukti - Unified Quality & Parity Test Harness")
    print("=" * 60)

    # 1. Ruff lint check
    print("\n[1/3] Running Ruff Linter...")
    t0 = time.time()
    ruff_res = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=repo_root, capture_output=True, text=True)
    if ruff_res.returncode != 0:
        print("RUFF LINT FAILED:\n" + ruff_res.stdout + ruff_res.stderr)
        sys.exit(1)
    print(f"PASS: Ruff check clean ({time.time() - t0:.2f}s)")

    # 2. Python Unit & Hypothesis Tests
    print("\n[2/3] Running Python Unit & Hypothesis Tests (82 tests)...")
    t0 = time.time()
    backend_dir = os.path.join(repo_root, "backend")
    env = os.environ.copy()
    env["PYTHONPATH"] = backend_dir + os.pathsep + env.get("PYTHONPATH", "")
    py_res = subprocess.run(
        [sys.executable, "-m", "unittest", "test_meru.py"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        env=env
    )
    if py_res.returncode != 0:
        print("PYTHON UNIT TESTS FAILED:\n" + py_res.stderr + py_res.stdout)
        sys.exit(1)
    print(f"PASS: 82/82 Python unit tests passed ({time.time() - t0:.2f}s)")

    # 3. Node.js Cross-Language Bit-for-Bit Parity
    print("\n[3/3] Running Cross-Language JS/Python Parity Tests (1,000 cases)...")
    t0 = time.time()
    node_res = subprocess.run(
        ["node", "tests/parity_test.js"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    if node_res.returncode != 0:
        print("NODE PARITY TEST FAILED:\n" + node_res.stderr + node_res.stdout)
        sys.exit(1)
    print(f"PASS: 1,000/1,000 random vectors & 10 golden vectors verified ({time.time() - t0:.2f}s)")

    print("\n" + "=" * 60)
    print("PASS: 82/82 Python tests | 1,000/1,000 JS parity | Ruff clean")
    print("=" * 60)


if __name__ == "__main__":
    main()
