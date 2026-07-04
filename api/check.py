import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from http.server import BaseHTTPRequestHandler
import json
from checker import check


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or b"{}")

            template_id  = (body.get("template") or "").strip()
            files        = body.get("files")
            raw_depth    = body.get("depth")
            max_depth    = int(raw_depth) if raw_depth is not None else None
            extra_ignore = body.get("ignore") or []

            if not template_id:
                raise ValueError("Missing field: template")
            if not isinstance(files, list) or not files:
                raise ValueError("Missing or empty field: files")

            result = check(files, template_id, max_depth, extra_ignore)
            body_out = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body_out)

        except ValueError as e:
            body_out = json.dumps({"error": str(e)}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body_out)
        except Exception as e:
            body_out = json.dumps({"error": f"Internal error: {e}"}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body_out)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()