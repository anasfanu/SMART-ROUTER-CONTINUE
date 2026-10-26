"""Mock upstream OpenAI-compatible server untuk pengujian router.

Dua instance dijalankan dalam satu proses:
  - port 9901 : upstream SEHAT (echo SSE / JSON normal)
  - port 9902 : upstream SAKIT (chat/completions selalu hang > chunk timeout)
"""
import sys, json, threading, time
import os, tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/models":
            data = {"data": [
                {"id": "llama-3.3-70b-versatile", "object": "model"},
                {"id": "gemma2-9b-it", "object": "model"},
                {"id": "whisper-large-v3", "object": "model"},  # harus kena filter non-coding
            ]}
            b = json.dumps(data).encode()
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
        else:
            self.send_error(404)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        # simpan payload terakhir utk diverifikasi test
        with open(os.path.join(tempfile.gettempdir(), "last_payload.json"),"w") as f: json.dump(body,f)
        # catat jumlah panggilan ke healthy-upstream (utuk uji cache T9)
        try:
            n = int(open(os.path.join(tempfile.gettempdir(), "hit_count.txt")).read())
        except Exception:
            n = 0
        with open(os.path.join(tempfile.gettempdir(), "hit_count.txt"),"w") as f: f.write(str(n+1))
        if self.path.endswith("/fail"):
            self.send_error(500); return
        if body.get("stream"):
            self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.end_headers()
            for tok in ["Halo"," dunia","!"]:
                chunk = {"choices":[{"delta":{"content":tok},"index":0}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode()); self.wfile.flush()
                time.sleep(0.05)
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        else:
            resp = {"choices":[{"message":{"role":"assistant","content":"halo dunia"}}],"received_model":body.get("model")}
            b = json.dumps(resp).encode()
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)

class HHang(BaseHTTPRequestHandler):
    """Upstream sakit: chat/completions diam (hang) sampai client timeout."""
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_error(404)
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        time.sleep(3600)  # tidak pernah mengirim respons -> chunk/read timeout

def serve(port, handler):
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=serve, args=(9902, HHang), daemon=True).start()
    serve(9901, H)
