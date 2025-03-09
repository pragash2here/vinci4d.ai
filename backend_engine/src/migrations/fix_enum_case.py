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

async def fix_enum_case():
    """Fix all enum values in the database to use lowercase"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # First, convert all status columns to text
        tables = ["grids", "functions", "tasks", "workers"]
        
        for table in tables:
            print(f"\nFixing {table} table...")
            
            # Check if the table exists
            table_exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """)
            
            if not table_exists:
                print(f"Table {table} doesn't exist, skipping")
                continue
            
            # Check if the status column exists
            status_exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = 'status'
                )
            """)
            
            if not status_exists:
                print(f"Status column doesn't exist in {table}, skipping")
                continue
            
            # Get the column type
            column_type = await conn.fetchval(f"""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'status'
            """)
            
            print(f"Current status column type in {table}: {column_type}")
            
            # Convert to text if it's an enum
            if column_type == 'USER-DEFINED':
                print(f"Converting {table}.status to text...")
                await conn.execute(f"""
                    ALTER TABLE {table}
                    ALTER COLUMN status TYPE text
                """)
                print(f"Converted {table}.status to text")
            
            # Update all values to lowercase
            print(f"Converting {table}.status values to lowercase...")
            result = await conn.execute(f"""
                UPDATE {table}
                SET status = LOWER(status)
                WHERE status != LOWER(status)
            """)
            
            print(f"Updated {result.split(' ')[-1]} rows in {table}")
        
        # Now recreate the enum types with lowercase values
        enum_types = {
            "gridstatus": ["active", "inactive", "creating", "paused", "terminated", "error"],
            "functionstatus": ["ready", "pending", "running", "completed", "failed", "cancelled"],
            "taskstatus": ["pending", "running", "completed", "failed", "cancelled"],
            "workerstatus": ["online", "offline", "busy", "error"]
        }
        
        for enum_name, values in enum_types.items():
            print(f"\nRecreating {enum_name} enum...")
            
            # Drop the enum type if it exists
            await conn.execute(f"""
                DROP TYPE IF EXISTS {enum_name}
            """)
            
            # Create the enum type with lowercase values
            values_str = ", ".join(f"'{val}'" for val in values)
            await conn.execute(f"""
                CREATE TYPE {enum_name} AS ENUM ({values_str})
            """)
            
            print(f"Created {enum_name} enum with values: {values}")
        
        # Convert columns back to enum types
        table_enums = {
            "grids": "gridstatus",
            "functions": "functionstatus",
            "tasks": "taskstatus",
            "workers": "workerstatus"
        }
        
        for table, enum_type in table_enums.items():
            print(f"\nConverting {table}.status back to {enum_type}...")
            
            # Check if the table exists
            table_exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """)
            
            if not table_exists:
                print(f"Table {table} doesn't exist, skipping")
                continue
            
            # Convert to enum
            try:
                await conn.execute(f"""
                    ALTER TABLE {table}
                    ALTER COLUMN status TYPE {enum_type} USING status::{enum_type}
                """)
                print(f"Converted {table}.status to {enum_type}")
            except Exception as e:
                print(f"Error converting {table}.status to {enum_type}: {e}")
                print(traceback.format_exc())
        
        print("\nEnum case fix completed successfully!")
        await conn.close()
        return True
    except Exception as e:
        print(f"Error fixing enum case: {e}")
        print(traceback.format_exc())
        return False

async def main():
    """Run the fix"""
    print("Starting enum case fix...")
    result = await fix_enum_case()
    if result:
        print("Enum case fix completed successfully!")
    else:
        print("Enum case fix failed!")

if __name__ == "__main__":
    asyncio.run(main()) 