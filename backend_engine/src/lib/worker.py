import logging
from sqlalchemy import text
from datetime import datetime
from db import Worker, WorkerStatus, get_session
import asyncio
from uuid import uuid4
import os

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
    """Set a worker's status to online"""
    try:
        logger.info(f"Setting worker {uid} online")
        
        # Use direct SQL update instead of ORM to avoid immutability issues
        async for session in get_session():
            # Update worker status using SQL
            await session.execute(
                text("""
                UPDATE workers 
                SET status = 'online', 
                    last_heartbeat = :now,
                    updated_at = :now
                WHERE uid = :uid
                """),
                {
                    "uid": uid,
                    "now": datetime.utcnow()
                }
            )
            
            try:
                await session.commit()
                logger.info(f"Worker {uid} set to online successfully")
                return True
            except Exception as commit_error:
                logger.error(f"Error committing worker status update: {commit_error}")
                await session.rollback()
                raise
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

async def create_worker(data):
    """Create a new worker in the database"""
    try:
        # Check if a worker with this name already exists
        async for session in get_session():
            result = await session.execute(
                text("SELECT COUNT(*) FROM workers WHERE name = :name"),
                {"name": data["name"]}
            )
            count = result.scalar()
            
            if count > 0:
                logger.error(f"Worker with name {data['name']} already exists")
                return None
        
        # Create worker object
        worker = Worker(
            uid=str(uuid4()),
            name=data["name"],
            grid_uid=data["grid_uid"],
            cpu_total=data["cpu_total"],
            cpu_available=data["cpu_total"],  # Initially all CPU is available
            memory_total=data["memory_total"],
            memory_available=data["memory_total"],  # Initially all memory is available
            gpu_id=data.get("gpu_id"),
            gpu_memory=data.get("gpu_memory"),
            status="offline",
            last_heartbeat=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            spec={
                "docker_image": data.get("docker_image", "python:3.11-slim"),
                "os": data.get("os", "linux"),
                "arch": data.get("arch", "x86_64")
            }
        )
        
        async for session in get_session():
            session.add(worker)
            await session.commit()
            
            # Update grid utilization
            from lib.grid import update_grid_utilization
            asyncio.create_task(update_grid_utilization(data["grid_uid"]))
            
            # Create worker response
            worker_response = {
                "uid": worker.uid,
                "name": worker.name,
                "grid_uid": worker.grid_uid,
                "status": worker.status,
                "cpu_total": worker.cpu_total,
                "memory_total": worker.memory_total,
                "docker_image": worker.spec.get("docker_image", "python:3.11-slim"),
                "created_at": worker.created_at.isoformat()
            }
            
            # Deploy worker to Kubernetes if auto_deploy is enabled
            if data.get("auto_deploy", True):
                try:
                    from lib.k8ssdk import K8sDeployer
                    namespace = os.environ.get("K8S_NAMESPACE", "default")
                    deployer = K8sDeployer(namespace=namespace)
                    
                    # Convert SQLAlchemy model to dict for deployer
                    worker_dict = {
                        "uid": worker.uid,
                        "name": worker.name,
                        "grid_uid": worker.grid_uid,
                        "cpu_total": worker.cpu_total,
                        "memory_total": worker.memory_total,
                        "gpu_id": worker.gpu_id,
                        "gpu_memory": worker.gpu_memory,
                        "spec": worker.spec
                    }
                    
                    # Deploy worker asynchronously
                    asyncio.create_task(deploy_worker_async(deployer, worker_dict))
                except Exception as e:
                    logger.error(f"Error setting up worker deployment: {e}")
            
            return worker_response
    except Exception as e:
        logger.error(f"Error creating worker: {e}")
        return None

async def deploy_worker_async(deployer, worker):
    """Deploy a worker asynchronously"""
    try:
        # Run the deployment in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, deployer.deploy_worker, worker)
        
        if result:
            logger.info(f"Worker {worker['uid']} deployed successfully")
        else:
            logger.error(f"Failed to deploy worker {worker['uid']}")
    except Exception as e:
        logger.error(f"Error deploying worker {worker['uid']}: {e}")

