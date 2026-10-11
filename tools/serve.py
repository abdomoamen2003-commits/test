"""Local production-like static server for QA.

- gzip for text assets (like nginx gzip on)
- immutable cache headers for hashed image files (like a real deploy)
- logs every request with encoded size so page weight can be measured over the wire

Usage: python tools/serve.py [port] [root]
"""
import gzip, io, os, sys, datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
ROOT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.getcwd()
LOG = os.path.join(ROOT, "_audit", "server.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

GZIP_TYPES = ("text/html", "text/css", "application/javascript", "text/javascript",
              "application/json", "image/svg+xml", "application/xml", "text/xml")


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        # hash-named images behave like a real immutable CDN asset; everything else
        # must never be reused during QA (stale-build traps)
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if "/img/" in self.path
                         else "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if not os.path.isfile(path):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            self._log(0, 0, "404")
            return
        raw = open(path, "rb").read()
        ctype = self.guess_type(path)
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        body, enc = raw, None
        if accepts_gzip and ctype in GZIP_TYPES and len(raw) > 512:
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as g:
                g.write(raw)
            if len(buf.getvalue()) < len(raw):
                body, enc = buf.getvalue(), "gzip"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if enc:
            self.send_header("Content-Encoding", enc)
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Raw-Size", str(len(raw)))
        self.end_headers()
        self.wfile.write(body)
        self._log(len(body), len(raw), ctype)

    def _log(self, sent, raw, ctype):
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{self.path}\t{ctype}\t{raw}\t{sent}\n")


if __name__ == "__main__":
    os.chdir(ROOT)
    srv = HTTPServer(("127.0.0.1", PORT), H)
    print(f"serving {ROOT} on http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()
