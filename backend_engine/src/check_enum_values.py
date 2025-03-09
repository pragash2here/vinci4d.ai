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

async def check_enum_values():
    """Check the current values of the FunctionStatus enum"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        
        # Get the enum values
        enum_values = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'functionstatus'
        """)
        
        enum_values_list = [val['enumlabel'] for val in enum_values]
        print(f"Current FunctionStatus enum values: {enum_values_list}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"Error checking enum values: {e}")
        return False

async def main():
    """Run the check"""
    print("Checking enum values...")
    await check_enum_values()

if __name__ == "__main__":
    asyncio.run(main()) 