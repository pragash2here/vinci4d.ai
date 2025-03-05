from sanic import Blueprint
from sanic.response import json
from lib.grid import get_all_grids, get_grid_by_uid, create_new_grid, activate_grid, pause_grid, terminate_grid

grid_bp = Blueprint('grids', url_prefix='/api/grids')

@grid_bp.get('/')
async def get_grids(request):
    """Get all grids"""
    grids = await get_all_grids()
    return json(grids)

@grid_bp.get('/<uid>')
async def get_grid(request, uid):
    """Get a specific grid"""
    grid = await get_grid_by_uid(uid)
    
    if not grid:
        return json({"error": f"Grid with UID {uid} not found"}, status=404)
    
    return json(grid)

@grid_bp.post('/')
async def create_grid(request):
    """Create a new grid"""
    data = request.json
    
    # Validate required fields
    required_fields = ['name', 'length', 'width']
    for field in required_fields:
        if field not in data:
            return json({"error": f"Missing required field: {field}"}, status=400)
    
    grid = await create_new_grid(data)
    return json(grid)

@grid_bp.post('/<uid>/activate')
async def activate_grid_api(request, uid):
    """Activate a grid"""
    result = await activate_grid(uid)
    
    if result:
        return json({"message": f"Grid {uid} activated successfully"})
    else:
        return json({"error": f"Failed to activate grid {uid}"}, status=400)

@grid_bp.post('/<uid>/pause')
async def pause_grid_api(request, uid):
    """Pause a grid"""
    result = await pause_grid(uid)
    
    if result:
        return json({"message": f"Grid {uid} paused successfully"})
    else:
        return json({"error": f"Failed to pause grid {uid}"}, status=400)

@grid_bp.post('/<uid>/terminate')
async def terminate_grid_api(request, uid):
    """Terminate a grid"""
    result = await terminate_grid(uid)
    
    if result:
        return json({"message": f"Grid {uid} terminated successfully"})
    else:
        return json({"error": f"Failed to terminate grid {uid}"}, status=400) 