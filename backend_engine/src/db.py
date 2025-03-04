from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum
import enum
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create async engine
DATABASE_URL = os.getenv('DATABASE_URL').replace('sqlite:///', 'postgresql+asyncpg:///')
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create base class for declarative models
Base = declarative_base()

class GridStatus(enum.Enum):
    CREATING = "creating"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkerStatus(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"

class Grid(Base):
    __tablename__ = 'grids'

    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    length = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    status = Column(Enum(GridStatus), default=GridStatus.CREATING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    utilization = Column(Float, default=0.0)  # Percentage of grid being utilized
    free_slots = Column(Integer)  # Number of free slots available
    metadata = Column(JSON, default={})  # Additional grid properties

class Task(Base):
    __tablename__ = 'tasks'

    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    grid_uid = Column(String, ForeignKey('grids.uid'))
    script_path = Column(String, nullable=False)
    artifactory_url = Column(String)
    resource_requirements = Column(JSON, nullable=False)  # CPU, Memory, GPU requirements
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    logs_url = Column(String)  # URL to task logs in logstore
    metadata = Column(JSON, default={})  # Additional task properties

class Worker(Base):
    __tablename__ = 'workers'

    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    grid_uid = Column(String, ForeignKey('grids.uid'))
    cpu_total = Column(Float, nullable=False)  # Total CPU cores
    cpu_available = Column(Float)  # Available CPU cores
    memory_total = Column(Integer, nullable=False)  # Total memory in MB
    memory_available = Column(Integer)  # Available memory in MB
    gpu_id = Column(String)  # GPU identifier if available
    gpu_memory = Column(Integer)  # GPU memory in MB if available
    status = Column(Enum(WorkerStatus), default=WorkerStatus.OFFLINE)
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    spec = Column(JSON)  # Additional worker specifications
    metadata = Column(JSON, default={})  # Additional worker properties

# Database initialization function
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Database session context manager
async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
