from sanic import Blueprint
from sanic.response import json
from lib.fn import get_all_functions, get_function_by_uid, create_new_function, update_function, start_function, cancel_function, check_function_status

bp = Blueprint("function", url_prefix="/api/functions")

@bp.route("/", methods=["GET"])
async def get_functions(request):
    """Get all functions"""
    functions = await get_all_functions()
    return json(functions)

@bp.route("/<uid>", methods=["GET"])
async def get_function(request, uid):
    """Get a specific function by UID"""
    function = await get_function_by_uid(uid)
    
    if not function:
        return json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return json(function)

@bp.route("/", methods=["POST"])
async def create_function(request):
    """Create a new function"""
    data = request.json
    
    # Validate required fields
    required_fields = ["name", "grid_uid", "script_path", "resource_requirements"]
    for field in required_fields:
        if field not in data:
            return json({"error": f"Missing required field: {field}"}, status=400)
    
    # Set default docker_image if not provided
    if "docker_image" not in data:
        data["docker_image"] = "default"
    
    function = await create_new_function(data)
    return json(function, status=201)

@bp.route("/<uid>", methods=["PUT"])
async def update_function_endpoint(request, uid):
    """Update a function"""
    data = request.json
    
    function = await update_function(uid, data)
    
    if not function:
        return json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return json(function)

@bp.route("/<uid>/start", methods=["POST"])
async def start_function_endpoint(request, uid):
    """Start a function"""
    result = await start_function(uid)
    
    if result:
        return json({"message": "Function started successfully"})
    
    return json({"error": "Failed to start function"}, status=500)

@bp.route("/<uid>/cancel", methods=["POST"])
async def cancel_function_endpoint(request, uid):
    """Cancel a function"""
    result = await cancel_function(uid)
    
    if result:
        return json({"message": "Function cancelled successfully"})
    
    return json({"error": "Failed to cancel function"}, status=500)

@bp.route("/<uid>/status", methods=["GET"])
async def check_function_status_endpoint(request, uid):
    """Check function status"""
    status = await check_function_status(uid)
    
    if status is None:
        return json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return json({"status": status}) 