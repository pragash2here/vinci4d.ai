from sanic import Blueprint
from sanic.response import json

bp = Blueprint('worker', url_prefix='/worker')

@bp.route("/")
async def list_workers(request):
    return json({"message": "List of all workers"})

@bp.route("/<worker_id>")
async def get_worker(request, worker_id):
    return json({"message": f"Details of worker {worker_id}"})

@bp.route("/<worker_id>/status")
async def get_worker_status(request, worker_id):
    return json({"message": f"Status of worker {worker_id}"})

@bp.route("/register", methods=["POST"])
async def register_worker(request):
    return json({"message": "Register new worker"}) 