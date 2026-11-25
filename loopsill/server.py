from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore
import logging

from .errors import MediaError
from .request import Request
from .routes import get, post, result
from .workbench import Workbench


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(12)
        super().setup()

    def do_GET(self):
        self.respond(get)

    def do_POST(self):
        origin = self.headers.get('Origin')
        host = self.headers.get('Host')
        if origin and origin != f'http://{host}':
            self.reply(*result({'error': '请从同一个本地工位打开页面'}, 403))
            return
        self.respond(post)

    def respond(self, action):
        if not self.server.slots.acquire(blocking=False):
            self.reply(*result({'error': '工位正处理多项媒体操作，请稍候'}, 503))
            return
        try:
            try:
                response = action(self.server.app, Request(self))
            except MediaError as exc:
                response = result({'error': str(exc)}, exc.status)
            except TimeoutError:
                response = result({'error': '请求读取超时'}, 408)
            except (ValueError, OverflowError):
                response = result({'error': '请求地址或字段无效'}, 400)
            except Exception:
                logging.exception('工位处理失败')
                response = result({'error': '本地工位处理失败，请查看服务日志'}, 500)
            self.reply(*response)
        finally:
            self.server.slots.release()

    def reply(self, code, content_type, body, headers):
        try:
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; object-src 'none'; frame-ancestors 'none'")
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True


class ProjectionServer(ThreadingHTTPServer):
    request_queue_size = 16

    def __init__(self, address, app):
        self.app = app
        self.slots = BoundedSemaphore(6)
        super().__init__(address, Handler)


def serve(root, port):
    with ProjectionServer(('127.0.0.1', port), Workbench(root)) as server:
        print(f'环映台已打开 http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()