async def create_workers_batch(data):
    """Create multiple workers at once"""
    results = []
    
    # Create the specified number of workers
    count = data.get("count", 1)
    
    # Use name_prefix if provided, otherwise use name as prefix
    base_name = data.get("name_prefix", data.get("name", "worker"))
    
    for i in range(count):
        worker_data = data.copy()
        worker_data["name"] = f"{base_name}-{i+1}"
        
        # Create the worker
        worker = await create_worker(worker_data)
        results.append(worker)
    
    return results

async def associate_worker_with_grid(worker_uid, grid_uid):
    """Associate a worker with a grid"""
    async for session in get_session():
        # Check if worker exists
        result = await session.execute(
            text("SELECT * FROM workers WHERE uid = :uid"),
            {"uid": worker_uid}
        )
        worker = result.fetchone()
        
        if not worker:
            logger.error(f"Worker {worker_uid} not found")
            return False
        
        # Check if grid exists
        result = await session.execute(
            text("SELECT * FROM grids WHERE uid = :uid"),
            {"uid": grid_uid}
        )
        grid = result.fetchone()
        
        if not grid:
            logger.error(f"Grid {grid_uid} not found")
            return False
        
        # Update worker's grid_uid
        worker.grid_uid = grid_uid
        worker.updated_at = datetime.utcnow()
        await session.commit()
        
        # Update grid utilization
        from lib.grid import update_grid_utilization
        asyncio.create_task(update_grid_utilization(grid_uid))
        
        logger.info(f"Worker {worker_uid} associated with grid {grid_uid}")
        return True
    
    return False

async def delete_worker(uid):
    """Delete a worker from the database"""
    try:
        async for session in get_session():
            # Check if worker exists
            result = await session.execute(
                text("SELECT * FROM workers WHERE uid = :uid"),
                {"uid": uid}
            )
            worker = result.fetchone()
            
            if not worker:
                logger.error(f"Worker {uid} not found")
                return False
            
            # Store grid_uid and name for later use
            grid_uid = worker.grid_uid
            worker_name = worker.name
            
            # Delete the worker
            await session.execute(
                text("DELETE FROM workers WHERE uid = :uid"),
                {"uid": uid}
            )
            await session.commit()
            
            logger.info(f"Worker {uid} deleted successfully from database")
            
            # Update grid utilization if worker was part of a grid
            if grid_uid:
                from lib.grid import update_grid_utilization
                asyncio.create_task(update_grid_utilization(grid_uid))
            
            # Delete worker from Kubernetes
            try:
                from lib.k8ssdk import K8sDeployer
                namespace = os.environ.get("K8S_NAMESPACE", "default")
                deployer = K8sDeployer(namespace=namespace)
                
                # Delete worker asynchronously
                asyncio.create_task(delete_worker_async(deployer, uid, worker_name))
            except Exception as e:
                logger.error(f"Error setting up worker deletion from Kubernetes: {e}")
            
            return True
    except Exception as e:
        logger.error(f"Error deleting worker {uid}: {e}")
        return False

async def delete_worker_async(deployer, worker_uid, worker_name=None):
    """Delete a worker from Kubernetes asynchronously"""
    try:
        # Run the deletion in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Pass both UID and name to the delete function
        if worker_name:
            result = await loop.run_in_executor(
                None, 
                lambda: deployer.delete_worker(worker_uid, worker_name)
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: deployer.delete_worker(worker_uid)
            )
        
        if result:
            logger.info(f"Worker {worker_uid} deleted successfully from Kubernetes")
        else:
            logger.error(f"Failed to delete worker {worker_uid} from Kubernetes")
    except Exception as e:
        logger.error(f"Error deleting worker {worker_uid} from Kubernetes: {e}")

async def update_worker_heartbeat(uid):
    """Update a worker's heartbeat timestamp"""
    try:
        logger.info(f"Updating heartbeat for worker {uid}")
        
        # Use direct SQL update
        async for session in get_session():
            await session.execute(
                text("""
                UPDATE workers 
                SET last_heartbeat = :now,
                    updated_at = :now
                WHERE uid = :uid
                """),
                {
                    "uid": uid,
                    "now": datetime.utcnow()
                }
            )
            
            try:
                await session.commit()
                return True
            except Exception as commit_error:
                logger.error(f"Error committing worker heartbeat update: {commit_error}")
                await session.rollback()
                raise
    except Exception as e:
        logger.error(f"Error updating heartbeat for worker {uid}: {e}")
        return False
