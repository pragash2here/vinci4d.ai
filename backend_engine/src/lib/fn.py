from db import Function, FunctionStatus, Task, TaskStatus, Worker, WorkerStatus, get_session
from datetime import datetime
import asyncio
import logging
from sqlalchemy import text
from uuid import uuid4
import asyncpg
import os
import json

logger = logging.getLogger(__name__)

# Get database URL from environment
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgresql+asyncpg://'):
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

# Database access functions
async def get_all_functions(filters=None):
    """Get all functions from the database with optional filters"""
    functions_list = []
    
    async for session in get_session():
        # Build query based on filters
        query = "SELECT * FROM functions WHERE 1=1"
        params = {}
        
        if filters:
            if "grid_uid" in filters:
                query += " AND grid_uid = :grid_uid"
                params["grid_uid"] = filters["grid_uid"]
                
            if "status" in filters:
                query += " AND status = :status"
                params["status"] = filters["status"]
        
        result = await session.execute(text(query), params)
        functions = result.fetchall()
        
        for fn in functions:
            fn_dict = {
                "uid": fn.uid,
                "name": fn.name,
                "grid_uid": fn.grid_uid,
                "script_path": fn.script_path,
                "artifactory_url": fn.artifactory_url,
                "resource_requirements": fn.resource_requirements,
                "docker_image": fn.docker_image,
                "status": fn.status if not hasattr(fn.status, 'value') else fn.status.value,
                "created_at": fn.created_at.isoformat() if fn.created_at else None,
                "updated_at": fn.updated_at.isoformat() if fn.updated_at else None,
                "started_at": fn.started_at.isoformat() if fn.started_at else None,
                "ended_at": fn.ended_at.isoformat() if fn.ended_at else None
            }
            functions_list.append(fn_dict)
    
    return functions_list

async def get_function_by_uid(uid):
    """Get a function by its UID"""
    async for session in get_session():
        result = await session.execute(
            text("SELECT * FROM functions WHERE uid = :uid"),
            {"uid": uid}
        )
        fn = result.fetchone()
        
        if not fn:
            return None
        
        fn_dict = {
            "uid": fn.uid,
            "name": fn.name,
            "grid_uid": fn.grid_uid,
            "script_path": fn.script_path,
            "artifactory_url": fn.artifactory_url,
            "resource_requirements": fn.resource_requirements,
            "docker_image": fn.docker_image,
            "status": fn.status if not hasattr(fn.status, 'value') else fn.status.value,
            "created_at": fn.created_at.isoformat() if fn.created_at else None,
            "updated_at": fn.updated_at.isoformat() if fn.updated_at else None,
            "started_at": fn.started_at.isoformat() if fn.started_at else None,
            "ended_at": fn.ended_at.isoformat() if fn.ended_at else None
        }
        
        return fn_dict

