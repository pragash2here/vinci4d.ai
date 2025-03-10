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

async def fix_worker_fk_constraint():
    """Fix the foreign key constraint for worker_uid in tasks table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # First, find the constraint name
        constraint_info = await conn.fetchrow("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'tasks'::regclass
            AND confrelid = 'workers'::regclass
        """)
        
        if not constraint_info:
            print("No foreign key constraint found between tasks and workers")
            await conn.close()
            return False
        
        constraint_name = constraint_info['conname']
        print(f"Found constraint: {constraint_name}")
        
        # Drop the existing constraint
        print("Dropping existing constraint...")
        await conn.execute(f"""
            ALTER TABLE tasks
            DROP CONSTRAINT {constraint_name}
        """)
        
        # Add a new constraint with ON DELETE SET NULL
        print("Adding new constraint with ON DELETE SET NULL...")
        await conn.execute("""
            ALTER TABLE tasks
            ADD CONSTRAINT tasks_worker_uid_fkey
            FOREIGN KEY (worker_uid)
            REFERENCES workers(uid)
            ON DELETE SET NULL
        """)
        
        print("Foreign key constraint updated successfully")
        await conn.close()
        return True
    except Exception as e:
        print(f"Error fixing worker foreign key constraint: {e}")
        print(traceback.format_exc())
        return False

async def main():
    """Run the migration"""
    print("Starting migration to fix worker foreign key constraint...")
    result = await fix_worker_fk_constraint()
    if result:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")

if __name__ == "__main__":
    asyncio.run(main()) 