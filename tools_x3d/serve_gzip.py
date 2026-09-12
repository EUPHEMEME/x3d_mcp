#!/usr/bin/env python3
# serve_gzip.py v1.0 (2026-08-31) — stdlib static server for the x3d_mcp demos:
# when the client accepts gzip and a sibling <file>.gz exists, serve the .gz with
# Content-Encoding: gzip and the Content-Type of the BASE name; else serve plain.
# Usage: python3 tools_x3d/serve_gzip.py [port]   (default 8099, serves repo root)
import http.server
import os
import sys


class GzipHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        gz = path + ".gz"
        if accepts_gzip and not path.endswith(".gz") and os.path.isfile(gz):
            try:
                f = open(gz, "rb")
            except OSError:
                return super().send_head()
            st = os.fstat(f.fileno())
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(st.st_size))
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Last-Modified", self.date_time_string(st.st_mtime))
            self.end_headers()
            return f
        return super().send_head()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)
    server = http.server.ThreadingHTTPServer(("", port), GzipHandler)
    print(f"serve_gzip.py v1.0 — serving {repo_root} on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
