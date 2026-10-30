"""Flask API for Yukti. Run: python app.py  ->  http://127.0.0.1:5000"""
import base64
import os
from flask import Flask, jsonify, request, send_from_directory

import core
from bench import compare

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.join(HERE, "..", "frontend")
app = Flask(__name__)
app.json.sort_keys = False

MAX_INPUT_BITS = 200000
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB max request size
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Configurable CORS origins (default: same origin + localhost variants)
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",")


@app.after_request
def add_security_headers(resp):
    origin = request.headers.get("Origin")
    if origin and (origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS or origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")):
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://127.0.0.1:5000"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
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
    return jsonify({"status": "ok", "name": "Yukti", "header_bits": core.HEADER_BITS})


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
    except Exception as e:
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


@app.get("/")
def index():
    return send_from_directory(FRONT, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
