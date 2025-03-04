from sanic import Blueprint
from sanic.response import json

bp = Blueprint('task', url_prefix='/task')

@bp.route("/")
async def list_tasks(request):
    return json({"message": "List of all tasks"})

@bp.route("/<task_id>")
async def get_task(request, task_id):
    return json({"message": f"Details of task {task_id}"})

@bp.route("/", methods=["POST"])
async def create_task(request):
    return json({"message": "Create new task"})

@bp.route("/<task_id>/status")
async def get_task_status(request, task_id):
    return json({"message": f"Status of task {task_id}"}) 