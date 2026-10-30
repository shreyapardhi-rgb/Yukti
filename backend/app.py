"""Flask API for Yukti. Run: python app.py  ->  http://127.0.0.1:5000"""
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
    return jsonify({"status": "ok", "name": "Yukti", "header_bits": core.HEADER_BITS})


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
