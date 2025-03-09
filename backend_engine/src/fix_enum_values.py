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

async def fix_enum_values():
    """Fix the FunctionStatus enum values in the database"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        
        print("Checking FunctionStatus enum values...")
        
        # Get the enum values
        enum_values = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'gridstatus'
        """)
        
        enum_values_list = [val['enumlabel'] for val in enum_values]
        print(f"Current enum values: {enum_values_list}")
        
        # Check if we need to recreate the enum
        expected_values = ['creating', 'active', 'paused', 'terminated', 'error']
        missing_values = [val for val in expected_values if val not in enum_values_list]
        
        if missing_values:
            print(f"Missing enum values: {missing_values}")
            print("Recreating the enum type...")
            
            # Create a new type with all values
            await conn.execute("""
                CREATE TYPE gridstatus_new AS ENUM (
                    'creating', 'active', 'paused', 'terminated', 'error'
                )
            """)
            
            # Update the functions table to use the new type
            await conn.execute("""
                ALTER TABLE tasks 
                ALTER COLUMN status TYPE gridstatus_new 
                USING status::text::gridstatus_new
            """)
            
            # Drop the old type
            await conn.execute("""
                DROP TYPE gridstatus
            """)
            
            # Rename the new type to the original name
            await conn.execute("""
                ALTER TYPE gridstatus_new RENAME TO gridstatus
            """)
            
            print("FunctionStatus enum updated successfully!")
        else:
            print("All expected enum values are present.")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error fixing enum values: {e}")
        return False

async def main():
    """Run the fix"""
    print("Starting enum fix...")
    result = await fix_enum_values()
    if result:
        print("Fix completed successfully!")
    else:
        print("Fix failed!")

if __name__ == "__main__":
    asyncio.run(main()) 