from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
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

# Define enum classes with lowercase values to match PostgreSQL enum types
class GridStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CREATING = "creating"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"

class FunctionStatus(enum.Enum):
    READY = "ready"
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
    ERROR = "error"

# Define models with explicit enum type names
class Grid(Base):
    __tablename__ = 'grids'

    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    length = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    status = Column(Enum(GridStatus, name="gridstatus"), default=GridStatus.CREATING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    utilization = Column(Float, default=0.0)  # Percentage of grid being utilized
    free_slots = Column(Integer)  # Number of free slots available
    worker_count = Column(Integer, default=0)  # Number of workers in the grid
    busy_workers = Column(Integer, default=0)  # Number of busy workers in the grid
    
class Function(Base):
    __tablename__ = "functions"
    
    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    grid_uid = Column(String, ForeignKey("grids.uid"), nullable=False)
    script_path = Column(String, nullable=False)
    artifactory_url = Column(String)
    resource_requirements = Column(JSON, nullable=False)
    docker_image = Column(String, default="default")
    status = Column(Enum(FunctionStatus, name="functionstatus"), default=FunctionStatus.PENDING)
    batch_size = Column(Integer, default=1)  # Default to 1 task per function
    function_params = Column(JSON, default={})  # Store default parameters
    created_at = Column(DateTime, default=func.utcnow())
    updated_at = Column(DateTime, default=func.utcnow(), onupdate=func.utcnow())
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

class Task(Base):
    __tablename__ = 'tasks'

    uid = Column(String, primary_key=True)
    function_uid = Column(String, ForeignKey('functions.uid'))
    worker_uid = Column(String, ForeignKey('workers.uid'))
    status = Column(Enum(TaskStatus, name="taskstatus"), default=TaskStatus.PENDING)
    data = Column(JSON, default={})  # Store task parameters and other data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    result = Column(JSON)  # Store task results

class Worker(Base):
    __tablename__ = 'workers'

    uid = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # Make name unique
    grid_uid = Column(String, ForeignKey('grids.uid'), nullable=False)
    cpu_total = Column(Float, nullable=False)
    cpu_available = Column(Float, nullable=False)
    memory_total = Column(Integer, nullable=False)  # Memory in MB
    memory_available = Column(Integer, nullable=False)  # Memory in MB
    gpu_id = Column(String)
    gpu_memory = Column(Integer)  # GPU memory in MB
    status = Column(Enum(WorkerStatus, name="workerstatus"), default=WorkerStatus.OFFLINE)
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    spec = Column(JSON, default={})  # Additional specifications (OS, arch, etc.)
    
# Database initialization function
async def init_db():
    print("Starting database initialization...")
    try:
        # First ensure the database exists
        await ensure_database_exists()
        
        # Ensure enum types exist
        await ensure_enum_types()
        
        # Then create tables
        async with engine.begin() as conn:
            print("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created successfully!")
        
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

async def ensure_enum_types():
    """Ensure all enum types exist in the database"""
    try:
        # Extract connection parameters
        db_url = DATABASE_URL
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Checking enum types...")
        
        # Define all enum types and their values
        enum_types = {
            "gridstatus": ["active", "inactive", "creating", "paused", "terminated", "error"],
            "functionstatus": ["ready", "pending", "running", "completed", "failed", "cancelled"],
            "taskstatus": ["pending", "running", "completed", "failed", "cancelled"],
            "workerstatus": ["online", "offline", "busy", "error"]
        }
        
        # Check and create each enum type
        for enum_name, values in enum_types.items():
            try:
                # Check if the enum type exists
                type_exists = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
                    )
                """)
                
                if not type_exists:
                    print(f"Creating {enum_name} enum...")
                    values_str = ", ".join(f"'{val}'" for val in values)
                    await conn.execute(f"""
                        CREATE TYPE {enum_name} AS ENUM ({values_str})
                    """)
                    print(f"Created {enum_name} enum")
            except Exception as e:
                print(f"Error with {enum_name} enum: {e}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error ensuring enum types: {e}")
        return False

# Database session context manager
async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Session error: {e}")
            raise
        finally:
            await session.close()
