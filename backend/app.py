"""Flask API for Yukti. Run: python app.py  ->  http://127.0.0.1:5000"""
import base64
import collections
import logging
import math
import os
import time

import core
from bench import compare
from flask import Flask, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.join(HERE, "..", "frontend")
app = Flask(__name__)
app.json.sort_keys = False

SERVER_START_TIME = time.time()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yukti")

MAX_INPUT_BITS = 200000
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB max request size
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Configurable CORS origins (default: same origin + localhost variants)
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",")

# In-memory sliding window rate limiter: IP -> list of timestamps
_RATE_LIMIT_STORE = collections.defaultdict(list)
RATE_LIMIT_WINDOW = 60.0  # 60 seconds
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "120"))  # requests per window
EXPENSIVE_ROUTES = {"/api/compare", "/api/sweep", "/api/analyze"}


@app.before_request
def before_request_hook():
    request._start_time = time.perf_counter()
    if request.path in EXPENSIVE_ROUTES:
        ip = request.remote_addr or "127.0.0.1"
        now = time.time()
        timestamps = _RATE_LIMIT_STORE[ip]
        while timestamps and timestamps[0] < now - RATE_LIMIT_WINDOW:
            timestamps.pop(0)
        if len(timestamps) >= RATE_LIMIT_MAX:
            resp = jsonify({
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {RATE_LIMIT_MAX} requests per minute exceeded for {request.path}"
                }
            })
            resp.headers["Retry-After"] = "60"
            return resp, 429
        timestamps.append(now)


