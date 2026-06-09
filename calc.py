from http.server import BaseHTTPRequestHandler, HTTPServer
import os, sys, threading
from prometheus_client import start_http_server, Counter, Gauge, generate_latest

REQUESTS = Counter('app_requests_total', 'Total requests', ['method', 'path'])
APP_INFO = Gauge('app_info', 'App version info', ['version'])
ACTIVE_REQUESTS = Gauge('app_active_requests', 'Currently active requests')

APP_VERSION = os.environ.get('APP_VERSION', '1')
DRUID_HOST = os.environ.get('DRUID_HOST', 'druid-broker.infra.svc.cluster.local')
DRUID_PORT = int(os.environ.get('DRUID_PORT', 8082))
BUILD_URL = os.environ.get('BUILD_URL', 'local')

APP_INFO.labels(version=APP_VERSION).set(1)

class SberMonitoringWebsite(BaseHTTPRequestHandler):
    def do_GET(self):
        REQUESTS.labels(method='GET', path=self.path).inc()
        ACTIVE_REQUESTS.inc()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = '<h1>Сбер-Мониторинг v' + APP_VERSION + ' 🔥</h1>'
        html += '<p>Druid: ' + DRUID_HOST + ':' + str(DRUID_PORT) + '</p>'
        html += '<p>Build: ' + BUILD_URL + '</p>'
        self.wfile.write(html.encode('utf-8'))
        ACTIVE_REQUESTS.dec()

if __name__ == '__main__':
    threading.Thread(target=start_http_server, args=(8000,), daemon=True).start()
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, SberMonitoringWebsite)
    sys.stdout.flush()
    httpd.serve_forever()
