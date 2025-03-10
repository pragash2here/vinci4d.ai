Requirements to deploy the application:

# Minikube or a Kubernetes cluster.
In mac:
    `brew install minikube`
    `minikube start`

# Access to pull docker images from the docker registry.
  - Following upstream images are needed:
    - postgres:latest
    - python:3.11-slim

Components:

# Postgres:
    - A postgres database is deployed to the Kubernetes cluster.
    - The database is used to store the application data.
    - The database is deployed using the `postgres/postgres_deployment.yaml` file.
    - The data is stored in the `postgres/data` directory which is mounted as a volume.

# Backend Engine:
    - The backend engine is deployed to the Kubernetes cluster.
    - The backend engine is deployed using the `backend_engine/k8s/deployment.yaml` file.

# CLI:
    - The cli is the vinci4d-cli. -> which translates to the `backend_engine/src/cli/main.py` file.

# Deploying the application:

* checkout this repository
* run `sh deploy.sh`

# Running the application:

* run `sh port-forward.sh` to forward the ports to the local machine.
* run `vinci4d-cli`

# Application Objects:

   * GRID:
        - Grid object translates to compute resources.
        - Grid has length and width
        - To create a grid: `vinci4d-cli grid create <grid_name> --length 10 --width 10`

   * Worker:
        - Worker object translates to k8s pod resources.
        - To create a worker: `vinci4d-cli worker create <worker_name> -g <grid_name>`
        - you can specify the cpu, memory, gpu, etc.

   * Task:
        - Task is the unit of work that is assigned to a worker.
        - Tasks can have multiple inputs.
        - To list all tasks: `vinci4d-cli task list`

   * FN:
        - FN is script which contains the buisness logic.
        - FN can have multiple inputs on which the script works on.
        - To create a FN: `vinci4d-cli fn create <fn_name> -g <grid_uuid> -s <script_path> -d <docker_image_name>`
        - To start a FN: `vinci4d-cli fn start <fn_uuid> -f <input_file_path>`
        - Sample input file: `{"input": [ "1", "2", "3" ], "batch_size": 1}`
        - To list all FNs: `vinci4d-cli fn list`