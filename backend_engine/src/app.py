from sanic import Sanic
from sanic.response import json
from pathlib import Path
import os
from dotenv import load_dotenv
from db import init_db
import logging

# Initialize Sanic app
app = Sanic("backend_engine")

# Set up logging
logging.basicConfig(level=logging.INFO)
app.ctx.logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent.parent / 'config.env'
load_dotenv(env_path)

# Configure app settings from environment variables
app.config.update({
    'DATABASE_URL': os.getenv('DATABASE_URL'),
    'SECRET_KEY': os.getenv('SECRET_KEY'),
    'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
    'ARTIFACTORY_URL': os.getenv('ARTIFACTORY_URL'),
    'LOGSTORE_URL': os.getenv('LOGSTORE_URL'),
    'BACKEND_ENGINE_URL': os.getenv('BACKEND_ENGINE_URL'),
    'FRONTEND_URL': os.getenv('FRONTEND_URL')
})

# Import blueprints
from blueprints.grid import bp as grid_bp
from blueprints.task import bp as task_bp
from blueprints.worker import bp as worker_bp

# Register blueprints
app.blueprint(grid_bp)
app.blueprint(task_bp)
app.blueprint(worker_bp)

@app.route("/health")
async def health_check(request):
    return json({"status": "healthy"})

async def setup_db(app, _):
    app.ctx.logger.info("Initializing database...")
    await init_db()
    app.ctx.logger.info("Database initialized successfully")

# Register startup listener
app.register_listener(setup_db, "before_server_start")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=app.config.DEBUG,
        auto_reload=app.config.DEBUG,
        workers=1,  # Use single worker for container
        access_log=True  # Enable access logs for debugging
    )
