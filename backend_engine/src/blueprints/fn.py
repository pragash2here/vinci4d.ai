import os
import shutil
import json
from pathlib import Path
from sanic import Blueprint
from sanic.response import json as sanic_json, file as send_file
from lib.fn import (
    get_all_functions, 
    get_function_by_uid, 
    create_new_function, 
    update_function, 
    start_function, 
    cancel_function, 
    check_function_status,
    delete_function,
    update_script_path
)
from db import FunctionStatus
import logging
from uuid import uuid4
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)

bp = Blueprint("function", url_prefix="/api/functions")

# Create scripts directory if it doesn't exist
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)

@bp.route("/", methods=["GET"])
async def get_functions(request):
    """Get all functions with optional filters"""
    filters = {}
    
    if "grid" in request.args:
        filters["grid_uid"] = request.args.get("grid")
    
    if "status" in request.args:
        filters["status"] = request.args.get("status")
    
    functions = await get_all_functions(filters)
    return sanic_json(functions)

@bp.route("/<uid>", methods=["GET"])
async def get_function(request, uid):
    """Get a specific function by UID"""
    function = await get_function_by_uid(uid)
    
    if not function:
        return sanic_json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return sanic_json(function)

@bp.route("/<uid>/script", methods=["GET"])
async def get_function_script(request, uid):
    """Get a function script"""
    # return a file
    script_path = SCRIPTS_DIR / uid / "main.py"
    if not script_path.exists():
        return sanic_json({"error": f"Function script not found for {uid}"}, status=404)
    return await send_file(script_path)

