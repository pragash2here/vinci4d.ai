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

async def add_grid_columns():
    """Add worker_count and busy_workers columns to grids table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Check if worker_count column exists
        worker_count_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'grids' 
                AND column_name = 'worker_count'
            )
        """)
        
        # Check if busy_workers column exists
        busy_workers_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'grids' 
                AND column_name = 'busy_workers'
            )
        """)
        
        # Add worker_count column if it doesn't exist
        if not worker_count_exists:
            print("Adding worker_count column to grids table...")
            await conn.execute("""
                ALTER TABLE grids 
                ADD COLUMN worker_count INTEGER DEFAULT 0 NOT NULL
            """)
            print("worker_count column added successfully!")
        else:
            print("worker_count column already exists.")
        
        # Add busy_workers column if it doesn't exist
        if not busy_workers_exists:
            print("Adding busy_workers column to grids table...")
            await conn.execute("""
                ALTER TABLE grids 
                ADD COLUMN busy_workers INTEGER DEFAULT 0 NOT NULL
            """)
            print("busy_workers column added successfully!")
        else:
            print("busy_workers column already exists.")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error adding columns to grids table: {e}")
        return False

async def fix_enum_values():
    """Fix enum values in the database to use lowercase"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Fixing enum values to use lowercase...")
        
        # Tables and their status columns
        tables = [
            ("functions", "status"),
            ("tasks", "status"),
            ("workers", "status"),
            ("grids", "status")
        ]
        
        for table, column in tables:
            try:
                # Get all records with uppercase status values
                records = await conn.fetch(f"""
                    SELECT uid, {column} FROM {table}
                    WHERE {column} IS NOT NULL
                """)
                
                updated_count = 0
                for record in records:
                    status = record[column]
                    if status and status.isupper():
                        lowercase_status = status.lower()
                        await conn.execute(f"""
                            UPDATE {table}
                            SET {column} = $1
                            WHERE uid = $2
                        """, lowercase_status, record['uid'])
                        updated_count += 1
                
                print(f"Updated {updated_count} {table}.{column} values to lowercase")
            except Exception as e:
                print(f"Error fixing {table}.{column} values: {e}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error fixing enum values: {e}")
        return False

async def ensure_enum_types():
    """Ensure all enum types exist in the database"""
    try:
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
                else:
                    print(f"{enum_name} enum already exists")
            except Exception as e:
                print(f"Error with {enum_name} enum: {e}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error ensuring enum types: {e}")
        return False

async def main():
    """Run all migrations"""
    print("Starting database migrations...")
    await ensure_enum_types()  # Make sure enum types exist first
    await add_grid_columns()
    await fix_enum_values()
    print("Database migrations completed!")

if __name__ == "__main__":
    asyncio.run(main()) 