import logging
from sqlalchemy import text
from datetime import datetime
from db import Task, TaskStatus, get_session

logger = logging.getLogger(__name__)

async def get_all_tasks(filters=None):
    """Get all tasks from the database with optional filters"""
    tasks_list = []
    
    async for session in get_session():
        # Build query based on filters
        query = "SELECT * FROM tasks WHERE 1=1"
        params = {}
        
        if filters:
            if "function_uid" in filters:
                query += " AND function_uid = :function_uid"
                params["function_uid"] = filters["function_uid"]
                
            if "worker_uid" in filters:
                query += " AND worker_uid = :worker_uid"
                params["worker_uid"] = filters["worker_uid"]
                
            if "status" in filters:
                query += " AND status = :status"
                params["status"] = filters["status"]
        
        result = await session.execute(text(query), params)
        tasks = result.fetchall()
        
        for task in tasks:
            task_dict = {
                "uid": task.uid,
                "function_uid": task.function_uid,
                "worker_uid": task.worker_uid,
                "status": task.status if not hasattr(task.status, 'value') else task.status.value,
                "result": task.result,
                "error": task.error,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "ended_at": task.ended_at.isoformat() if task.ended_at else None
            }
            tasks_list.append(task_dict)
    
    return tasks_list

async def get_task_by_uid(uid):
    """Get a task by its UID"""
    async for session in get_session():
        result = await session.execute(
            text("SELECT * FROM tasks WHERE uid = :uid"),
            {"uid": uid}
        )
        task = result.fetchone()
        
        if not task:
            return None
        
        task_dict = {
            "uid": task.uid,
            "function_uid": task.function_uid,
            "worker_uid": task.worker_uid,
            "status": task.status if not hasattr(task.status, 'value') else task.status.value,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "ended_at": task.ended_at.isoformat() if task.ended_at else None
        }
        
        return task_dict

async def create_new_task(data):
    """Create a new task in the database"""
    from uuid import uuid4
    
    # Create task object
    task = Task(
        uid=str(uuid4()),
        function_uid=data["function_uid"],
        worker_uid=data["worker_uid"],
        status=TaskStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    async for session in get_session():
        session.add(task)
        await session.commit()
        
        return {
            "uid": task.uid,
            "function_uid": task.function_uid,
            "worker_uid": task.worker_uid,
            "status": task.status.value,
            "created_at": task.created_at.isoformat()
        }
