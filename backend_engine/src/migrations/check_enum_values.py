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

async def check_enum_values():
    """Check enum values in the database"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Check gridstatus enum values
        print("\nChecking gridstatus enum values...")
        enum_values = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'gridstatus'
            ORDER BY e.enumsortorder
        """)
        
        if enum_values:
            print("Current gridstatus enum values:")
            for val in enum_values:
                print(f"  - {val['enumlabel']}")
        else:
            print("No gridstatus enum found")
        
        # Check grid table status column
        print("\nChecking grid table status values...")
        grid_statuses = await conn.fetch("""
            SELECT uid, status FROM grids
        """)
        
        if grid_statuses:
            print("Current grid status values:")
            for grid in grid_statuses:
                print(f"  - {grid['uid']}: {grid['status']}")
        else:
            print("No grids found")
        
        # Check if there are any tables using gridstatus
        print("\nChecking tables using gridstatus enum...")
        tables = await conn.fetch("""
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN pg_type t ON c.udt_name = t.typname
            WHERE t.typname = 'gridstatus'
        """)
        
        if tables:
            print("Tables using gridstatus enum:")
            for table in tables:
                print(f"  - {table['table_name']}.{table['column_name']}")
        else:
            print("No tables using gridstatus enum")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error checking enum values: {e}")
        print(traceback.format_exc())
        return False

async def main():
    """Run the check"""
    print("Starting enum value check...")
    result = await check_enum_values()
    if result:
        print("\nEnum value check completed successfully!")
    else:
        print("\nEnum value check failed!")

if __name__ == "__main__":
    asyncio.run(main()) 