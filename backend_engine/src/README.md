# Design:
# Backend Engine:

# - The code runs a sanic server that will be used to manage the grid and the tasks.
# - The db is a pgsql database that will be used to store the grid and the tasks.
# - We will use asyncpg to connect to the db.
# - We will run the app as a microservice.
# - The app will run either locally or in a k8s cluster as a seperate.
# - The front end will get status of jobs / grid / tasks etc from the backend engine.
# - The metrics collector will collect metrics from the backend engine and store them in a metrics store.
# - The cli will also be part of the backend engine, and also can be run from anywhere as a script.

#  Postgres DB:
# - We will be using a postgres database, postgres provides high availability and a robust database.
#   - postgres is used because of high scale requirements of the tasks.
#   - Each task status has to be updated in the db.
#   - All objects will be stored in the db.

#  Artifacts:
#   - We will be using a seperate microservice to manage the artifacts.
#     - All the tasks/scripts will be stored here.
#     - When the user wants to run a task, the script is first uploaded to the artifactory service.
#     - Later when the user wants to execute the task, the artifactory service is used to get the script.

#  Metrics:
#   - We will be using a seperate microservice to manage the metrics.
#     - The metrics collector will collect the metrics from the backend engine and store them in a metrics store.
#     - The metrics will be used to monitor the backend engine.

#  CLI:
#   - The cli will be a seperate script that will be used to manage the backend engine.
#     - The cli will be used to create a grid, add tasks to the grid, get the status of the grid, etc.

#  Frontend:
#   - The frontend will be a seperate service that will be used to manage the frontend.
#     - The frontend will be used to get the status of the grid, add tasks to the grid, etc.

#  Logstore:
#   - The logstore will be a seperate service that will be used to store the logs of the tasks.
#     - The logstore will be used to store the logs of the tasks.


# We will use the following structure for the backend engine.  

- backend_engine/
    - src/
        - app.py
        - db.py    
        - README.md
        - lib/
            - grid.py
            - utils.py
            - kubesdk.py
            - task.py
            - artifacts.py
            - minikubeapi.py
            - worker.py
        - cli/
            - main.py
            - grid.py
            - task.py
            - artifacts.py
        - blueprints/
            - grid.py
            - task.py
            - artifacts.py
- .env
    - DATABASE_URL=sqlite:///./db.sqlite
    - SECRET_KEY=your_secret_key
    - DEBUG=True
    - ARTIFACTORY_URL=https://github.com/vinci-ai/vinci-ai.git
    - LOGSTORE_URL=https://github.com/vinci-ai/vinci-ai.git
    - BACKEND_ENGINE_URL=http://localhost:8000
    - FRONTEND_URL=http://localhost:3000
    - BACKEND_ENGINE_URL=http://localhost:8000
- tests/
