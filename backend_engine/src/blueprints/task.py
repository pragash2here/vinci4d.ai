from sanic import Blueprint
from sanic.response import json
from lib.task import get_all_tasks, get_task_by_uid, create_new_task

bp = Blueprint("task", url_prefix="/api/tasks")

@bp.route("/", methods=["GET"])
async def get_tasks(request):
    """Get all tasks with optional filters"""
    filters = {}
    
    if "function" in request.args:
        filters["function_uid"] = request.args.get("function")
    
    if "worker" in request.args:
        filters["worker_uid"] = request.args.get("worker")
    
    if "status" in request.args:
        filters["status"] = request.args.get("status")
    
    tasks = await get_all_tasks(filters)
    return json(tasks)

@bp.route("/<uid>", methods=["GET"])
async def get_task(request, uid):
    """Get a specific task by UID"""
    task = await get_task_by_uid(uid)
    
    if not task:
        return json({"error": f"Task with UID {uid} not found"}, status=404)
    
    return json(task)

@bp.route("/", methods=["POST"])
async def create_task(request):
    """Create a new task"""
    data = request.json
    
    # Validate required fields
    required_fields = ["function_uid", "worker_uid"]
    for field in required_fields:
        if field not in data:
            return json({"error": f"Missing required field: {field}"}, status=400)
    
    task = await create_new_task(data)
    return json(task, status=201)

@bp.route("/<task_id>/status")
async def get_task_status(request, task_id):
    """Get task status (shorthand endpoint)"""
    task = await get_task_by_uid(task_id)
    
    if not task:
        return json({"error": f"Task with UID {task_id} not found"}, status=404)
    
    return json({"status": task["status"]}) 