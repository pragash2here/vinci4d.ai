import logging
from sqlalchemy import text
from datetime import datetime
from db import Worker, WorkerStatus, get_session

logger = logging.getLogger(__name__)

async def get_all_workers(filters=None):
    """Get all workers from the database with optional filters"""
    workers_list = []
    
    async for session in get_session():
        # Build query based on filters
        query = "SELECT * FROM workers WHERE 1=1"
        params = {}
        
        if filters:
            if "grid_uid" in filters:
                query += " AND grid_uid = :grid_uid"
                params["grid_uid"] = filters["grid_uid"]
                
            if "status" in filters:
                query += " AND status = :status"
                params["status"] = filters["status"]
        
        result = await session.execute(text(query), params)
        workers = result.fetchall()
        
        for worker in workers:
            worker_dict = {
                "uid": worker.uid,
                "name": worker.name,
                "grid_uid": worker.grid_uid,
                "status": worker.status if not hasattr(worker.status, 'value') else worker.status.value,
                "cpu_total": worker.cpu_total,
                "cpu_available": worker.cpu_available,
                "memory_total": worker.memory_total,
                "memory_available": worker.memory_available,
                "gpu_id": worker.gpu_id,
                "gpu_memory": worker.gpu_memory,
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                "created_at": worker.created_at.isoformat() if worker.created_at else None,
                "updated_at": worker.updated_at.isoformat() if worker.updated_at else None,
                "spec": worker.spec
            }
            workers_list.append(worker_dict)
    
    return workers_list

async def get_worker_by_uid(uid):
    """Get a worker by its UID"""
    async for session in get_session():
        result = await session.execute(
            text("SELECT * FROM workers WHERE uid = :uid"),
            {"uid": uid}
        )
        worker = result.fetchone()
        
        if not worker:
            return None
        
        worker_dict = {
            "uid": worker.uid,
            "name": worker.name,
            "grid_uid": worker.grid_uid,
            "status": worker.status if not hasattr(worker.status, 'value') else worker.status.value,
            "cpu_total": worker.cpu_total,
            "cpu_available": worker.cpu_available,
            "memory_total": worker.memory_total,
            "memory_available": worker.memory_available,
            "gpu_id": worker.gpu_id,
            "gpu_memory": worker.gpu_memory,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "created_at": worker.created_at.isoformat() if worker.created_at else None,
            "updated_at": worker.updated_at.isoformat() if worker.updated_at else None,
            "spec": worker.spec
        }
        
        return worker_dict

async def set_worker_online(uid):
    """Set a worker status to online"""
    try:
        async for session in get_session():
            result = await session.execute(
                text("SELECT * FROM workers WHERE uid = :uid"),
                {"uid": uid}
            )
            worker = result.fetchone()
            
            if not worker:
                logger.error(f"Worker {uid} not found")
                return False
            
            worker.status = WorkerStatus.ONLINE
            worker.updated_at = datetime.utcnow()
            worker.last_heartbeat = datetime.utcnow()
            await session.commit()
            
            logger.info(f"Worker {uid} set to online")
            return True
    except Exception as e:
        logger.error(f"Error setting worker {uid} online: {e}")
        return False

async def set_worker_offline(uid):
    """Set a worker status to offline"""
    try:
        async for session in get_session():
            result = await session.execute(
                text("SELECT * FROM workers WHERE uid = :uid"),
                {"uid": uid}
            )
            worker = result.fetchone()
            
            if not worker:
                logger.error(f"Worker {uid} not found")
                return False
            
            worker.status = WorkerStatus.OFFLINE
            worker.updated_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"Worker {uid} set to offline")
            return True
    except Exception as e:
        logger.error(f"Error setting worker {uid} offline: {e}")
        return False
