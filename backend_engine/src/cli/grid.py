import click
import json
import os
from datetime import datetime
from tabulate import tabulate
from cli.api_client import APIClient

@click.group(name="grid")
def grid_cli():
    """Manage computation grids"""
    pass

@grid_cli.command(name="list")
def list_grids():
    """List all grids"""
    try:
        client = APIClient()
        grids = client.get("/api/grids")
        
        if not grids:
            click.echo("No grids found")
            return
        
        # Format data for tabulate
        headers = ["UID", "Name", "Size", "Status", "Utilization", "Free Slots", "Created"]
        table_data = []
        
        for grid in grids:
            table_data.append([
                grid["uid"],
                grid["name"],
                f"{grid['length']}x{grid['width']}",
                grid["status"],
                f"{grid['utilization']:.1f}%",
                grid["free_slots"],
                grid["created_at"].split("T")[0]  # Format date
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@grid_cli.command(name="create")
@click.option("--name", "-n", required=True, help="Grid name")
@click.option("--length", "-l", required=True, type=int, help="Grid length")
@click.option("--width", "-w", required=True, type=int, help="Grid width")
def create_grid(name, length, width):
    """Create a new grid"""
    try:
        client = APIClient()
        data = {
            "name": name,
            "length": length,
            "width": width
        }
        
        response = client.post("/api/grids", data)
        
        click.echo(f"Grid created with UID: {response['uid']}")
        click.echo("Initializing grid...")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@grid_cli.command(name="show")
@click.argument("uid")
def show_grid(uid):
    """Show details of a specific grid"""
    try:
        client = APIClient()
        grid = client.get(f"/api/grids/{uid}")
        
        click.echo(f"Grid: {grid['name']} ({grid['uid']})")
        click.echo(f"Size: {grid['length']}x{grid['width']}")
        click.echo(f"Status: {grid['status']}")
        click.echo(f"Utilization: {grid['utilization']:.1f}%")
        click.echo(f"Free Slots: {grid['free_slots']}")
        click.echo(f"Created: {grid['created_at']}")
        click.echo(f"Updated: {grid['updated_at']}")
        
        # Get workers for this grid
        workers = client.get("/api/workers", {"grid": uid})
        click.echo(f"\nWorkers: {len(workers)}")
        
        if workers:
            # Show worker summary
            online = sum(1 for w in workers if w["status"] == "ONLINE")
            offline = sum(1 for w in workers if w["status"] == "OFFLINE")
            busy = sum(1 for w in workers if w["status"] == "BUSY")
            
            click.echo(f"  Online: {online}")
            click.echo(f"  Busy: {busy}")
            click.echo(f"  Offline: {offline}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@grid_cli.command(name="activate")
@click.argument("uid")
def activate_grid_cmd(uid):
    """Activate a grid"""
    try:
        client = APIClient()
        response = client.post(f"/api/grids/{uid}/activate")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@grid_cli.command(name="pause")
@click.argument("uid")
def pause_grid_cmd(uid):
    """Pause a grid"""
    try:
        client = APIClient()
        response = client.post(f"/api/grids/{uid}/pause")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@grid_cli.command(name="terminate")
@click.argument("uid")
@click.confirmation_option(prompt="Are you sure you want to terminate this grid?")
def terminate_grid_cmd(uid):
    """Terminate a grid"""
    try:
        client = APIClient()
        response = client.post(f"/api/grids/{uid}/terminate")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")
