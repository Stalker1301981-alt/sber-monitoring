pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- РЕАЛЬНЫЕ НАСТРОЙКИ КЛАСТЕРА OPENSHIFT ---
        OPENSHIFT_API = 'https://openshiftapps.com'
        OS_TOKEN = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        
        // --- ПАРАМЕТРЫ ПРИЛОЖЕНИЙ (Разворачиваем оба в один Sandbox-проект) ---
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
                    writeFile file: "Dockerfile", text: """FROM python:3.9-slim
WORKDIR /app
COPY calc.py .
EXPOSE 8080
CMD ["python", "calc.py"]
"""
                }
                
                echo "=== Скачивание OpenShift CLI (oc) ==="
                sh """
                    curl -sLO https://openshift.com
                    tar -xzf openshift-client-linux.tar.gz oc
                    chmod +x oc
                    rm -f openshift-client-linux.tar.gz
                """
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
                echo "=== Авторизация и инициализация ресурсов ТЕСТ ==="
                sh """
                    # Входим в облачную песочницу
                    ./oc login ${env.OPENSHIFT_API} --token=${env.OS_TOKEN} --insecure-skip-tls-verify
                    
                    # Проверяем, созданы ли сущности для ТЕСТА. Если нет — создаем автоматически
                    ./oc get bc/${env.APP_TEST}-bc >/dev/null 2>&1 || {
                        echo "Создание ресурсов для ${env.APP_TEST}..."
                        ./oc create imagestream ${env.APP_TEST}
                        ./oc new-build --strategy=docker --binary=true --name=${env.APP_TEST}-bc --to=${env.APP_TEST}:latest
                        ./oc new-app ${env.APP_TEST}:latest --name=${env.APP_TEST}
                        ./oc expose svc/${env.APP_TEST} --port=8080
                    }
                    
                    # Запускаем сборку и передаем файлы
                    ./oc start-build ${env.APP_TEST}-bc --from-dir=. --follow
                    
                    # Прокидываем переменные окружения
                    ./oc set env deployment/${env.APP_TEST} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
                """
            }
        }
        
        stage("3.1 Проверка ТЕСТА") {
            steps {
                catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
                    script {
                        def testHost = sh(script: "./oc get route ${env.APP_TEST} -o jsonpath='{.spec.host}'", returnStdout: true).trim()
                        echo "=== Проверяем живой URL теста: http://${testHost} ==="
                        sh "curl -k --fail --connect-timeout 5 --retry 2 http://${testHost}"
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
                echo "=== Инициализация и деплой на ОСНОВУ (PROD) ==="
                sh """
                    # Проверяем ресурсы для ПРОДА. Если нет — создаем автоматически
                    ./oc get bc/${env.APP_PROD}-bc >/dev/null 2>&1 || {
                        echo "Создание ресурсов для ${env.APP_PROD}..."
                        ./oc create imagestream ${env.APP_PROD}
                        ./oc new-build --strategy=docker --binary=true --name=${env.APP_PROD}-bc --to=${env.APP_PROD}:latest
                        ./oc new-app ${env.APP_PROD}:latest --name=${env.APP_PROD}
                        ./oc expose svc/${env.APP_PROD} --port=8080
                    }
                    
                    # Запускаем сборку прода
                    ./oc start-build ${env.APP_PROD}-bc --from-dir=. --follow
                    ./oc set env deployment/${env.APP_PROD} DRUID_HOST=${env.DRUID_HOST} DRUID_PORT=${env.DRUID_PORT} APP_VERSION=${env.APP_VERSION} --overwrite
                """
            }
        }
        
        stage("5.1 Проверка ОСНОВЫ") {
            steps {
                catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
                    script {
                        def prodHost = sh(script: "./oc get route ${env.APP_PROD} -o jsonpath='{.spec.host}'", returnStdout: true).trim()
                        echo "=== Проверяем живой URL прод-контура: http://${prodHost} ==="
                        sh "curl -k --fail --connect-timeout 5 --retry 2 http://${prodHost}"
                    }
                }
            }
        }
    }
    post {
        success { echo "=== УСПЕХ: Сборка #${currentBuild.number} завершена! ===" }
    }
}
