#! /bin/bash

kubectl delete -f postgres/postgres_deployment.yaml
kubectl delete -f backend_engine/k8s/deployment.yaml
