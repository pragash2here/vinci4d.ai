from sanic import Blueprint
from sanic.response import json
from lib.worker import get_all_workers, get_worker_by_uid, create_worker, create_workers_batch, set_worker_online, set_worker_offline, associate_worker_with_grid, delete_worker
from sqlalchemy.sql import text
import os

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

@bp.route("/", methods=["POST"])
async def create_worker_endpoint(request):
    """Create a new worker"""
    data = request.json
    
    # Validate required fields
    required_fields = ["grid_uid"]
    for field in required_fields:
        if field not in data:
            return json({"error": f"Missing required field: {field}"}, status=400)
    
    # Set default values if not provided
    if "name" not in data and "name_prefix" not in data:
        data["name"] = "worker"
    
    if "cpu_total" not in data:
        data["cpu_total"] = 2  # Default: 2 cores
    
    if "memory_total" not in data:
        data["memory_total"] = 4096  # Default: 4GB
    
    if "docker_image" not in data:
        data["docker_image"] = "python:3.11-slim"  # Set default Docker image
    
    # Check if we're creating a batch of workers
    if "count" in data and int(data["count"]) > 1:
        workers = await create_workers_batch(data)
        return json({"message": f"Created {len(workers)} workers", "workers": workers}, status=201)
    else:
        worker = await create_worker(data)
        return json(worker, status=201)

@bp.route("/<uid>/grid/<grid_uid>", methods=["POST"])
async def associate_worker_with_grid_endpoint(request, uid, grid_uid):
    """Associate a worker with a grid"""
    result = await associate_worker_with_grid(uid, grid_uid)
    
    if result:
        return json({"message": f"Worker {uid} associated with grid {grid_uid}"})
    else:
        return json({"error": f"Failed to associate worker {uid} with grid {grid_uid}"}, status=400)

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

@bp.route("/<uid>", methods=["DELETE"])
async def delete_worker_endpoint(request, uid):
    """Delete a worker"""
    result = await delete_worker(uid)
    
    if result:
        return json({"message": f"Worker {uid} deleted successfully"})
    else:
        return json({"error": f"Failed to delete worker {uid}"}, status=400)

@bp.route("/<uid>/deploy", methods=["POST"])
async def deploy_worker_endpoint(request, uid):
    """Deploy a worker to Kubernetes"""
    try:
        async for session in get_session():
            # Check if worker exists
            result = await session.execute(
                text("SELECT * FROM workers WHERE uid = :uid"),
                {"uid": uid}
            )
            worker = result.fetchone()
            
            if not worker:
                return json({"error": f"Worker {uid} not found"}, status=404)
            
            # Convert SQLAlchemy model to dict for deployer
            worker_dict = {
                "uid": worker.uid,
                "name": worker.name,
                "grid_uid": worker.grid_uid,
                "cpu_total": worker.cpu_total,
                "memory_total": worker.memory_total,
                "gpu_id": worker.gpu_id,
                "gpu_memory": worker.gpu_memory,
                "spec": worker.spec
            }
            
            # Deploy worker to Kubernetes
            from lib.k8ssdk import K8sDeployer
            namespace = os.environ.get("K8S_NAMESPACE", "default")
            deployer = K8sDeployer(namespace=namespace)
            
            # Deploy worker
            result = deployer.deploy_worker(worker_dict)
            
            if result:
                return json({"message": f"Worker {uid} deployed successfully"})
            else:
                return json({"error": f"Failed to deploy worker {uid}"}, status=500)
    except Exception as e:
        logger.error(f"Error deploying worker {uid}: {e}")
        return json({"error": f"Error deploying worker: {str(e)}"}, status=500) 