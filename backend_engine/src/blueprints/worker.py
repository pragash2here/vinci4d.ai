from sanic import Blueprint
from sanic.response import json
from lib.worker import get_all_workers, get_worker_by_uid, set_worker_online, set_worker_offline

bp = Blueprint("worker", url_prefix="/api/workers")

@bp.route("/", methods=["GET"])
async def get_workers(request):
    """Get all workers with optional filters"""
    filters = {}
    
    if "grid" in request.args:
        filters["grid_uid"] = request.args.get("grid")
    
    if "status" in request.args:
        filters["status"] = request.args.get("status")
    
    workers = await get_all_workers(filters)
    return json(workers)

@bp.route("/<uid>", methods=["GET"])
async def get_worker(request, uid):
    """Get a specific worker by UID"""
    worker = await get_worker_by_uid(uid)
    
    if not worker:
        return json({"error": f"Worker with UID {uid} not found"}, status=404)
    
    return json(worker)

@bp.route("/<uid>/online", methods=["POST"])
async def set_worker_online_endpoint(request, uid):
    """Set a worker status to online"""
    result = await set_worker_online(uid)
    
    if result:
        return json({"message": f"Worker {uid} is now online"})
    else:
        return json({"error": f"Failed to set worker {uid} online"}, status=400)

@bp.route("/<uid>/offline", methods=["POST"])
async def set_worker_offline_endpoint(request, uid):
    """Set a worker status to offline"""
    result = await set_worker_offline(uid)
    
    if result:
        return json({"message": f"Worker {uid} is now offline"})
    else:
        return json({"error": f"Failed to set worker {uid} offline"}, status=400) 