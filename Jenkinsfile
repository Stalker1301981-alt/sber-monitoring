pipeline {
    agent { label 'master' }
    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 1, unit: "HOURS")
        timestamps()
    }
    environment {
        OPENSHIFT_API = 'https://api.rm3.7wse.p1.openshiftapps.com:6443'
        NAMESPACE = 'kovaliov2700-dev'
        APP_NAME = 'sber-monitoring'
        APP_VERSION = "${BUILD_NUMBER}"
        IMAGE = "image-registry.openshift-image-registry.svc:5000/${NAMESPACE}/${APP_NAME}:${BUILD_NUMBER}"
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Test') {
            steps {
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
                sh '. venv/bin/activate && python test_app.py'
            }
        }
        stage('Login OpenShift') {
            steps {
                sh 'oc project ${NAMESPACE}'
            }
        }
        stage('Apply K8s Core') {
            steps {
                sh """
                    oc apply -f k8s/deployment.yaml -n ${NAMESPACE}
                    oc apply -f k8s/service.yaml -n ${NAMESPACE}
                    oc apply -f k8s/route.yaml -n ${NAMESPACE}
                """
            }
        }
        stage('Apply Monitoring') {
            steps {
                sh """
                    oc apply -f k8s/servicemonitor.yaml -n ${NAMESPACE} || true
                    oc apply -f k8s/prometheusrule.yaml -n ${NAMESPACE} || true
                    oc apply -f k8s/prometheus.yaml -n ${NAMESPACE}
                    oc apply -f k8s/grafana/configmap.yaml -n ${NAMESPACE}
                    oc apply -f k8s/grafana/deployment.yaml -n ${NAMESPACE}
                    oc apply -f k8s/grafana/service.yaml -n ${NAMESPACE}
                    oc apply -f k8s/grafana/route.yaml -n ${NAMESPACE}
                """
            }
        }
        stage('Build Image') {
            steps {
                script {
                    sh """
                        oc new-build --name=${APP_NAME} --binary --strategy=docker -n ${NAMESPACE} || true
                        oc start-build ${APP_NAME} --from-dir=. --wait -n ${NAMESPACE}
                        oc tag ${NAMESPACE}/${APP_NAME}:latest ${NAMESPACE}/${APP_NAME}:${BUILD_NUMBER} -n ${NAMESPACE}
                    """
                }
            }
        }
        stage('Deploy to TEST') {
            steps {
                sh """
                    oc set image deployment/${APP_NAME}-test app=${IMAGE} -n ${NAMESPACE}
                    oc set env deployment/${APP_NAME}-test APP_VERSION=${APP_VERSION} BUILD_URL=${BUILD_URL} -n ${NAMESPACE}
                    oc scale deployment/${APP_NAME}-test --replicas=1 -n ${NAMESPACE}
                """
            }
        }
        stage('Approve PROD') {
            options { timeout(time: 1, unit: "DAYS") }
            steps {
                input message: "Deploy build #${BUILD_NUMBER} to PROD?", ok: "Yes, deploy!"
            }
        }
        stage('Deploy to PROD') {
            steps {
                sh """
                    oc set image deployment/${APP_NAME}-prod app=${IMAGE} -n ${NAMESPACE}
                    oc set env deployment/${APP_NAME}-prod APP_VERSION=${APP_VERSION} BUILD_URL=${BUILD_URL} -n ${NAMESPACE}
                    oc scale deployment/${APP_NAME}-prod --replicas=2 -n ${NAMESPACE}
                """
            }
        }
    }
    post {
        success { echo "=== SUCCESS: Build #${BUILD_NUMBER} deployed ===" }
        failure { echo "=== FAILED: Build #${BUILD_NUMBER} ===" }
    }
}
