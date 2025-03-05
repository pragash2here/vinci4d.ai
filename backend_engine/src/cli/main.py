#!/usr/bin/env python
import click
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

# Import CLI command groups
from cli.grid import grid_cli
from cli.fn import fn_cli
from cli.task import task_cli
from cli.worker import worker_cli

@click.group()
def cli():
    """Vinci4D Backend Engine CLI"""
    pass

# Register command groups
cli.add_command(grid_cli)
cli.add_command(fn_cli)
cli.add_command(task_cli)
cli.add_command(worker_cli)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / 'config.env'
    load_dotenv(env_path)
    
    # Run the CLI
    cli()
