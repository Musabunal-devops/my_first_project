pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/USERNAME/REPO_NAME.git'
            }
        }
        stage('Build') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
    }
}