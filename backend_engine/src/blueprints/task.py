from sanic import Blueprint
from sanic.response import json
from lib.task import get_all_tasks, get_task_by_uid, create_new_task, assign_task_to_worker, update_task_status

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

    if "worker" in request.args:
        response = await assign_task_to_worker(request.args.get("worker"))
        return json(response)
    
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

@bp.route("/<task_id>/result", methods=["POST"])
async def update_task_result(request, task_id):
    """Update task result"""
    data = request.json
    
    if not data:
        return json({"error": "No data provided"}, status=400)
    
    success = data.get("success", False)
    result = data.get("result")
    error = data.get("error")
    worker_uid = data.get("worker_uid")
    
    # Update task status and result
    updated = await update_task_status(
        task_id, 
        "completed" if success else "failed",
        result=result,
        error=error,
        worker_uid=worker_uid
    )
    
    if not updated:
        return json({"error": f"Failed to update task {task_id}"}, status=500)
    
    return json({"success": True, "message": f"Task {task_id} updated successfully"})