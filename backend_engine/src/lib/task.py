import logging
from sqlalchemy import text
from datetime import datetime
from db import Task, TaskStatus, get_session
import json

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

async def assign_task_to_worker(worker_uid):
    """Assign a task to a worker"""
    try:
        async for session in get_session():
            # First, find a pending task
            result = await session.execute(
                text("SELECT * FROM tasks WHERE status = 'pending' LIMIT 1")
            )
            task_row = result.fetchone()
            
            if not task_row:
                # No pending tasks found
                return {"error": "No pending tasks available"}
            
            # Get task data before updating
            task_uid = task_row.uid
            function_uid = task_row.function_uid
            task_data = task_row.data if hasattr(task_row, 'data') else {}
            
            # Extract inputs from task data
            inputs = []
            if task_data and isinstance(task_data, dict) and 'input' in task_data:
                inputs = task_data.get('input', [])
            
            # Update the task using SQL instead of trying to modify the Row object
            await session.execute(
                text("""
                UPDATE tasks 
                SET worker_uid = :worker_uid, 
                    status = 'running',
                    started_at = :now,
                    updated_at = :now
                WHERE uid = :task_uid
                """),
                {
                    "worker_uid": worker_uid,
                    "now": datetime.utcnow(),
                    "task_uid": task_uid
                }
            )
            
            await session.commit()
            
            # Return the function_uid and inputs for the worker
            return {
                "task_uid": task_uid,
                "function_uid": function_uid,
                "inputs": inputs
            }
    except Exception as e:
        logger.error(f"Error assigning task to worker {worker_uid}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

async def update_task_status(task_uid, status, result=None, error=None, worker_uid=None):
    """Update a task's status and result"""
    try:
        async for session in get_session():
            # Build update query
            update_clauses = ["status = :status", "updated_at = :updated_at"]
            params = {
                "task_uid": task_uid,
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if status in ["completed", "failed"]:
                update_clauses.append("ended_at = :ended_at")
                params["ended_at"] = datetime.utcnow()
            
            if result is not None:
                update_clauses.append("result = :result")
                params["result"] = json.dumps(result)
            
            if error is not None:
                update_clauses.append("error = :error")
                params["error"] = error
            
            if worker_uid is not None:
                update_clauses.append("worker_uid = :worker_uid")
                params["worker_uid"] = worker_uid
            
            # Execute update
            query = f"""
                UPDATE tasks 
                SET {', '.join(update_clauses)}
                WHERE uid = :task_uid
            """
            
            await session.execute(text(query), params)
            await session.commit()
            
            # If task is completed or failed, update function status if all tasks are done
            if status in ["completed", "failed"]:
                # Get the function_uid for this task
                result = await session.execute(
                    text("SELECT function_uid FROM tasks WHERE uid = :uid"),
                    {"uid": task_uid}
                )
                task = result.fetchone()
                
                if task:
                    function_uid = task.function_uid
                    
                    # Check if all tasks for this function are done
                    result = await session.execute(
                        text("""
                        SELECT COUNT(*) as total_tasks,
                               SUM(CASE WHEN status IN ('completed', 'failed', 'cancelled') THEN 1 ELSE 0 END) as done_tasks
                        FROM tasks
                        WHERE function_uid = :function_uid
                        """),
                        {"function_uid": function_uid}
                    )
                    task_counts = result.fetchone()
                    
                    if task_counts and task_counts.total_tasks == task_counts.done_tasks:
                        # All tasks are done, update function status
                        await session.execute(
                            text("""
                            UPDATE functions
                            SET status = 'completed', ended_at = :now, updated_at = :now
                            WHERE uid = :function_uid
                            """),
                            {
                                "function_uid": function_uid,
                                "now": datetime.utcnow()
                            }
                        )
                        await session.commit()
            
            return True
    except Exception as e:
        logger.error(f"Error updating task status {task_uid}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
