Requirements to deploy the application:

* Minikube or a Kubernetes cluster.

* Access to pull docker images from the docker registry.
  - Following upstream images are needed:
    - postgres:latest
    - python:3.11-slim

Deploying the application:

* checkout this repository
* run `sh deploy.sh`

Components:

* Postgres:
    - A postgres database is deployed to the Kubernetes cluster.
    - The database is used to store the application data.
    - The database is deployed using the `postgres/postgres_deployment.yaml` file.
    - The data is stored in the `postgres/data` directory which is mounted as a volume.

* Backend Engine:
    - The backend engine is deployed to the Kubernetes cluster.
    - The backend engine is deployed using the `backend_engine/k8s/deployment.yaml` file.

* CLI:
    - The cli is the vinci4d-cli. -> which translates to the `backend_engine/src/cli/main.py` file.