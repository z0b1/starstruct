# main.py — Flask API

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from checker import check, list_templates

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__)
CORS(app)


@app.route("/templates", methods=["GET"])
def get_templates():
    return jsonify(list_templates())


@app.route("/check", methods=["POST"])
def check_structure():
    body = request.get_json(force=True, silent=True)

    if not body:
        return jsonify({"error": "Expected JSON body."}), 400

    template_id = (body.get("template") or "").strip()
    files       = body.get("files")
    raw_depth    = body.get("depth")
    max_depth    = int(raw_depth) if raw_depth is not None else None
    extra_ignore = body.get("ignore") or []

    if not template_id:
        return jsonify({"error": "Missing field: template"}), 400
    if not isinstance(files, list) or not files:
        return jsonify({"error": "Missing or empty field: files (must be a list of paths)"}), 400

    try:
        result = check(files, template_id, max_depth, extra_ignore)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {e}"}), 500


# Static file routes LAST so they don't shadow the API routes
@app.route("/")
def index():
    print(f"[debug] serving index.html from {FRONTEND_DIR}")
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    print(f"API running → http://localhost:8000")
    print(f"Frontend dir: {FRONTEND_DIR}")
    print(f"index.html exists: {os.path.isfile(os.path.join(FRONTEND_DIR, 'index.html'))}")
    app.run(debug=True, port=8000)