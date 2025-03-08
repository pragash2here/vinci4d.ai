#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

# Load environment variables from config.env
env_path = Path(__file__).parent.parent.parent / 'config.env'
load_dotenv(env_path)

# Get database connection info from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Extract connection parameters
db_url = DATABASE_URL
if db_url.startswith('postgresql+asyncpg://'):
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

async def add_docker_image_column():
    """Add docker_image column to functions table if it doesn't exist"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        
        # Check if the column already exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'functions' 
                AND column_name = 'docker_image'
            )
        """)
        
        if not column_exists:
            print("Adding docker_image column to functions table...")
            # Add the column with a default value
            await conn.execute("""
                ALTER TABLE functions 
                ADD COLUMN docker_image VARCHAR DEFAULT 'default' NOT NULL
            """)
            print("Column added successfully!")
        else:
            print("docker_image column already exists in functions table.")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error adding docker_image column: {e}")
        return False

async def add_worker_name_unique_constraint():
    """Add unique constraint to worker names"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        
        # Check if the constraint already exists
        constraint_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.table_constraints 
                WHERE table_name = 'workers' 
                AND constraint_name = 'workers_name_key'
            )
        """)
        
        if not constraint_exists:
            print("Adding unique constraint to worker names...")
            # Add the unique constraint
            await conn.execute("""
                ALTER TABLE workers 
                ADD CONSTRAINT workers_name_key UNIQUE (name)
            """)
            print("Unique constraint added successfully!")
        else:
            print("Unique constraint on worker names already exists.")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error adding unique constraint to worker names: {e}")
        return False

async def main():
    """Run all migrations"""
    print("Starting database migrations...")
    await add_docker_image_column()
    await add_worker_name_unique_constraint()
    print("Database migrations completed!")

if __name__ == "__main__":
    asyncio.run(main()) 