@bp.route("/", methods=["POST"])
async def create_function_endpoint(request):
    """Create a new function"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ["name", "grid_uid", "resource_requirements"]
        for field in required_fields:
            if field not in data:
                return sanic_json({"error": f"Missing required field: {field}"}, status=400)
        
        # Check if we have script_content, script_path, or server_file_path
        if not any(key in data for key in ["script_content", "script_path", "server_file_path"]):
            return sanic_json({"error": "Either script_content, script_path, or server_file_path is required"}, status=400)
        
        # Set batch_size if provided
        if "batch_size" in data:
            try:
                batch_size = int(data["batch_size"])
                if batch_size < 1:
                    return sanic_json({"error": "batch_size must be at least 1"}, status=400)
                data["batch_size"] = batch_size
            except (ValueError, TypeError):
                return sanic_json({"error": "batch_size must be an integer"}, status=400)
        
        # Create function in database first to get the UID
        function = await create_new_function(data)
        
        if not function:
            return sanic_json({"error": "Failed to create function"}, status=500)
        
        try:
            # Create script directory for this function
            function_dir = SCRIPTS_DIR / function["uid"]
            function_dir.mkdir(exist_ok=True)
            
            # Save script to file
            script_path = function_dir / "main.py"
            
            if "script_content" in data:
                # Save script content directly
                script_content = data["script_content"]
                with open(script_path, "w") as f:
                    f.write(script_content)
            elif "script_path" in data:
                # Copy script file from local path
                source_path = data["script_path"]
                if os.path.exists(source_path):
                    shutil.copy(source_path, script_path)
                else:
                    # Clean up function if script file doesn't exist
                    await delete_function(function["uid"])
                    return sanic_json({"error": f"Script file not found: {source_path}"}, status=400)
            elif "server_file_path" in data:
                # Copy script file from server path (uploaded file)
                source_path = data["server_file_path"]
                if os.path.exists(source_path):
                    shutil.copy(source_path, script_path)
                    # Remove the temporary uploaded file
                    os.remove(source_path)
                else:
                    # Clean up function if script file doesn't exist
                    await delete_function(function["uid"])
                    return sanic_json({"error": f"Uploaded script file not found: {source_path}"}, status=400)
            
            # Update function with script path
            relative_path = str(script_path.relative_to(Path(__file__).parent.parent))
            logger.info(f"Setting script path for function {function['uid']} to {relative_path}")

            # Try using the update_script_path function first
            try:
                updated_function = await update_script_path(function["uid"], relative_path)
                
                if updated_function:
                    return sanic_json(updated_function, status=201)
                
                # If direct SQL update fails, try the regular update function
                logger.warning(f"Direct SQL update failed, trying ORM update for function {function['uid']}")
            except Exception as e:
                logger.error(f"Error in direct SQL update: {e}")

            # Fall back to the regular update function
            updated_function = await update_function(function["uid"], {"script_path": relative_path})

            if not updated_function:
                # Clean up if update fails
                await delete_function(function["uid"])
                if function_dir.exists():
                    shutil.rmtree(function_dir)
                return sanic_json({"error": f"Failed to update function with script path"}, status=500)

            return sanic_json(updated_function, status=201)
        
        except Exception as e:
            # Clean up on error
            logger.error(f"Error creating function: {e}")
            await delete_function(function["uid"])
            if function_dir.exists():
                shutil.rmtree(function_dir)
            return sanic_json({"error": f"Error creating function: {str(e)}"}, status=500)
    
    except Exception as e:
        logger.error(f"Error in function creation endpoint: {e}")
        return sanic_json({"error": f"Server error: {str(e)}"}, status=500)

@bp.route("/<uid>", methods=["PUT"])
async def update_function_endpoint(request, uid):
    """Update a function"""
    data = request.json
    
    function = await update_function(uid, data)
    
    if not function:
        return sanic_json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return sanic_json(function)

@bp.route("/<uid>/start", methods=["POST"])
async def start_function_endpoint(request, uid):
    """Start a function"""
    try:
        # Get parameters from request body if provided
        params = None
        if request.json and 'params' in request.json:
            try:
                # If params is a string, parse it as JSON
                if isinstance(request.json['params'], str):
                    try:
                        params = json.loads(request.json['params'])
                    except ValueError as e:  # Use ValueError instead of JSONDecodeError
                        logger.error(f"Invalid JSON parameters for function {uid}: {e}")
                        return sanic_json({"error": "Invalid JSON parameters"}, status=400)
                else:
                    params = request.json['params']
                logger.info(f"Starting function {uid} with parameters: {params}")
            except Exception as e:
                logger.error(f"Error processing parameters for function {uid}: {e}")
                return sanic_json({"error": f"Error processing parameters: {str(e)}"}, status=400)
        # Start the function with parameters
        result = await start_function(uid, params)
        
        if result:
            return sanic_json({"message": "Function started successfully"})
        
        return sanic_json({"error": "Failed to start function"}, status=500)
    except Exception as e:
        logger.error(f"Error starting function {uid}: {e}")
        return sanic_json({"error": f"Error starting function: {str(e)}"}, status=500)

@bp.route("/<uid>/cancel", methods=["POST"])
async def cancel_function_endpoint(request, uid):
    """Cancel a function"""
    result = await cancel_function(uid)
    
    if result:
        return sanic_json({"message": "Function cancelled successfully"})
    
    return sanic_json({"error": "Failed to cancel function"}, status=500)

@bp.route("/<uid>/status", methods=["GET"])
async def check_function_status_endpoint(request, uid):
    """Check function status"""
    status = await check_function_status(uid)
    
    if status is None:
        return sanic_json({"error": f"Function with UID {uid} not found"}, status=404)
    
    return sanic_json({"status": status})

@bp.route("/<uid>", methods=["DELETE"])
async def delete_function_endpoint(request, uid):
    """Delete a function"""
    # Delete function from database
    result = await delete_function(uid)
    
    if not result:
        return sanic_json({"error": f"Failed to delete function {uid}"}, status=400)
    
    # Delete function script directory
    function_dir = SCRIPTS_DIR / uid
    if function_dir.exists():
        shutil.rmtree(function_dir)
    
    return sanic_json({"message": f"Function {uid} deleted successfully"})

@bp.route("/upload", methods=["POST"])
async def upload_script(request):
    """Upload a script file"""
    try:
        if "file" not in request.files:
            return sanic_json({"error": "No file provided"}, status=400)
        
        file = request.files["file"][0]
        
        # Create a temporary directory for uploads if it doesn't exist
        upload_dir = Path(__file__).parent.parent / "scripts"
        upload_dir.mkdir(exist_ok=True)
        
        # Generate a unique filename
        filename = f"{uuid4()}.py"
        file_path = upload_dir / filename
        
        # Save the uploaded file
        with open(file_path, "wb") as f:
            f.write(file.body)
        
        # Return the file path for reference in function creation
        return sanic_json({
            "file_path": str(file_path),
            "filename": file.name
        })
    
    except Exception as e:
        logger.error(f"Error uploading script: {e}")
        return sanic_json({"error": f"Error uploading script: {str(e)}"}, status=500) 