from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum
import enum
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import asyncpg

# Load environment variables from config.env
env_path = Path(__file__).parent.parent.parent / 'config.env'
load_dotenv(env_path)

# Get database connection info from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Function to create database if it doesn't exist
async def ensure_database_exists():
    print("Checking if database exists...")
    
    # Extract connection parameters
    db_url = DATABASE_URL
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    # Extract database name
    db_name = db_url.split('/')[-1]
    
    # Create connection string to postgres database (for admin operations)
    admin_url = db_url.rsplit('/', 1)[0] + '/postgres'
    
    try:
        # Connect to default postgres database
        conn = await asyncpg.connect(admin_url)
        
        # Check if our database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        
        if not exists:
            print(f"Creating database {db_name}...")
            # Create the database
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database {db_name} created successfully!")
        else:
            print(f"Database {db_name} already exists.")
            
        await conn.close()
        return True
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        return False

# Convert the URL to use asyncpg driver
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')

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

class FunctionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

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
    
class Function(Base):
    __tablename__ = 'functions'

    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    grid_uid = Column(String, ForeignKey('grids.uid'))
    script_path = Column(String, nullable=False)
    artifactory_url = Column(String)
    resource_requirements = Column(JSON, nullable=False)  # CPU, Memory, GPU requirements
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    status = Column(Enum(FunctionStatus), default=FunctionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    logs_url = Column(String)  # URL to task logs in logstore

class Task(Base):
    __tablename__ = 'tasks'

    uid = Column(String, primary_key=True)
    function_uid = Column(String, ForeignKey('functions.uid'))
    worker_uid = Column(String, ForeignKey('workers.uid'))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    
# Database initialization function
async def init_db():
    print("Starting database initialization...")
    try:
        # First ensure the database exists
        await ensure_database_exists()
        
        # Then create tables
        async with engine.begin() as conn:
            print("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created successfully!")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

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
