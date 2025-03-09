#!/usr/bin/env python3
import os
import logging
from sanic import Sanic
from sanic.response import json
from pathlib import Path
from dotenv import load_dotenv
from db import init_db

# Load environment variables
env_path = Path(__file__).parent.parent.parent / 'config.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Sanic app
app = Sanic("backend_engine")

# Set up app logger
app.ctx.logger = logger

# Configure app
app.config.CORS_ORIGINS = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.config.CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
app.config.CORS_ALWAYS_SEND = True

# Import blueprints
from blueprints.grid import grid_bp
from blueprints.fn import bp as fn_bp
from blueprints.task import bp as task_bp
from blueprints.worker import bp as worker_bp

# Register blueprints
app.blueprint(grid_bp)
app.blueprint(fn_bp)
app.blueprint(task_bp)
app.blueprint(worker_bp)

@app.route("/")
async def index(request):
    return json({
        "name": "Vinci4D Backend Engine API",
        "version": "0.1.0",
        "status": "running"
    })

@app.route("/health")
async def health(request):
    return json({
        "status": "healthy",
        "database": "connected"  # This should be checked dynamically
    })

async def setup_db(app, _):
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

# Register startup listener
app.register_listener(setup_db, "before_server_start")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting server on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug, workers=1)
