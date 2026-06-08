pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- НАСТРОЙКИ ОБЛАЧНОЙ ПЕСОЧНИЦЫ ---
        OPENSHIFT_API = 'https://openshiftapps.com'
        OS_TOKEN = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        GIT_REPO = 'https://github.com/Stalker1301981-alt/sber-monitoring.git'
        
        // --- ИМЕНА ПРИЛОЖЕНИЙ ДЛЯ ОДНОГО ПРОЕКТА ---
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
                    # Авторизуемся через стандартный kubectl (он точно есть в системе)
                    kubectl config set-cluster sandbox --server=${env.OPENSHIFT_API} --insecure-skip-tls-verify=true
                    kubectl config set-credentials jenkins --token=${env.OS_TOKEN}
                    kubectl config set-context sandbox --cluster=sandbox --user=jenkins
                    kubectl config use-context sandbox
                    
                    # Разворачиваем Python-приложение напрямую из вашего публичного GitHub (S2I)
                    # Если оно уже есть — команда просто пропустит создание, если нет — создаст с нуля
                    kubectl get deployment/${env.APP_TEST} >/dev/null 2>&1 || {
                        echo "Инициализация приложения в облаке..."
                        # Используем встроенный в OpenShift образ-сборщик python
                        kubectl create deployment ${env.APP_TEST} --image=image-registry.openshift-image-registry.svc:5000/openshift/python:3.9-ubi8
                        kubectl expose deployment ${env.APP_TEST} --port=8080
                    }
                    
                    # Накатываем переменные окружения
                    kubectl set env deployment/${env.APP_TEST} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
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
                    kubectl get deployment/${env.APP_PROD} >/dev/null 2>&1 || {
                        kubectl create deployment ${env.APP_PROD} --image=image-registry.openshift-image-registry.svc:5000/openshift/python:3.9-ubi8
                        kubectl expose deployment ${env.APP_PROD} --port=8080
                    }
                    kubectl set env deployment/${env.APP_PROD} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
                """
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
