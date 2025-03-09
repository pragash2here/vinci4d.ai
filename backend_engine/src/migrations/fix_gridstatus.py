#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
import traceback

# Load environment variables from config.env
env_path = Path(__file__).parent.parent.parent / 'config.env'
load_dotenv(env_path)

# Extract connection parameters
db_url = 'postgresql+asyncpg://postgres:postgres@localhost:5432/engine_db'
if db_url.startswith('postgresql+asyncpg://'):
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

async def fix_gridstatus():
    """Fix the gridstatus enum in the database"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # First, convert the status column to text
        print("Converting grid.status to text...")
        await conn.execute("""
            ALTER TABLE grids
            ALTER COLUMN status TYPE text
        """)
        
        # Drop the gridstatus enum
        print("Dropping gridstatus enum...")
        await conn.execute("""
            DROP TYPE IF EXISTS gridstatus
        """)
        
        # Create the gridstatus enum with correct values
        print("Creating gridstatus enum with correct values...")
        await conn.execute("""
            CREATE TYPE gridstatus AS ENUM (
                'active', 'inactive', 'creating', 'paused', 'terminated', 'error'
            )
        """)
        
        # Convert the status column back to enum
        print("Converting grid.status back to enum...")
        await conn.execute("""
            ALTER TABLE grids
            ALTER COLUMN status TYPE gridstatus USING status::gridstatus
        """)
        
        print("GridStatus enum fixed successfully!")
        await conn.close()
        return True
    except Exception as e:
        print(f"Error fixing gridstatus enum: {e}")
        print(traceback.format_exc())
        return False

async def main():
    """Run the fix"""
    print("Starting gridstatus enum fix...")
    result = await fix_gridstatus()
    if result:
        print("GridStatus enum fix completed successfully!")
    else:
        print("GridStatus enum fix failed!")

if __name__ == "__main__":
    asyncio.run(main()) 