pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- ЧЕТКИЕ РЕАЛЬНЫЕ НАСТРОЙКИ КЛАСТЕРА SANDBOX ---
        OPENSHIFT_API = 'https://openshiftapps.com'
        OS_TOKEN = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        
        // --- ТВОЙ ЛИЧНЫР ПРОЕКТ В ПЕСОЧНИЦЕ ---
        MY_NAMESPACE = "kovaliov2700-dev"
        
        // --- ИМЕНА ПРИЛОЖЕНИЙ ДЛЯ ТЕСТА И ПРОДА ---
        APP_TEST = "sber-monitoring-test"
        APP_PROD = "sber-monitoring-prod"
        
        APP_VERSION = "2.0"
        DRUID_HOST = "druid-broker.infra.svc.cluster.local"
        DRUID_PORT = "8082"
    }
    stages {
        stage("1. Подготовка кода") {
            steps {
                echo "=== Создание файлов проекта ==="
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
                echo "=== Деплой ТЕСТ в пространство ${env.MY_NAMESPACE} ==="
                sh """
                    # 1. Настройка контекста kubectl с подстановкой реальной переменной OPENSHIFT_API
                    kubectl config set-cluster sandbox --server=${env.OPENSHIFT_API} --insecure-skip-tls-verify=true
                    kubectl config set-credentials jenkins --token=${env.OS_TOKEN}
                    kubectl config set-context sandbox --cluster=sandbox --user=jenkins --namespace=${env.MY_NAMESPACE}
                    kubectl config use-context sandbox
                    
                    # 2. Обновляем ConfigMap с кодом calc.py в OpenShift
                    kubectl delete configmap code-test -n ${env.MY_NAMESPACE} --ignore-not-found
                    kubectl create configmap code-test --from-file=calc.py -n ${env.MY_NAMESPACE}
                    
                    # 3. Проверяем и создаем Deployment, если его нет
                    kubectl get deployment/${env.APP_TEST} -n ${env.MY_NAMESPACE} >/dev/null 2>&1 || {
                        echo "Инициализация приложения sber-monitoring-test..."
                        kubectl create deployment ${env.APP_TEST} --image=python:3.9-slim -n ${env.MY_NAMESPACE} -- /bin/sh -c "python /code/calc.py"
                        kubectl expose deployment ${env.APP_TEST} --port=8080 --target-port=8080 -n ${env.MY_NAMESPACE}
                        
                        # Подключаем папку с кодом из ConfigMap внутрь контейнера
                        kubectl set volume deployment/${env.APP_TEST} --add --name=code-volume --type=configmap --configmap-name=code-test --mount-path=/code -n ${env.MY_NAMESPACE}
                    }
                    
                    # 4. Обновляем переменные и перезапускаем поды для применения нового кода
                    kubectl set env deployment/${env.APP_TEST} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} -n ${env.MY_NAMESPACE} --overwrite
                    kubectl rollout restart deployment/${env.APP_TEST} -n ${env.MY_NAMESPACE}
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
                echo "=== Деплой ПРОД в пространство ${env.MY_NAMESPACE} ==="
                sh """
                    # 1. Обновляем ConfigMap с кодом для ПРОДа
                    kubectl delete configmap code-prod -n ${env.MY_NAMESPACE} --ignore-not-found
                    kubectl create configmap code-prod --from-file=calc.py -n ${env.MY_NAMESPACE}
                    
                    # 2. Проверяем и создаем PROD Deployment
                    kubectl get deployment/${env.APP_PROD} -n ${env.MY_NAMESPACE} >/dev/null 2>&1 || {
                        echo "Инициализация приложения sber-monitoring-prod..."
                        kubectl create deployment ${env.APP_PROD} --image=python:3.9-slim -n ${env.MY_NAMESPACE} -- /bin/sh -c "python /code/calc.py"
                        kubectl expose deployment ${env.APP_PROD} --port=8080 --target-port=8080 -n ${env.MY_NAMESPACE}
                        
                        kubectl set volume deployment/${env.APP_PROD} --add --name=code-volume --type=configmap --configmap-name=code-prod --mount-path=/code -n ${env.MY_NAMESPACE}
                    }
                    
                    # 3. Накатываем переменные и перезапускаем
                    kubectl set env deployment/${env.APP_PROD} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} -n ${env.MY_NAMESPACE} --overwrite
                    kubectl rollout restart deployment/${env.APP_PROD} -n ${env.MY_NAMESPACE}
                """
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