async def create_new_function(data):
    """Create a new function in the database"""
    try:
        # Create function object
        function = Function(
            uid=str(uuid4()),
            name=data["name"],
            grid_uid=data["grid_uid"],
            script_path=data.get("script_path", ""),  # Will be updated after saving script
            artifactory_url=data.get("artifactory_url"),
            resource_requirements=data["resource_requirements"],
            docker_image=data.get("docker_image", "python:3.11-slim"),  # Use Python 3.11 slim as default
            status="ready",  # Use lowercase string directly
            batch_size=data.get("batch_size", 1),  # Default to 1 if not specified
            function_params=data.get("function_params", {}),  # Store default parameters
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        async for session in get_session():
            session.add(function)
            await session.commit()
            
            # Return function data
            return {
                "uid": function.uid,
                "name": function.name,
                "grid_uid": function.grid_uid,
                "script_path": function.script_path,
                "artifactory_url": function.artifactory_url,
                "resource_requirements": function.resource_requirements,
                "docker_image": function.docker_image,
                "status": "ready",  # Use lowercase string directly
                "batch_size": function.batch_size,
                "function_params": function.function_params,
                "created_at": function.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        return None

async def update_function(uid, data):
    """Update a function in the database"""
    try:
        logger.info(f"Updating function {uid} with data: {data}")
        
        # Use direct SQL update instead of ORM to avoid immutability issues
        async for session in get_session():
            update_clauses = []
            params = {"uid": uid}
            
            if "name" in data:
                update_clauses.append("name = :name")
                params["name"] = data["name"]
            
            if "script_path" in data:
                logger.info(f"Updating script path to: {data['script_path']}")
                update_clauses.append("script_path = :script_path")
                params["script_path"] = data["script_path"]
            
            if "artifactory_url" in data:
                update_clauses.append("artifactory_url = :artifactory_url")
                params["artifactory_url"] = data["artifactory_url"]
            
            if "resource_requirements" in data:
                update_clauses.append("resource_requirements = :resource_requirements")
                params["resource_requirements"] = data["resource_requirements"]
            
            if "docker_image" in data:
                update_clauses.append("docker_image = :docker_image")
                params["docker_image"] = data["docker_image"]
            
            if "status" in data:
                update_clauses.append("status = :status")
                params["status"] = data["status"]
            
            # Always update the updated_at timestamp
            update_clauses.append("updated_at = :updated_at")
            params["updated_at"] = datetime.utcnow()
            
            if not update_clauses:
                logger.warning(f"No fields to update for function {uid}")
                return await get_function_by_uid(uid)
            
            # Build and execute the update query
            update_query = f"UPDATE functions SET {', '.join(update_clauses)} WHERE uid = :uid"
            await session.execute(text(update_query), params)
            
            try:
                await session.commit()
                logger.info(f"Function {uid} updated successfully")
            except Exception as commit_error:
                logger.error(f"Error committing function update: {commit_error}")
                await session.rollback()
                raise
            
            # Return the updated function
            return await get_function_by_uid(uid)
    except Exception as e:
        logger.error(f"Error updating function {uid}: {e}")
        return None

# Existing functions with improved error handling
async def start_function(function_uid, params=None):
    """Start a function"""
    try:
        async for session in get_session():
            # Get the function
            result = await session.execute(
                text("SELECT * FROM functions WHERE uid = :uid"),
                {"uid": function_uid}
            )
            function = result.fetchone()
            
            if not function:
                logger.error(f"Function {function_uid} not found")
                return False
            
            # Check if function can be started - use lowercase values
            valid_statuses = [
                "ready", "pending", "running", "completed", "failed", "cancelled"
            ]
            
            if function.status not in valid_statuses:
                logger.error(f"Function {function_uid} cannot be started in {function.status} state")
                return False
            
            # Update function status - use lowercase directly
            try:
                await session.execute(
                    text("""
                    UPDATE functions 
                    SET status = 'running', 
                        started_at = :now,
                        updated_at = :now
                    WHERE uid = :uid
                    """),
                    {
                        "uid": function_uid,
                        "now": datetime.utcnow()
                    }
                )
                await session.commit()
            except Exception as e:
                logger.error(f"Error updating function status: {e}")
                return False
            
            # Determine batch size
            batch_size = function.batch_size if hasattr(function, 'batch_size') else 1
            
            # Override batch size from params if provided
            if params and isinstance(params, dict) and 'batch_size' in params:
                try:
                    batch_size = int(params['batch_size'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid batch_size in params: {params['batch_size']}, using default: {batch_size}")
            
            # Get inputs from params
            inputs = []
            if params and isinstance(params, dict) and 'inputs' in params:
                inputs = params.get('inputs', [])
                if not isinstance(inputs, list):
                    logger.warning(f"Inputs parameter is not a list, using empty list")
                    inputs = []
            
            # If no inputs provided, create a single task
            if not inputs:
                logger.info(f"No inputs provided, creating a single task for function {function_uid}")
                task_uid = str(uuid4())
                
                # Create task data
                task_data = {
                    'batch_index': 0,
                    'batch_size': 1,
                    'batch_total': 1
                }
                
                # Include parameters in task data if provided
                if params:
                    task_data['params'] = params
                
                try:
                    await session.execute(
                        text("""
                        INSERT INTO tasks (uid, function_uid, status, created_at, updated_at, data)
                        VALUES (:uid, :function_uid, 'pending', :now, :now, :data)
                        """),
                        {
                            "uid": task_uid,
                            "function_uid": function_uid,
                            "now": datetime.utcnow(),
                            "data": json.dumps(task_data)
                        }
                    )
                    await session.commit()
                except Exception as e:
                    logger.error(f"Error creating task: {e}")
                    return False
                
                logger.info(f"Created single task {task_uid} for function {function_uid}")
                return True
            
            # Calculate number of batches
            total_inputs = len(inputs)
            num_batches = (total_inputs + batch_size - 1) // batch_size  # Ceiling division
            
            logger.info(f"Starting function {function_uid} with {total_inputs} inputs, batch size {batch_size}, creating {num_batches} tasks")
            
            # Create tasks for this function
            task_uids = []
            for i in range(num_batches):
                task_uid = str(uuid4())
                task_uids.append(task_uid)
                
                # Calculate start and end indices for this batch
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, total_inputs)
                
                # Get the inputs for this batch
                batch_inputs = inputs[start_idx:end_idx]
                
                # Create task data with batch information
                task_data = {
                    'batch_index': i,
                    'batch_size': batch_size,
                    'batch_total': num_batches,
                    'input_start': start_idx,
                    'input_end': end_idx,
                    'inputs': batch_inputs
                }
                
                # Include other parameters in task data if provided
                if params:
                    # Copy params but exclude 'inputs' to avoid duplication
                    params_copy = params.copy()
                    if 'inputs' in params_copy:
                        del params_copy['inputs']
                    task_data['params'] = params_copy
                
                try:
                    await session.execute(
                        text("""
                        INSERT INTO tasks (uid, function_uid, status, created_at, updated_at, data)
                        VALUES (:uid, :function_uid, 'pending', :now, :now, :data)
                        """),
                        {
                            "uid": task_uid,
                            "function_uid": function_uid,
                            "now": datetime.utcnow(),
                            "data": json.dumps(task_data)
                        }
                    )
                except Exception as e:
                    logger.error(f"Error creating task {i+1}/{num_batches}: {e}")
                    # Continue with other tasks
            
            try:
                await session.commit()
            except Exception as e:
                logger.error(f"Error committing tasks: {e}")
                return False
            
            logger.info(f"Created {num_batches} tasks for function {function_uid}: {task_uids}")
            
            # Assign tasks to workers (this would be handled by a scheduler)
            # For now, just log that tasks were created
            logger.info(f"Function {function_uid} started successfully with {num_batches} tasks")
            
            return True
    except Exception as e:
        logger.error(f"Error starting function {function_uid}: {e}")
        # Print the line number where the error occurred
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error traceback: {tb}")
        return False

async def cancel_function(function_uid):
    """Cancel a function"""
    try:
        async for session in get_session():
            result = await session.execute(
                text("SELECT * FROM functions WHERE uid = :uid"),
                {"uid": function_uid}
            )
            function = result.fetchone()
            
            if not function:
                logger.error(f"Function {function_uid} not found")
                return False
            
            # Check if function can be cancelled - use lowercase values
            if function.status not in ["pending", "running"]:
                logger.error(f"Function {function_uid} cannot be cancelled in {function.status} state")
                return False
            
            # Update function status - use lowercase directly
            await session.execute(
                text("""
                UPDATE functions 
                SET status = 'cancelled', 
                    ended_at = :now,
                    updated_at = :now
                WHERE uid = :uid
                """),
                {
                    "uid": function_uid,
                    "now": datetime.utcnow()
                }
            )
            
            # Cancel any running tasks - use lowercase values
            await session.execute(
                text("""
                UPDATE tasks 
                SET status = 'cancelled', 
                    ended_at = :now,
                    updated_at = :now
                WHERE function_uid = :function_uid 
                AND status IN ('pending', 'running')
                """),
                {
                    "function_uid": function_uid,
                    "now": datetime.utcnow()
                }
            )
            
            await session.commit()
            
            return True
    except Exception as e:
        logger.error(f"Error cancelling function {function_uid}: {e}")
        return False

async def check_function_status(function_uid):
    """Check the status of a function"""
    try:
        async for session in get_session():
            result = await session.execute(
                text("SELECT * FROM functions WHERE uid = :uid"),
                {"uid": function_uid}
            )
            function = result.fetchone()
            
            if not function:
                logger.error(f"Function {function_uid} not found")
                return None
            
            return function.status.value if hasattr(function.status, 'value') else function.status
    except Exception as e:
        logger.error(f"Error checking function status {function_uid}: {e}")
        return None

async def delete_function(uid):
    """Delete a function from the database"""
    try:
        async for session in get_session():
            # Check if function exists
            result = await session.execute(
                text("SELECT * FROM functions WHERE uid = :uid"),
                {"uid": uid}
            )
            function = result.fetchone()
            
            if not function:
                logger.error(f"Function {uid} not found")
                return False
            
            # Check if function can be deleted (not running) - use lowercase
            if function.status == "running":
                logger.error(f"Cannot delete function {uid} because it is currently running")
                return False
            
            # Delete associated tasks first
            await session.execute(
                text("DELETE FROM tasks WHERE function_uid = :function_uid"),
                {"function_uid": uid}
            )
            
            # Delete the function
            await session.execute(
                text("DELETE FROM functions WHERE uid = :uid"),
                {"uid": uid}
            )
            await session.commit()
            
            logger.info(f"Function {uid} deleted successfully")
            return True
    except Exception as e:
        logger.error(f"Error deleting function {uid}: {e}")
        return False

async def update_script_path(uid, script_path):
    """Update a function's script path using direct SQL"""
    try:
        # Get database URL from environment
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        # Connect to the database directly
        conn = await asyncpg.connect(db_url)
        
        # Update the script path
        await conn.execute(
            """
            UPDATE functions 
            SET script_path = $1, updated_at = $2
            WHERE uid = $3
            """,
            script_path, datetime.utcnow(), uid
        )
        
        await conn.close()
        
        # Get the updated function
        return await get_function_by_uid(uid)
    except Exception as e:
        logger.error(f"Error updating script path with direct SQL: {e}")
        return None 