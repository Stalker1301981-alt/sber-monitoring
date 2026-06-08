from http.server import BaseHTTPRequestHandler, HTTPServer
import os, sys
APP_VERSION = '1'
DRUID_HOST = os.environ.get('DRUID_HOST', 'druid-broker.infra.svc.cluster.local')
DRUID_PORT = int(os.environ.get('DRUID_PORT', 8082))
class SberMonitoringWebsite(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = '<h1>Сбер-Мониторинг v' + APP_VERSION + '</h1>'
        html += '<p>Druid: ' + DRUID_HOST + ':' + str(DRUID_PORT) + '</p>'
        html += '<p>Build: ' + os.environ.get('BUILD_URL', 'local') + '</p>'
        self.wfile.write(html.encode('utf-8'))
if __name__ == '__main__':
    server_address = ('0.0.0.0', 3000)
    httpd = HTTPServer(server_address, SberMonitoringWebsite)
    sys.stdout.flush()
    httpd.serve_forever()
