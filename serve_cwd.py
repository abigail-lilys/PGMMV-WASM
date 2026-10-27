import http.server
import socketserver
import os
import sys

PORT = 8000
if len(sys.argv) > 1:
    PORT = int(sys.argv[1])

class ThreadingHTTPHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    
    def end_headers(self):
        # 跨源隔离头，保证 SharedArrayBuffer 可用
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

# 用 ThreadingHTTPServer 代替单线程的 HTTPServer
class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


print(f"Serving at http://127.0.0.1:{PORT}")
httpd = ThreadingHTTPServer(("127.0.0.1", PORT), ThreadingHTTPHandler)
httpd.serve_forever()
