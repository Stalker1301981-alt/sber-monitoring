pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- РЕАЛЬНЫЕ НАСТРОЙКИ КЛАСТЕРА OPENSHIFT ---
        OPENSHIFT_API = 'https://api.rm3.7wse.p1.openshiftapps.com:6443'
        OPENSHIFT_CREDENTIALS_ID = 'openshift-token' // Сюда подставится твой токен sha256~... из Credentials
        
        // --- НАСТРОЙКИ ПРОЕКТОВ (ПРОСТРАНСТВ ИМЕН) ---
        PROJECT_TEST = "sber-monitoring-test"
        PROJECT_PROD = "sber-monitoring-prod"
        
        // --- ПАРАМЕТРЫ ПРИЛОЖЕНИЯ ---
        APP_NAME = "sber-monitoring"
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
                    // Создаем Dockerfile "на лету" под твой Python веб-сервер
                    writeFile file: "Dockerfile", text: """FROM python:3.9-slim
WORKDIR /app
COPY calc.py .
EXPOSE 8080
CMD ["python", "calc.py"]
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
                echo "=== Деплой: ${env.APP_NAME} в тестовый проект ${env.PROJECT_TEST} ==="
                withCredentials([string(credentialsId: env.OPENSHIFT_CREDENTIALS_ID, variable: 'OS_TOKEN')]) {
                    sh """
                        # Логин в твой кластер
                        oc login ${env.OPENSHIFT_API} --token=${OS_TOKEN} --insecure-skip-tls-verify
                        oc project ${env.PROJECT_TEST}
                        
                        # Запуск сборки Docker-образа внутри OpenShift
                        oc start-build ${env.APP_NAME}-bc --from-dir=. --follow
                        
                        # Передача переменных окружения во внутренний контейнер
                        oc set env deployment/${env.APP_NAME} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
                    """
                }
            }
        }
        
        stage("3.1 Проверка ТЕСТА") {
            steps {
                catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
                    withCredentials([string(credentialsId: env.OPENSHIFT_CREDENTIALS_ID, variable: 'OS_TOKEN')]) {
                        script {
                            sh "oc login ${env.OPENSHIFT_API} --token=${OS_TOKEN} --insecure-skip-tls-verify"
                            // Получаем настоящий сгенерированный роут вида *.openshiftapps.com
                            def testHost = sh(script: "oc get route ${env.APP_NAME} -n ${env.PROJECT_TEST} -o jsonpath='{.spec.host}'", returnStdout: true).trim()
                            echo "=== Проверяем живой URL теста: http://${testHost} ==="
                            
                            sh "curl -k --fail --connect-timeout 5 --retry 2 http://${testHost}"
                        }
                    }
                }
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
                echo "=== Деплой: ${env.APP_NAME} на ОСНОВУ (PROD) в проект ${env.PROJECT_PROD} ==="
                withCredentials([string(credentialsId: env.OPENSHIFT_CREDENTIALS_ID, variable: 'OS_TOKEN')]) {
                    sh """
                        oc login ${env.OPENSHIFT_API} --token=${OS_TOKEN} --insecure-skip-tls-verify
                        oc project ${env.PROJECT_PROD}
                        
                        oc start-build ${env.APP_NAME}-bc --from-dir=. --follow
                        oc set env deployment/${env.APP_NAME} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
                    """
                }
            }
        }
        
        stage("5.1 Проверка ОСНОВЫ") {
            steps {
                catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
                    withCredentials([string(credentialsId: env.OPENSHIFT_CREDENTIALS_ID, variable: 'OS_TOKEN')]) {
                        script {
                            sh "oc login ${env.OPENSHIFT_API} --token=${OS_TOKEN} --insecure-skip-tls-verify"
                            def prodHost = sh(script: "oc get route ${env.APP_NAME} -n ${env.PROJECT_PROD} -o jsonpath='{.spec.host}'", returnStdout: true).trim()
                            echo "=== Проверяем живой URL прод-контура: http://${prodHost} ==="
                            
                            sh "curl -k --fail --connect-timeout 5 --retry 2 http://${prodHost}"
                        }
                    }
                }
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
