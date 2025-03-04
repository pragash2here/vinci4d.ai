from sanic import Blueprint
from sanic.response import json

bp = Blueprint('grid', url_prefix='/grid')

@bp.route("/")
async def list_grids(request):
    return json({"message": "List of all grids"})

@bp.route("/<grid_id>")
async def get_grid(request, grid_id):
    return json({"message": f"Details of grid {grid_id}"})

@bp.route("/", methods=["POST"])
async def create_grid(request):
    return json({"message": "Create new grid"})

@bp.route("/<grid_id>", methods=["DELETE"])
async def delete_grid(request, grid_id):
    return json({"message": f"Delete grid {grid_id}"}) 