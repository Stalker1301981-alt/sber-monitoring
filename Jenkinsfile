pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- ЧЕТКИЕ НАСТРОЙКИ КЛАСТЕРА И ТОКЕНА ---
        OPENSHIFT_API = 'https://openshiftapps.com'
        OS_TOKEN = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        
        // --- ИМЕНА ПРИЛОЖЕНИЙ ---
        APP_TEST = "sber-monitoring-test"
        APP_PROD = "sber-monitoring-prod"
        
        APP_VERSION = "2.0"
        DRUID_HOST = "druid-broker.infra.svc.cluster.local"
        DRUID_PORT = "8082"
    }
    stages {
        stage("1. Подготовка кода") {
            steps {
                echo "=== Создание эталонных файлов проекта calc ==="
                deleteDir()
                script {
                    writeFile file: "calc.py", text: """from http.server import BaseHTTPRequestHandler, HTTPServer
import os, sys
APP_VERSION = "${env.APP_VERSION}"
DRUID_HOST = os.environ.get("DRUID_HOST", "${env.DRUID_HOST}")
DRUID_PORT = int(os.environ.get("DRUID_PORT", ${env.DRUID_PORT}))
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
                echo "=== Деплой ТЕСТ через Kubernetes CLI ==="
                sh """
                    # 1. Авторизация и жесткая привязка к правильному серверу API
                    kubectl config set-cluster sandbox --server=${env.OPENSHIFT_API} --insecure-skip-tls-verify=true
                    kubectl config set-credentials jenkins --token=${env.OS_TOKEN}
                    kubectl config set-context sandbox --cluster=sandbox --user=jenkins
                    kubectl config use-context sandbox
                    
                    # 2. Автоматическое определение имени вашего Sandbox-проекта из токена
                    # (Скрипт сам поймет, какой namespace вам выделило облако Red Hat)
                    MY_NAMESPACE=\$(kubectl target-namespace 2>/dev/null || kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "")
                    if [ -z "\$MY_NAMESPACE" ]; then
                        # Резервный способ определения namespace через запрос к API
                        MY_NAMESPACE=\$(curl -k -s -H "Authorization: Bearer ${env.OS_TOKEN}" "${env.OPENSHIFT_API}/apis/project.openshift.io/v1/projects" | grep -o '"name": "[^"]*' | head -n 1 | sed 's/"name": "//')
                    fi
                    echo "Обнаружен рабочий namespace: \$MY_NAMESPACE"
                    
                    # 3. Деплой в определенный Sandbox-проект
                    kubectl get deployment/${env.APP_TEST} -n \$MY_NAMESPACE >/dev/null 2>&1 || {
                        echo "Инициализация приложения sber-monitoring-test..."
                        # Берем официальный стабильный образ python
                        kubectl create deployment ${env.APP_TEST} --image=python:3.9-slim -n \$MY_NAMESPACE
                        kubectl expose deployment ${env.APP_TEST} --port=8080 -n \$MY_NAMESPACE
                    }
                    
                    # 4. Накатываем переменные окружения в этот проект
                    kubectl set env deployment/${env.APP_TEST} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} -n \$MY_NAMESPACE --overwrite
                """
            }
        }
        
        stage("4. Ожидание одобрения") {
            options { timeout(time: 1, unit: "DAYS") }
            steps {
                script {
                    input message: "Отправить версию ${env.APP_VERSION} на боевой (PROD)?",
                        ok: "Да, выкатываем!"
                }
            }
        }
        
        stage("5. Деплой на ОСНОВУ") {
            steps {
                echo "=== Деплой ПРОД через Kubernetes CLI ==="
                sh """
                    # Повторяем логику определения namespace для прода
                    MY_NAMESPACE=\$(kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "")
                    if [ -z "\$MY_NAMESPACE" ]; then
                        MY_NAMESPACE=\$(curl -k -s -H "Authorization: Bearer ${env.OS_TOKEN}" "${env.OPENSHIFT_API}/apis/project.openshift.io/v1/projects" | grep -o '"name": "[^"]*' | head -n 1 | sed 's/"name": "//')
                    fi
                    
                    kubectl get deployment/${env.APP_PROD} -n \$MY_NAMESPACE >/dev/null 2>&1 || {
                        kubectl create deployment ${env.APP_PROD} --image=python:3.9-slim -n \$MY_NAMESPACE
                        kubectl expose deployment ${env.APP_PROD} --port=8080 -n \$MY_NAMESPACE
                    }
                    kubectl set env deployment/${env.APP_PROD} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} -n \$MY_NAMESPACE --overwrite
                """
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
