pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
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
        html = f"<h1>Сбер-Мониторинг v{APP_VERSION}</h1><p>Связь с Apache Druid: {DRUID_HOST}:{DRUID_PORT}</p>"
        self.wfile.write(html.encode("utf-8"))
if __name__ == "__main__":
    server_address = ("0.0.0.0", 8080)
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
        
        stage("2. Предварительное тестирование") {
            steps {
                echo "=== Запуск тестов ==="
                sh "python3 test_calc.py"
            }
        }
        
        stage("3. Деплой на ТЕСТ") {
            steps {
                echo "=== Деплой ТЕСТ в пространство kovaliov2700-dev ==="
                sh """
                    # Жестко прописываем прямые текстовые значения без использования переменных Jenkins
                    kubectl config set-cluster sandbox --server=https://openshiftapps.com --insecure-skip-tls-verify=true
                    kubectl config set-credentials jenkins --token=sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4
                    kubectl config set-context sandbox --cluster=sandbox --user=jenkins --namespace=kovaliov2700-dev
                    kubectl config use-context sandbox
                    
                    # Пересоздаем ConfigMap с кодом
                    kubectl delete configmap code-test -n kovaliov2700-dev --ignore-not-found
                    kubectl create configmap code-test --from-file=calc.py -n kovaliov2700-dev
                    
                    # Создаем Deployment sber-monitoring-test, если он отсутствует
                    kubectl get deployment/sber-monitoring-test -n kovaliov2700-dev >/dev/null 2>&1 || {
                        echo "Инициализация приложения sber-monitoring-test..."
                        kubectl create deployment sber-monitoring-test --image=python:3.9-slim -n kovaliov2700-dev -- /bin/sh -c "python /code/calc.py"
                        kubectl expose deployment sber-monitoring-test --port=8080 --target-port=8080 -n kovaliov2700-dev
                        
                        # Приматываем ConfigMap как том внутрь контейнера
                        kubectl set volume deployment/sber-monitoring-test --add --name=code-volume --type=configmap --configmap-name=code-test --mount-path=/code -n kovaliov2700-dev
                    }
                    
                    # Прописываем параметры среды и отправляем под в перезагрузку
                    kubectl set env deployment/sber-monitoring-test DRUID_HOST=druid-broker.infra.svc.cluster.local DRUID_PORT=8082 APP_VERSION=2.0 -n kovaliov2700-dev --overwrite
                    kubectl rollout restart deployment/sber-monitoring-test -n kovaliov2700-dev
                """
            }
        }
        
        stage("4. Ожидание одобрения") {
            options { timeout(time: 1, unit: "DAYS") }
            steps {
                script {
                    input message: "Отправить версию 2.0 на боевой (PROD)?",
                        ok: "Да, выкатываем!"
                }
            }
        }
        
        stage("5. Деплой на ОСНОВУ") {
            steps {
                echo "=== Деплой ПРОД в пространство kovaliov2700-dev ==="
                sh """
                    # Повторяем аналогичный чистый деплой для боевого контура
                    kubectl delete configmap code-prod -n kovaliov2700-dev --ignore-not-found
                    kubectl create configmap code-prod --from-file=calc.py -n kovaliov2700-dev
                    
                    kubectl get deployment/sber-monitoring-prod -n kovaliov2700-dev >/dev/null 2>&1 || {
                        echo "Инициализация приложения sber-monitoring-prod..."
                        kubectl create deployment sber-monitoring-prod --image=python:3.9-slim -n kovaliov2700-dev -- /bin/sh -c "python /code/calc.py"
                        kubectl expose deployment sber-monitoring-prod --port=8080 --target-port=8080 -n kovaliov2700-dev
                        
                        kubectl set volume deployment/sber-monitoring-prod --add --name=code-volume --type=configmap --configmap-name=code-prod --mount-path=/code -n kovaliov2700-dev
                    }
                    
                    kubectl set env deployment/sber-monitoring-prod DRUID_HOST=druid-broker.infra.svc.cluster.local DRUID_PORT=8082 APP_VERSION=2.0 -n kovaliov2700-dev --overwrite
                    kubectl rollout restart deployment/sber-monitoring-prod -n kovaliov2700-dev
                """
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
