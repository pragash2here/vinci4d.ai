from db import Grid, GridStatus, Worker, WorkerStatus, get_session
from datetime import datetime
import asyncio
import logging
import uuid
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Database access functions
async def get_all_grids():
    """Get all grids from the database"""
    grids_list = []
    
    async for session in get_session():
        result = await session.execute(text("SELECT * FROM grids"))
        grids = result.fetchall()
        
        for grid in grids:
            grid_dict = {
                "uid": grid.uid,
                "name": grid.name,
                "length": grid.length,
                "width": grid.width,
                "status": grid.status if not hasattr(grid.status, 'value') else grid.status.value,
                "utilization": grid.utilization,
                "free_slots": grid.free_slots,
                "created_at": grid.created_at.isoformat() if grid.created_at else None,
                "updated_at": grid.updated_at.isoformat() if grid.updated_at else None
            }
            grids_list.append(grid_dict)
    
    return grids_list

async def get_grid_by_uid(uid):
    """Get a grid by its UID"""
    async for session in get_session():
        result = await session.execute(
            text("SELECT * FROM grids WHERE uid = :uid"),
            {"uid": uid}
        )
        grid = result.fetchone()
        
        if not grid:
            return None
        
        grid_dict = {
            "uid": grid.uid,
            "name": grid.name,
            "length": grid.length,
            "width": grid.width,
            "status": grid.status if not hasattr(grid.status, 'value') else grid.status.value,
            "utilization": grid.utilization,
            "free_slots": grid.free_slots,
            "created_at": grid.created_at.isoformat() if grid.created_at else None,
            "updated_at": grid.updated_at.isoformat() if grid.updated_at else None
        }
        
        return grid_dict

