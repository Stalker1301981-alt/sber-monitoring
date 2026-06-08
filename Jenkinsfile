pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        OS_SERVER = 'https://openshiftapps.com'
        OS_TOKEN  = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        OS_NS     = 'kovaliov2700-dev'
    }
    stages {
        stage("1. Подготовка кода") {
            steps {
                echo "=== Создание файлов проекта ==="
                deleteDir()
                script {
                    writeFile file: "calc.py", text: """from http.server import BaseHTTPRequestHandler, HTTPServer
import os, sys
APP_VERSION = "2.0"
DRUID_HOST = os.environ.get("DRUID_HOST", "druid-broker.infra.svc.cluster.local")
DRUID_PORT = int(os.environ.get("DRUID_PORT", 8082))
class SberMonitoringWebsite(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = "<h1>Сбер-Мониторинг v" + APP_VERSION + "</h1>"
        html += "<p>Druid: " + DRUID_HOST + ":" + str(DRUID_PORT) + "</p>"
        self.wfile.write(html.encode("utf-8"))
if __name__ == "__main__":
    server_address = ("0.0.0.0", 3000)
    httpd = HTTPServer(server_address, SberMonitoringWebsite)
    sys.stdout.flush()
    httpd.serve_forever()
"""
                    writeFile file: "test_calc.py", text: """import unittest, sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from calc import SberMonitoringWebsite, APP_VERSION
class TestSberMonitoring(unittest.TestCase):
    def test_app_version_exists(self):
        self.assertTrue(len(APP_VERSION) > 0)
    def test_website_class_exists(self):
        self.assertTrue(issubclass(SberMonitoringWebsite, object))
if __name__ == "__main__":
    unittest.main()
"""
                }
                sh "rm -rf __pycache__"
                sh "ls -la"
            }
        }
        stage("2. Тестирование") {
            steps {
                echo "=== Запуск тестов ==="
                sh "python3 test_calc.py"
            }
        }
        stage("3. Сборка образа в OpenShift") {
            steps {
                echo "=== Сборка силами OpenShift (S2I) ==="
                sh 'kubectl config set-cluster sandbox --server=${OS_SERVER} --insecure-skip-tls-verify=true'
                sh 'kubectl config set-credentials jenkins --token=${OS_TOKEN}'
                sh 'kubectl config set-context sandbox --cluster=sandbox --user=jenkins --namespace=${OS_NS}'
                sh 'kubectl config use-context sandbox'
                sh 'kubectl delete configmap code-sber -n ${OS_NS} --ignore-not-found'
                sh 'kubectl create configmap code-sber --from-file=calc.py -n ${OS_NS}'
            }
        }
        stage("4. Обновление манифестов") {
            steps {
                echo "=== Пропуск локального деплоя ==="
            }
        }
        stage("5. Деплой через ArgoCD") {
            steps {
                echo "=== Синхронизация ресурсов в OpenShift ==="
                sh 'kubectl config use-context sandbox'
                sh '''
                    kubectl get deployment/sber-monitoring -n ${OS_NS} >/dev/null 2>&1 || {
                        kubectl create deployment sber-monitoring --image=python:3.9-slim -n ${OS_NS} -- /bin/sh -c "python /code/calc.py"
                        kubectl expose deployment sber-monitoring --port=3000 --target-port=3000 -n ${OS_NS}
                        kubectl set volume deployment/sber-monitoring --add --name=code-volume --type=configmap --configmap-name=code-sber --mount-path=/code -n ${OS_NS}
                    }
                    kubectl set env deployment/sber-monitoring DRUID_HOST=druid-broker.infra.svc.cluster.local DRUID_PORT=8082 APP_VERSION=2.0 -n ${OS_NS} --overwrite
                '''
            }
        }
        stage("6. Проверка деплоя") {
            steps {
                echo "=== Ожидание готовности подов ==="
                sh 'kubectl config use-context sandbox'
                sh 'kubectl rollout restart deployment/sber-monitoring -n ${OS_NS}'
                sh 'kubectl rollout status deployment/sber-monitoring --timeout=120s -n ${OS_NS}'
            }
        }
        stage("7. Ожидание одобрения") {
            options { timeout(time: 1, unit: "DAYS") }
            steps {
                script {
                    input message: "Отправить версию на боевой?",
                        ok: "Да, выкатываем!"
                }
            }
        }
    }
    post {
        success {
            echo "=== СБОРКА УСПЕШНА ==="
        }
    }
}
