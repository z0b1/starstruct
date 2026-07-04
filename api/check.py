import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from http.server import BaseHTTPRequestHandler
import json
from checker import check


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}")

        template_id  = (body.get("template") or "").strip()
        files        = body.get("files")
        raw_depth    = body.get("depth")
        max_depth    = int(raw_depth) if raw_depth is not None else None
        extra_ignore = body.get("ignore") or []

        def error(msg, code=400):
            b = json.dumps({"error": msg}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b)

        if not template_id:
            return error("Missing field: template")
        if not isinstance(files, list) or not files:
            return error("Missing or empty field: files")

        try:
            result = check(files, template_id, max_depth, extra_ignore)
            b = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b)
        except ValueError as e:
            error(str(e), 400)
        except Exception as e:
            error(f"Internal error: {e}", 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
