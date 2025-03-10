#! /bin/bash

# Create the postgres database
kubectl apply -f postgres/postgres_deployment.yaml

# Build the backend engine Docker image
docker build -t backend_engine:latest .

# Push the backend engine Docker image to the docker registry
docker push backend_engine:latest

# Deploy the backend engine to the Kubernetes cluster
kubectl apply -f backend_engine/k8s/deployment.yaml

