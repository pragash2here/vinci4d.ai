#! /bin/bash

# Create the postgres database
kubectl apply -f postgres/postgres_deployment.yaml

# Build the backend engine Docker image
cd backend_engine
docker build -t vinci4d-backend:latest .
# Push the backend engine Docker image to the docker registry
# docker push vinci4d-backend:latest

# Load the backend engine Docker image to the minikube cluster
minikube image load vinci4d-backend:latest

cd ..
# Deploy the backend engine to the Kubernetes cluster
kubectl apply -f backend_engine/k8s/deployment.yaml