@app.after_request
def after_request_hook(resp):
    origin = request.headers.get("Origin")
    if origin and (origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS or origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")):
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://127.0.0.1:5000"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"

    duration_ms = 0.0
    if hasattr(request, "_start_time"):
        duration_ms = round((time.perf_counter() - request._start_time) * 1000, 2)
    input_size = request.content_length or 0
    logger.info(
        f"{request.method} {request.path} status={resp.status_code} "
        f"duration={duration_ms}ms input_bytes={input_size} ip={request.remote_addr or 'local'}"
    )
    return resp


@app.errorhandler(core.MeruError)
def handle_meru_error(e):
    return jsonify({"error": e.to_dict()}), 400


@app.errorhandler(400)
def handle_bad_request(e):
    msg = getattr(e, "description", "bad request")
    return jsonify({"error": {"code": "BAD_REQUEST", "message": str(msg)}}), 400


@app.errorhandler(404)
def handle_not_found(_):
    return jsonify({"error": {"code": "NOT_FOUND", "message": "resource not found"}}), 404


@app.errorhandler(405)
def handle_method_not_allowed(_):
    return jsonify({"error": {"code": "METHOD_NOT_ALLOWED", "message": "method not allowed"}}), 405


@app.errorhandler(413)
def handle_payload_too_large(_):
    return jsonify({"error": {"code": "PAYLOAD_TOO_LARGE", "message": "request payload exceeds maximum limit"}}), 413


@app.errorhandler(415)
def handle_unsupported_media_type(_):
    return jsonify({"error": {"code": "UNSUPPORTED_MEDIA_TYPE", "message": "content-type must be application/json"}}), 415


@app.errorhandler(429)
def handle_rate_limit_exceeded(e):
    resp = jsonify({"error": {"code": "TOO_MANY_REQUESTS", "message": "rate limit exceeded, please retry later"}})
    resp.headers["Retry-After"] = "5"
    return resp, 429


@app.errorhandler(Exception)
def handle_generic_exception(e):
    # Log securely without leaking internal traceback to client
    app.logger.error("Unhandled exception: %s", str(e), exc_info=True)
    return jsonify({"error": {"code": "INTERNAL_SERVER_ERROR", "message": "internal server error"}}), 500


# ---------- Parameter & Body Validation Helpers ----------
def _parse_int(val, name, min_val=None, max_val=None, default=None):
    """Safely parses and bounds an integer from query string or JSON."""
    if val is None:
        if default is not None:
            return default
        raise core.MeruError(f"'{name}' is required", code="MISSING_PARAMETER", field=name)
    if isinstance(val, bool):
        raise core.MeruError(f"'{name}' must be an integer, not a boolean", code="INVALID_TYPE", field=name)
    if isinstance(val, (int, float)):
        if isinstance(val, float):
            if val != int(val):
                raise core.MeruError(f"'{name}' must be an integer, not a float", code="INVALID_TYPE", field=name)
            val = int(val)
    elif isinstance(val, str):
        val = val.strip()
        try:
            val = int(val)
        except ValueError:
            raise core.MeruError(f"'{name}' must be a valid integer", code="INVALID_INTEGER", field=name)
    else:
        raise core.MeruError(f"'{name}' must be an integer", code="INVALID_TYPE", field=name)

    if min_val is not None and val < min_val:
        raise core.MeruError(f"'{name}' must be at least {min_val}", code="VALUE_OUT_OF_RANGE", field=name)
    if max_val is not None and val > max_val:
        raise core.MeruError(f"'{name}' must be at most {max_val}", code="VALUE_OUT_OF_RANGE", field=name)
    return val


def _parse_float(val, name, min_val=None, max_val=None, default=None):
    """Safely parses and bounds a float from query string or JSON."""
    if val is None:
        if default is not None:
            return default
        raise core.MeruError(f"'{name}' is required", code="MISSING_PARAMETER", field=name)
    if isinstance(val, bool):
        raise core.MeruError(f"'{name}' must be a number, not a boolean", code="INVALID_TYPE", field=name)
    if isinstance(val, (int, float)):
        val = float(val)
    elif isinstance(val, str):
        val = val.strip()
        try:
            val = float(val)
        except ValueError:
            raise core.MeruError(f"'{name}' must be a valid number", code="INVALID_FLOAT", field=name)
    else:
        raise core.MeruError(f"'{name}' must be a number", code="INVALID_TYPE", field=name)

    if math.isnan(val) or math.isinf(val):
        raise core.MeruError(f"'{name}' cannot be NaN or Infinity", code="INVALID_FLOAT", field=name)

    if min_val is not None and val < min_val:
        raise core.MeruError(f"'{name}' must be at least {min_val}", code="VALUE_OUT_OF_RANGE", field=name)
    if max_val is not None and val > max_val:
        raise core.MeruError(f"'{name}' must be at most {max_val}", code="VALUE_OUT_OF_RANGE", field=name)
    return val


def _parse_str(val, name, max_len=None, required=True):
    """Validates that val is a string within length bounds."""
    if val is None:
        if not required:
            return ""
        raise core.MeruError(f"'{name}' is required", code="MISSING_PARAMETER", field=name)
    if not isinstance(val, str):
        raise core.MeruError(f"'{name}' must be a string", code="INVALID_TYPE", field=name)
    if max_len is not None and len(val) > max_len:
        raise core.MeruError(f"'{name}' exceeds maximum allowed length of {max_len}", code="STRING_TOO_LONG", field=name)
    return val


def _body(allowed_fields=None):
    """Validates that the request has a valid JSON dictionary body."""
    if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
        raise core.MeruError("request payload exceeds maximum limit", code="PAYLOAD_TOO_LARGE")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise core.MeruError("send a JSON object", code="INVALID_JSON")
    if allowed_fields is not None:
        unexpected = set(data.keys()) - set(allowed_fields)
        if unexpected:
            raise core.MeruError(f"unexpected field(s): {', '.join(sorted(unexpected))}", code="UNEXPECTED_FIELD")
    return data


def _input_bits(data):
    """Accepts {"text": "..."} or {"bits": "0101"}; returns (bits, mode)."""
    has_bits = "bits" in data
    has_text = "text" in data
    if has_bits and has_text:
        raise core.MeruError("provide either 'text' or 'bits', not both", code="AMBIGUOUS_INPUT")
    if has_bits:
        bits_val = data["bits"]
        if not isinstance(bits_val, str):
            raise core.MeruError("'bits' must be a string of '0' and '1'", code="INVALID_TYPE", field="bits")
        bits, mode = bits_val, "bits"
    elif has_text:
        text_val = data["text"]
        if not isinstance(text_val, str):
            raise core.MeruError("'text' must be a string", code="INVALID_TYPE", field="text")
        bits, mode = core.text_to_bits(text_val), "text"
    else:
        raise core.MeruError("give either text or bits", code="MISSING_INPUT")
    core._check_bits(bits, field="bits")
    if len(bits) > MAX_INPUT_BITS:
        raise core.MeruError("input too long (max %d bits)" % MAX_INPUT_BITS, code="INPUT_TOO_LONG", field="bits")
    return bits, mode


def _block(data, default=8):
    b = data.get("block", default)
    return _parse_int(b, "block", min_val=1, max_val=core.MAX_BLOCK)


@app.get("/api/health")
def health():
    uptime = round(time.time() - SERVER_START_TIME, 2)
    return jsonify({
        "status": "ok",
        "name": "Yukti",
        "version": "2.0.0",
        "uptime_seconds": uptime,
        "header_bits": core.HEADER_BITS
    })


@app.get("/api/prastara")
def prastara():
    n = _parse_int(request.args.get("n"), "n", min_val=0, max_val=16, default=3)
    pats = core.prastara(n)
    return jsonify({"n": n, "count": len(pats), "patterns": pats,
                    "display": [p.replace("0", "L").replace("1", "G") for p in pats]})


@app.get("/api/meru")
def meru():
    rows = _parse_int(request.args.get("rows"), "rows", min_val=1, max_val=64, default=9)
    return jsonify({"rows": core.meru_rows(rows)})


@app.get("/api/matra")
def matra():
    m = _parse_int(request.args.get("m"), "m", min_val=1, max_val=16, default=5)
    pats = core.matra_vritta(m)
    return jsonify({"matra": m, "count": len(pats), "patterns": pats})


@app.get("/api/uddishta")
def uddishta():
    p = _parse_str(request.args.get("pattern"), "pattern", max_len=64, required=False)
    core._check_bits(p, field="pattern")
    return jsonify({"pattern": p, "index": core.uddishta(p)})


@app.get("/api/nashta")
def nashta():
    n = _parse_int(request.args.get("n"), "n", min_val=0, max_val=64)
    i = _parse_int(request.args.get("index"), "index", min_val=0)
    return jsonify({"n": n, "index": i, "pattern": core.nashta(n, i)})


@app.get("/api/presets")
def presets():
    return jsonify({k: v["label"] for k, v in core.PRESETS.items()})


@app.post("/api/generate")
def generate():
    d = _body(allowed_fields={"preset", "length", "seed"})
    preset = _parse_str(d.get("preset", "sparse"), "preset", max_len=32)
    length = _parse_int(d.get("length", 256), "length", min_val=1, max_val=100000)
    seed = _parse_int(d.get("seed", 42), "seed")
    bits = core.make_preset(preset, length, seed)
    return jsonify({"bits": bits, "ones": bits.count("1"), "length": len(bits)})


@app.post("/api/encode")
def encode():
    d = _body(allowed_fields={"text", "bits", "block"})
    bits, mode = _input_bits(d)
    block = _block(d)
    enc, rows = core.encode(bits, block, detail=True)
    return jsonify({"mode": mode, "input_bits": len(bits), "block": block,
                    "header": enc[:core.HEADER_BITS], "blocks": rows,
                    "encoded": enc, "encoded_bits": len(enc)})


@app.post("/api/decode")
def decode():
    d = _body(allowed_fields={"encoded", "as_text"})
    enc = _parse_str(d.get("encoded"), "encoded", max_len=MAX_INPUT_BITS * 2)
    bits = core.decode(enc)
    out = {"bits": bits, "bit_length": len(bits)}
    if d.get("as_text"):
        out["text"] = core.bits_to_text(bits)
    return jsonify(out)


@app.post("/api/compare")
def compare_route():
    d = _body(allowed_fields={"text", "bits", "block", "repeats"})
    bits, _ = _input_bits(d)
    block = _block(d)
    repeats = _parse_int(d.get("repeats", 20), "repeats", min_val=1, max_val=100) if "repeats" in d else 20
    return jsonify(compare(bits, block, repeats=repeats))


@app.post("/api/pack")
def pack():
    d = _body(allowed_fields={"text", "bits", "block"})
    bits, mode = _input_bits(d)
    block = _block(d)
    container_bytes = core.pack_container(bits, block=block)
    return jsonify({
        "version": core.CONTAINER_VERSION_2,
        "container_base64": base64.b64encode(container_bytes).decode("ascii"),
        "container_bytes": len(container_bytes),
        "original_bits": len(bits),
        "block": block,
        "crc32": hex(core.zlib.crc32(core.bits_to_bytes(bits)) & 0xFFFFFFFF)
    })


@app.post("/api/unpack")
def unpack():
    d = _body(allowed_fields={"container_base64", "as_text"})
    b64_str = _parse_str(d.get("container_base64"), "container_base64", max_len=MAX_CONTENT_LENGTH * 2)
    try:
        container_bytes = base64.b64decode(b64_str, validate=True)
    except Exception:
        raise core.MeruError("invalid base64 encoding", code="INVALID_BASE64")

    bits, meta = core.unpack_container(container_bytes)
    out = {
        "bits": bits,
        "bit_length": len(bits),
        "version": meta.get("version", 1),
        "crc_verified": meta.get("crc_verified", False)
    }
    if "crc32" in meta:
        out["crc32"] = meta["crc32"]
    if d.get("as_text"):
        out["text"] = core.bits_to_text(bits)
    return jsonify(out)


@app.get("/api/info")
def info():
    return jsonify({
        "name": "Yukti (MeruCode)",
        "version": "2.0.0",
        "description": "Lossless combinatorial bitstream codec inspired by Pingala's Chhandas-Shastra",
        "limits": {
            "max_input_bits": MAX_INPUT_BITS,
            "max_output_bits": core.MAX_OUTPUT_BITS,
            "max_content_length_bytes": MAX_CONTENT_LENGTH,
            "max_block_size": core.MAX_BLOCK,
            "max_matra": 16,
            "max_prastara_n": 16
        },
        "header_layout": {
            "v1_raw": {
                "total_bits": 40,
                "fields": [
                    {"name": "original_length", "bits": 32, "type": "uint32 BE", "description": "Original stream length in bits"},
                    {"name": "block_size", "bits": 8, "type": "uint8", "description": "Block size n (1..64)"}
                ]
            },
            "v2_container": {
                "magic": "MERU",
                "version": 2,
                "header_size_bytes": core.CONTAINER_HEADER_SIZE,
                "fields": [
                    {"name": "magic", "bytes": 4, "value": "MERU"},
                    {"name": "version", "bytes": 1, "value": 2},
                    {"name": "flags", "bytes": 1, "value": 0},
                    {"name": "original_bit_length", "bytes": 4, "type": "uint32 BE"},
                    {"name": "block_size", "bytes": 1, "type": "uint8"},
                    {"name": "payload_bit_length", "bytes": 4, "type": "uint32 BE"},
                    {"name": "original_crc32", "bytes": 4, "type": "uint32 BE"},
                    {"name": "payload", "bytes": "variable", "description": "Rank/k encoded stream"}
                ]
            }
        },
        "endpoints": [
            {"method": "GET", "path": "/api/health", "description": "Service healthcheck and version"},
            {"method": "GET", "path": "/api/info", "description": "API metadata, limits, and header specifications"},
            {"method": "GET", "path": "/api/docs", "description": "Interactive HTML documentation"},
            {"method": "POST", "path": "/api/encode", "description": "Encode bitstream or text into MeruCode"},
            {"method": "POST", "path": "/api/decode", "description": "Decode MeruCode bitstream into bits or text"},
            {"method": "POST", "path": "/api/pack", "description": "Package bits/text into robust .meru v2 container with CRC32"},
            {"method": "POST", "path": "/api/unpack", "description": "Unpack .meru v2 container with CRC32 integrity validation"},
            {"method": "POST", "path": "/api/trace", "description": "Step-by-step block ranking walk with binomial terms"},
            {"method": "POST", "path": "/api/sweep", "description": "Block size vs compression ratio sweep grid for heatmaps"},
            {"method": "POST", "path": "/api/analyze", "description": "Shannon entropy H(p), theoretical minimum, and MeruCode gap"},
            {"method": "POST", "path": "/api/corrupt", "description": "Bit-flip corruption laboratory simulator"},
            {"method": "POST", "path": "/api/compare", "description": "Benchmark comparison vs raw, zlib, gzip, bz2, lzma, rle"},
            {"method": "POST", "path": "/api/generate", "description": "Deterministic PRNG bitstream generator"},
            {"method": "GET", "path": "/api/prastara", "description": "Pingala Prastara binary permutations"},
            {"method": "GET", "path": "/api/meru", "description": "Meru Prastara (Pascal triangle) rows"},
            {"method": "GET", "path": "/api/matra", "description": "Matra-vritta meter combinations"},
            {"method": "GET", "path": "/api/nashta", "description": "Nashta: index -> pattern"},
            {"method": "GET", "path": "/api/uddishta", "description": "Uddishta: pattern -> index"}
        ]
    })


@app.get("/api/docs")
def docs():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Yukti (MeruCode) API Reference</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #24292f; }
        h1 { border-bottom: 2px solid #e1e4e8; padding-bottom: 12px; }
        .endpoint { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
        .method { font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 13px; color: #fff; display: inline-block; }
        .GET { background: #0969da; }
        .POST { background: #1a7f37; }
        code { background: #e1e4e8; padding: 2px 6px; border-radius: 4px; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Yukti (MeruCode) - API Documentation</h1>
    <p>Lossless combinatorial bitstream codec inspired by Pingala's Chhandas-Shastra.</p>
    <p>Explore system endpoints below or fetch machine-readable schema at <code><a href="/api/info">/api/info</a></code>.</p>
    <div class="endpoint"><span class="method GET">GET</span> <code>/api/info</code> &mdash; Version, limits, and header layout</div>
    <div class="endpoint"><span class="method GET">GET</span> <code>/api/health</code> &mdash; Service health and uptime</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/encode</code> &mdash; Encode bits/text</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/decode</code> &mdash; Decode bitstream</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/pack</code> &mdash; Create .meru v2 container</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/unpack</code> &mdash; Unpack .meru v2 container</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/trace</code> &mdash; Trace binomial terms walk</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/sweep</code> &mdash; Block size sweep grid</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/analyze</code> &mdash; Shannon entropy vs MeruCode gap</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/corrupt</code> &mdash; Corruption lab simulation</div>
    <div class="endpoint"><span class="method POST">POST</span> <code>/api/compare</code> &mdash; Benchmarks vs standard compressors</div>
</body>
</html>""", 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/api/trace")
def trace_route():
    d = _body(allowed_fields={"text", "bits", "block", "max_blocks"})
    bits, mode = _input_bits(d)
    block = _block(d)
    max_blocks = _parse_int(d.get("max_blocks", 32), "max_blocks", min_val=1, max_val=256) if "max_blocks" in d else 32
    res = core.trace_stream(bits, block=block, max_blocks=max_blocks)
    res["mode"] = mode
    return jsonify(res)


@app.post("/api/sweep")
def sweep_route():
    d = _body(allowed_fields={"density", "length", "seed", "block_min", "block_max", "step"})
    density = _parse_float(d.get("density", 0.05), "density", min_val=0.0, max_val=1.0) if "density" in d else 0.05
    length = _parse_int(d.get("length", 1024), "length", min_val=16, max_val=20000) if "length" in d else 1024
    seed = _parse_int(d.get("seed", 42), "seed") if "seed" in d else 42
    b_min = _parse_int(d.get("block_min", 4), "block_min", min_val=1, max_val=core.MAX_BLOCK) if "block_min" in d else 4
    b_max = _parse_int(d.get("block_max", 64), "block_max", min_val=b_min, max_val=core.MAX_BLOCK) if "block_max" in d else 64
    step = _parse_int(d.get("step", 2), "step", min_val=1, max_val=16) if "step" in d else 2
    res = core.sweep_ratios(density=density, length=length, seed=seed, block_min=b_min, block_max=b_max, step=step)
    return jsonify(res)


@app.post("/api/analyze")
def analyze_route():
    d = _body(allowed_fields={"text", "bits", "block"})
    bits, _ = _input_bits(d)
    block = _block(d)
    res = core.calculate_entropy(bits, block=block)
    return jsonify(res)


@app.post("/api/corrupt")
def corrupt_route():
    d = _body(allowed_fields={"encoded", "position"})
    encoded = _parse_str(d.get("encoded"), "encoded", max_len=MAX_INPUT_BITS * 2)
    core._check_bits(encoded, field="encoded")
    pos = _parse_int(d.get("position"), "position", min_val=0, max_val=len(encoded) - 1)
    res = core.corrupt_and_decode(encoded, pos)
    return jsonify(res)


@app.get("/")
@app.get("/index")
@app.get("/index.html")
def index():
    return send_from_directory(FRONT, "index.html")


@app.get("/patterns")
@app.get("/patterns.html")
def patterns_page():
    return send_from_directory(FRONT, "patterns.html")


@app.get("/codec")
@app.get("/codec.html")
def codec_page():
    return send_from_directory(FRONT, "codec.html")


@app.get("/benchmark")
@app.get("/benchmark.html")
def benchmark_page():
    return send_from_directory(FRONT, "benchmark.html")


@app.get("/verify")
@app.get("/verify.html")
def verify_page():
    return send_from_directory(FRONT, "verify.html")


@app.get("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(FRONT, "css"), filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONT, "js"), filename)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true")
    app.run(host=host, port=port, debug=debug)
