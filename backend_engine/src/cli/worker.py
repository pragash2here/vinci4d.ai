import click
from tabulate import tabulate
from cli.api_client import APIClient

@click.group(name="worker")
def worker_cli():
    """Manage worker nodes"""
    pass

@worker_cli.command(name="list")
@click.option("--grid", "-g", help="Filter by grid UID")
@click.option("--status", "-s", help="Filter by status")
def list_workers(grid, status):
    """List workers with optional filters"""
    try:
        client = APIClient()
        params = {}
        if grid:
            params["grid"] = grid
        if status:
            params["status"] = status
            
        workers = client.get("/api/workers", params)
        
        if not workers:
            click.echo("No workers found")
            return
        
        # Format data for tabulate
        headers = ["UID", "Name", "Grid", "Status", "CPU", "Memory", "Last Heartbeat"]
        table_data = []
        
        for worker in workers:
            cpu_usage = f"{worker['cpu_total'] - worker['cpu_available']:.1f}/{worker['cpu_total']:.1f}" if worker.get('cpu_available') is not None else f"{worker['cpu_total']:.1f}"
            memory_usage = f"{(worker['memory_total'] - worker['memory_available'])/1024:.1f}/{worker['memory_total']/1024:.1f} GB" if worker.get('memory_available') is not None else f"{worker['memory_total']/1024:.1f} GB"
            
            last_heartbeat = worker.get('last_heartbeat', 'Never').split("T")[0] if worker.get('last_heartbeat') else "Never"
            
            table_data.append([
                worker["uid"],
                worker["name"],
                worker["grid_uid"],
                worker["status"],
                cpu_usage,
                memory_usage,
                last_heartbeat
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="show")
@click.argument("uid")
def show_worker(uid):
    """Show details of a specific worker"""
    try:
        client = APIClient()
        worker = client.get(f"/api/workers/{uid}")
        
        click.echo(f"Worker: {worker['name']} ({worker['uid']})")
        click.echo(f"Grid: {worker['grid_uid']}")
        click.echo(f"Status: {worker['status']}")
        click.echo(f"CPU: {worker.get('cpu_available', 0)}/{worker['cpu_total']} cores available")
        click.echo(f"Memory: {worker.get('memory_available', 0)/1024:.2f}/{worker['memory_total']/1024:.2f} GB available")
        
        if worker.get('gpu_id'):
            click.echo(f"GPU: {worker['gpu_id']}")
            click.echo(f"GPU Memory: {worker['gpu_memory']/1024:.2f} GB")
        
        # Get tasks for this worker
        tasks = client.get("/api/tasks", {"worker": uid})
        click.echo(f"Tasks: {len(tasks)}")
        
        if worker.get('last_heartbeat'):
            click.echo(f"Last Heartbeat: {worker['last_heartbeat']}")
            
        click.echo(f"Created: {worker['created_at']}")
        click.echo(f"Updated: {worker['updated_at']}")
        
        if worker.get('spec'):
            click.echo("Specifications:")
            for key, value in worker['spec'].items():
                click.echo(f"  {key}: {value}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="online")
@click.argument("uid")
def set_worker_online(uid):
    """Set a worker status to online"""
    try:
        client = APIClient()
        response = client.post(f"/api/workers/{uid}/online")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="offline")
@click.argument("uid")
def set_worker_offline(uid):
    """Set a worker status to offline"""
    try:
        client = APIClient()
        response = client.post(f"/api/workers/{uid}/offline")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")