async def create_new_grid(data):
    """Create a new grid in the database"""
    try:
        # Create grid object with lowercase string values
        grid = Grid(
            uid=str(uuid.uuid4()),
            name=data["name"],
            length=data.get("length", 1),
            width=data.get("width", 1),
            status="active",  # Use lowercase string directly
            utilization=0.0,
            free_slots=data.get("length", 1) * data.get("width", 1),
            worker_count=0,
            busy_workers=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        async for session in get_session():
            session.add(grid)
            await session.commit()
            
            # Return grid data
            return {
                "uid": grid.uid,
                "name": grid.name,
                "length": grid.length,
                "width": grid.width,
                "status": "active",  # Use lowercase string directly
                "utilization": 0.0,
                "free_slots": grid.free_slots,
                "worker_count": 0,
                "busy_workers": 0,
                "created_at": grid.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Error creating grid: {e}")
        return None

async def initialize_grid(grid_uid):
    """Initialize a grid by creating worker nodes"""
    try:
        async for session in get_session():
            # Get the grid
            result = await session.execute(
                text("SELECT * FROM grids WHERE uid = :uid"),
                {"uid": grid_uid}
            )
            grid = result.fetchone()
            
            if not grid:
                logger.error(f"Grid {grid_uid} not found")
                return False
            
            # Check if grid can be initialized
            if grid.status != "creating":  # Use lowercase string
                logger.error(f"Grid {grid_uid} cannot be initialized from {grid.status} state")
                return False
            
            # Calculate total number of workers
            total_workers = grid.length * grid.width
            
            # Create worker nodes
            for i in range(total_workers):
                worker = Worker(
                    uid=str(uuid.uuid4()),
                    name=f"{grid.name}-worker-{i+1}",
                    grid_uid=grid_uid,
                    cpu_total=4.0,  # Default values
                    cpu_available=4.0,
                    memory_total=8192,  # 8GB in MB
                    memory_available=8192,
                    status="offline",  # Use lowercase string
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    spec={"node_type": "standard"}
                )
                session.add(worker)
            
            # Update grid status
            grid.status = "active"  # Use lowercase string
            grid.updated_at = datetime.utcnow()
            
            await session.commit()
            logger.info(f"Grid {grid_uid} initialized successfully with {total_workers} workers")
            return True
            
    except Exception as e:
        logger.error(f"Error initializing grid {grid_uid}: {e}")
        
        # Update grid status to ERROR
        try:
            async for session in get_session():
                result = await session.execute(
                    text("SELECT * FROM grids WHERE uid = :uid"),
                    {"uid": grid_uid}
                )
                grid = result.fetchone()
                if grid:
                    grid.status = "error"  # Use lowercase string
                    grid.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception as inner_e:
            logger.error(f"Error updating grid status: {inner_e}")
            
        return False

async def activate_grid(grid_uid):
    """Activate a grid by changing its status and activating workers"""
    try:
        async for session in get_session():
            # Get the grid
            result = await session.execute(
                text("SELECT * FROM grids WHERE uid = :uid"),
                {"uid": grid_uid}
            )
            grid = result.fetchone()
            
            if not grid:
                logger.error(f"Grid {grid_uid} not found")
                return False
            
            # Check if grid can be activated
            if grid.status not in [GridStatus.PAUSED, GridStatus.ERROR]:
                logger.error(f"Grid {grid_uid} cannot be activated from {grid.status} state")
                return False
            
            # Update grid status
            grid.status = GridStatus.ACTIVE
            grid.updated_at = datetime.utcnow()
            
            # Activate workers
            await session.execute(
                text("""
                UPDATE workers 
                SET status = :online_status, updated_at = :now
                WHERE grid_uid = :grid_uid AND status = :offline_status
                """),
                {
                    "online_status": WorkerStatus.ONLINE,
                    "now": datetime.utcnow(),
                    "grid_uid": grid_uid,
                    "offline_status": WorkerStatus.OFFLINE
                }
            )
            
            await session.commit()
            logger.info(f"Grid {grid_uid} activated successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error activating grid {grid_uid}: {e}")
        return False

async def pause_grid(grid_uid):
    """Pause a grid by changing its status and pausing workers"""
    try:
        async for session in get_session():
            # Get the grid
            result = await session.execute(
                text("SELECT * FROM grids WHERE uid = :uid"),
                {"uid": grid_uid}
            )
            grid = result.fetchone()
            
            if not grid:
                logger.error(f"Grid {grid_uid} not found")
                return False
            
            # Check if grid can be paused
            if grid.status != GridStatus.ACTIVE:
                logger.error(f"Grid {grid_uid} cannot be paused from {grid.status} state")
                return False
            
            # Update grid status
            grid.status = GridStatus.PAUSED
            grid.updated_at = datetime.utcnow()
            
            # Pause workers
            await session.execute(
                text("""
                UPDATE workers 
                SET status = :offline_status, updated_at = :now
                WHERE grid_uid = :grid_uid AND status IN (:online_status, :busy_status)
                """),
                {
                    "offline_status": WorkerStatus.OFFLINE,
                    "now": datetime.utcnow(),
                    "grid_uid": grid_uid,
                    "online_status": WorkerStatus.ONLINE,
                    "busy_status": WorkerStatus.BUSY
                }
            )
            
            await session.commit()
            logger.info(f"Grid {grid_uid} paused successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error pausing grid {grid_uid}: {e}")
        return False

async def terminate_grid(grid_uid):
    """Terminate a grid by changing its status and terminating workers"""
    try:
        async for session in get_session():
            # Get the grid
            result = await session.execute(
                text("SELECT * FROM grids WHERE uid = :uid"),
                {"uid": grid_uid}
            )
            grid = result.fetchone()
            
            if not grid:
                logger.error(f"Grid {grid_uid} not found")
                return False
            
            # Check if grid can be terminated
            if grid.status == GridStatus.TERMINATED:
                logger.error(f"Grid {grid_uid} is already terminated")
                return False
            
            # Update grid status
            grid.status = GridStatus.TERMINATED
            grid.updated_at = datetime.utcnow()
            
            # Terminate workers (delete them)
            await session.execute(
                text("DELETE FROM workers WHERE grid_uid = :grid_uid"),
                {"grid_uid": grid_uid}
            )
            
            await session.commit()
            logger.info(f"Grid {grid_uid} terminated successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error terminating grid {grid_uid}: {e}")
        return False

async def update_grid_utilization(grid_uid):
    """Update grid utilization statistics"""
    try:
        async for session in get_session():
            # Get worker counts
            result = await session.execute(
                text("""
                SELECT 
                    COUNT(*) as total_workers,
                    SUM(CASE WHEN status = :busy_status THEN 1 ELSE 0 END) as busy_workers
                FROM workers
                WHERE grid_uid = :grid_uid
                """),
                {"busy_status": WorkerStatus.BUSY.value, "grid_uid": grid_uid}  # Use .value to get string
            )
            worker_stats = result.fetchone()
            
            # Get grid
            result = await session.execute(
                text("SELECT * FROM grids WHERE uid = :uid"),
                {"uid": grid_uid}
            )
            grid = result.fetchone()
            
            if not grid:
                logger.error(f"Grid {grid_uid} not found")
                return False
            
            # Update grid utilization
            total_workers = worker_stats.total_workers or 0
            busy_workers = worker_stats.busy_workers or 0
            
            # Calculate utilization percentage
            utilization = 0
            if total_workers > 0:
                utilization = (busy_workers / total_workers) * 100
            
            # Update grid
            await session.execute(
                text("""
                UPDATE grids 
                SET worker_count = :worker_count, 
                    busy_workers = :busy_workers,
                    utilization = :utilization,
                    updated_at = :updated_at
                WHERE uid = :uid
                """),
                {
                    "worker_count": total_workers,
                    "busy_workers": busy_workers,
                    "utilization": utilization,
                    "updated_at": datetime.utcnow(),
                    "uid": grid_uid
                }
            )
            await session.commit()
            
            logger.info(f"Grid {grid_uid} utilization updated: {utilization:.1f}% ({busy_workers}/{total_workers} workers busy)")
            return True
    except Exception as e:
        logger.error(f"Error updating grid utilization {grid_uid}: {e}")
        return False
