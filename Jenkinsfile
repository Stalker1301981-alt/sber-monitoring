pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 2, unit: "HOURS")
        timestamps()
    }
    environment {
        // --- ДАННЫЕ ТВОЕГО OPENSHIFT CLUSTER ---
        OPENSHIFT_API = 'https://openshiftapps.com'
        OS_TOKEN = 'sha256~8HuHBQoZDsixfl8vKxOAvuh8Q5vT8U4wWxZzizberE4'
        MY_NAMESPACE = "kovaliov2700-dev"

        // --- ТВОИ ОРИГИНАЛЬНЫЕ НАСТРОЙКИ ---
        APP_VERSION = "${BUILD_NUMBER}"
        REGISTRY = "k3d-sber-registry:5000"
        IMAGE = "${REGISTRY}/sber-monitoring:${BUILD_NUMBER}"
        IMAGE_LATEST = "${REGISTRY}/sber-monitoring:latest"
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
APP_VERSION = '${env.APP_VERSION}'
DRUID_HOST = os.environ.get('DRUID_HOST', '${env.DRUID_HOST}')
DRUID_PORT = int(os.environ.get('DRUID_PORT', ${env.DRUID_PORT}))
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
"""
                    writeFile file: "test_calc.py", text: """import unittest, sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from calc import SberMonitoringWebsite, APP_VERSION
class TestSberMonitoring(unittest.TestCase):
    def test_app_version_exists(self):
        self.assertTrue(len(APP_VERSION) > 0)
    def test_website_class_exists(self):
        self.assertTrue(issubclass(SberMonitoringWebsite, object))
if __name__ == '__main__':
    unittest.main()
"""
                    writeFile file: "Dockerfile", text: """FROM python:3-slim
WORKDIR /app
COPY calc.py .
EXPOSE 3000
CMD ["python3", "calc.py"]
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
        stage("3. Сборка Docker образа") {
            steps {
                echo "=== Kaniko build & push ==="
                sh """
                    # Создаем конфиг локально в рабочей папке Jenkins, а не в корне системы
                    mkdir -p .docker
                    echo '{}' > .docker/config.json
                    
                    /usr/local/bin/executor \
                        --context=${WORKSPACE} \
                        --dockerfile=${WORKSPACE}/Dockerfile \
                        --destination=${IMAGE} \
                        --destination=${IMAGE_LATEST} \
                        --force --skip-tls-verify \
                        --insecure --insecure-registry=${REGISTRY}
                """
            }
        }
        stage("4. Обновление Git манифестов") {
            steps {
                sh """
                    sed -i 's|image: .*|image: ${IMAGE}|' ${WORKSPACE}/k8s/deployment.yaml
                    git config user.email "jenkins@sber-monitoring"
                    git config user.name "Jenkins CI"
                    git add k8s/deployment.yaml
                    git commit -m "Update image tag to ${BUILD_NUMBER}" || true
                    git push origin main
                """
            }
        }
        stage("5. Деплой через ArgoCD") {
            steps {
                echo "=== ArgoCD sync ==="
                sh """
                    argocd login localhost:8443 --username admin --password my3Somy9Mwkmp7fN --insecure
                    argocd app sync sber-monitoring --grpc-web
                """
            }
        }
        stage("6. Проверка деплоя") {
            steps {
                echo "=== Проверка статуса в облаке OpenShift ==="
                sh """
                    # Логин в твой живой OpenShift для контроля раскатки
                    kubectl config set-cluster sandbox --server=${env.OPENSHIFT_API} --insecure-skip-tls-verify=true
                    kubectl config set-credentials jenkins --token=${env.OS_TOKEN}
                    kubectl config set-context sandbox --cluster=sandbox --user=jenkins --namespace=${env.MY_NAMESPACE}
                    kubectl config use-context sandbox
                    
                    kubectl rollout status deployment/sber-monitoring --timeout=120s -n ${env.MY_NAMESPACE}
                """
            }
        }
        stage("7. Ожидание одобрения") {
            options { timeout(time: 1, unit: "DAYS") }
            steps {
                script {
                    input message: "Отправить версию ${env.APP_VERSION} на боевой?",
                        ok: "Да, выкатываем!"
                }
            }
        }
    }
    post {
        success {
            sh """
                echo "=== СБОРКА УСПЕШНА ==="
                echo "Сайт: http://172.20.0.3:3000"
                echo "Версия: ${APP_VERSION}"
            """
        }
    }
}
