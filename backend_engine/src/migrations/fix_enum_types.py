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

async def fix_enum_types():
    """Fix all enum types in the database"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
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
                print(f"\nChecking {enum_name} enum...")
                
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
                    print(f"Created {enum_name} enum with values: {values}")
                else:
                    # Get current enum values
                    current_values = await conn.fetch(f"""
                        SELECT e.enumlabel
                        FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = '{enum_name}'
                    """)
                    
                    current_values_list = [val['enumlabel'] for val in current_values]
                    print(f"Current {enum_name} values: {current_values_list}")
                    
                    # Check if we need to update the enum
                    missing_values = [val for val in values if val not in current_values_list]
                    
                    if missing_values:
                        print(f"Missing values in {enum_name}: {missing_values}")
                        print(f"Recreating {enum_name} enum...")
                        
                        # Create a new enum type with all values
                        new_type_name = f"{enum_name}_new"
                        values_str = ", ".join(f"'{val}'" for val in values)
                        
                        # Create the new enum type
                        await conn.execute(f"""
                            CREATE TYPE {new_type_name} AS ENUM ({values_str})
                        """)
                        
                        # Find tables using this enum
                        tables = await conn.fetch(f"""
                            SELECT c.table_name, c.column_name
                            FROM information_schema.columns c
                            JOIN pg_type t ON c.udt_name = t.typname
                            WHERE t.typname = '{enum_name}'
                        """)
                        
                        # Update each table to use the new enum
                        for table in tables:
                            table_name = table['table_name']
                            column_name = table['column_name']
                            
                            print(f"Updating {table_name}.{column_name} to use new enum...")
                            
                            # First convert to text
                            await conn.execute(f"""
                                ALTER TABLE {table_name}
                                ALTER COLUMN {column_name} TYPE text
                            """)
                            
                            # Then convert to new enum
                            await conn.execute(f"""
                                ALTER TABLE {table_name}
                                ALTER COLUMN {column_name} TYPE {new_type_name} USING {column_name}::{new_type_name}
                            """)
                        
                        # Drop the old enum type
                        await conn.execute(f"""
                            DROP TYPE {enum_name} CASCADE
                        """)
                        
                        # Rename the new type to the original name
                        await conn.execute(f"""
                            ALTER TYPE {new_type_name} RENAME TO {enum_name}
                        """)
                        
                        print(f"Successfully updated {enum_name} enum")
                    else:
                        print(f"All expected values present in {enum_name}")
            except Exception as e:
                print(f"Error fixing {enum_name} enum: {e}")
                print(traceback.format_exc())
        
        await conn.close()
        print("\nEnum types fixed successfully")
        return True
    except Exception as e:
        print(f"Error fixing enum types: {e}")
        print(traceback.format_exc())
        return False

async def main():
    """Run the fix"""
    print("Starting enum type fixes...")
    result = await fix_enum_types()
    if result:
        print("Enum type fixes completed successfully!")
    else:
        print("Enum type fixes failed!")

if __name__ == "__main__":
    asyncio.run(main()) 