from db import Function, FunctionStatus, Task, TaskStatus, Worker, WorkerStatus, get_session
from datetime import datetime
import asyncio
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Database access functions
async def get_all_functions():
    """Get all functions from the database"""
    functions_list = []
    
    async for session in get_session():
        result = await session.execute(text("SELECT * FROM functions"))
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
    from uuid import uuid4
    
    # Create function object
    function = Function(
        uid=str(uuid4()),
        name=data["name"],
        grid_uid=data["grid_uid"],
        script_path=data["script_path"],
        artifactory_url=data.get("artifactory_url"),
        resource_requirements=data["resource_requirements"],
        docker_image=data.get("docker_image", "default"),
        status=FunctionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    async for session in get_session():
        session.add(function)
        await session.commit()
        
        return {
            "uid": function.uid,
            "name": function.name,
            "docker_image": function.docker_image,
            "status": function.status.value,
            "created_at": function.created_at.isoformat()
        }

async def update_function(uid, data):
    """Update a function in the database"""
    async for session in get_session():
        result = await session.execute(
            text("SELECT * FROM functions WHERE uid = :uid"),
            {"uid": uid}
        )
        function = result.fetchone()
        
        if not function:
            return None
        
        # Update fields if provided
        if "name" in data:
            function.name = data["name"]
        if "script_path" in data:
            function.script_path = data["script_path"]
        if "artifactory_url" in data:
            function.artifactory_url = data["artifactory_url"]
        if "resource_requirements" in data:
            function.resource_requirements = data["resource_requirements"]
        if "docker_image" in data:
            function.docker_image = data["docker_image"]
        
        function.updated_at = datetime.utcnow()
        await session.commit()
        
        return {
            "uid": function.uid,
            "name": function.name,
            "docker_image": function.docker_image,
            "status": function.status.value,
            "updated_at": function.updated_at.isoformat()
        }

# Existing functions with improved error handling
async def start_function(function_uid):
    """Start a function"""
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
            
            if function.status != FunctionStatus.PENDING:
                logger.error(f"Function {function_uid} is not in PENDING state")
                return False
            
            # Update function status
            function.status = FunctionStatus.RUNNING
            function.started_at = datetime.utcnow()
            function.updated_at = datetime.utcnow()
            await session.commit()
            
            # TODO: Implement actual function execution logic
            
            return True
    except Exception as e:
        logger.error(f"Error starting function {function_uid}: {e}")
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
            
            if function.status not in [FunctionStatus.PENDING, FunctionStatus.RUNNING]:
                logger.error(f"Function {function_uid} cannot be cancelled in {function.status} state")
                return False
            
            # Update function status
            function.status = FunctionStatus.CANCELLED
            function.ended_at = datetime.utcnow()
            function.updated_at = datetime.utcnow()
            await session.commit()
            
            # Cancel any running tasks
            result = await session.execute(
                text("SELECT * FROM tasks WHERE function_uid = :function_uid AND status IN ('PENDING', 'RUNNING')"),
                {"function_uid": function_uid}
            )
            tasks = result.fetchall()
            
            for task in tasks:
                task.status = TaskStatus.CANCELLED
                task.ended_at = datetime.utcnow()
                task.updated_at = datetime.utcnow()
            
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