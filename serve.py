#!/usr/bin/env python3
# Static server with the cross-origin-isolation headers that -pthread (SharedArrayBuffer) needs.
# Usage: cd build/web && python3 ../../serve.py   ->  http://127.0.0.1:8000/hello_app.html
import http.server, socketserver

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', 8000), Handler) as srv:
    print('serving on http://127.0.0.1:8000/')
    srv.serve_forever()
