import click
import json
from tabulate import tabulate
from cli.api_client import APIClient

@click.group(name="worker")
def worker_cli():
    """Manage workers"""
    pass

@worker_cli.command(name="list")
@click.option("--grid", "-g", help="Filter by grid UID")
@click.option("--status", "-s", help="Filter by status (online, offline, busy)")
def list_workers(grid, status):
    """List all workers"""
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
        headers = ["UID", "Name", "Grid", "Status", "CPU", "Memory", "Docker Image", "Last Heartbeat"]
        table_data = []
        
        for worker in workers:
            # Format memory as GB
            memory_gb = worker["memory_total"] / 1024
            
            # Get docker image from spec
            docker_image = worker.get("spec", {}).get("docker_image", "default")
            
            table_data.append([
                worker["uid"],
                worker["name"],
                worker["grid_uid"],
                worker["status"],
                f"{worker['cpu_total']} cores",
                f"{memory_gb:.1f} GB",
                docker_image,
                worker["last_heartbeat"].split("T")[0] if worker.get("last_heartbeat") else "Never"
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="create")
@click.argument("name")
@click.option("--grid", "-g", required=True, help="Grid UID")
@click.option("--cpu", "-c", default=2, help="CPU cores")
@click.option("--memory", "-m", default=4096, help="Memory in MB")
@click.option("--gpu-id", "-G", help="GPU ID")
@click.option("--gpu-memory", "-M", type=int, help="GPU memory in MB")
@click.option("--docker-image", "-d", default="python:3.11-slim", help="Docker image")
@click.option("--count", "-n", default=1, help="Number of workers to create")
def create_worker(name, grid, cpu, memory, gpu_id, gpu_memory, docker_image, count):
    """Create a new worker"""
    try:
        client = APIClient()
        
        data = {
            "name": name,
            "grid_uid": grid,
            "cpu_total": cpu,
            "memory_total": memory,
            "cpu_request": cpu,
            "memory_request": memory,
            "docker_image": docker_image,
            "count": count
        }
        
        if gpu_id:
            data["gpu_id"] = gpu_id
        if gpu_memory:
            data["gpu_memory"] = gpu_memory
        
        response = client.post("/api/workers", data)
        
        if count > 1:
            click.echo(f"Created {len(response['workers'])} workers")
            for worker in response["workers"]:
                click.echo(f"  - {worker['name']} ({worker['uid']})")
        else:
            click.echo(f"Worker created with UID: {response['uid']}")
            click.echo(f"Name: {response['name']}")
            click.echo(f"Grid: {response['grid_uid']}")
            click.echo(f"Status: {response['status']}")
            click.echo(f"CPU: {response['cpu_total']} cores")
            click.echo(f"Memory: {response['memory_total']} MB")
            click.echo(f"Docker Image: {response.get('docker_image', 'python:3.11-slim')}")
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
        click.echo(f"CPU: {worker['cpu_total']} cores (Available: {worker['cpu_available']} cores)")
        
        memory_total_gb = worker['memory_total'] / 1024
        memory_available_gb = worker['memory_available'] / 1024 if worker.get('memory_available') else 0
        
        click.echo(f"Memory: {memory_total_gb:.1f} GB (Available: {memory_available_gb:.1f} GB)")
        
        if worker.get('gpu_id'):
            click.echo(f"GPU: {worker['gpu_id']}")
            if worker.get('gpu_memory'):
                gpu_memory_gb = worker['gpu_memory'] / 1024
                click.echo(f"GPU Memory: {gpu_memory_gb:.1f} GB")
        
        # Get docker image from spec
        docker_image = worker.get("spec", {}).get("docker_image", "default")
        click.echo(f"Docker Image: {docker_image}")
        
        if worker.get('last_heartbeat'):
            click.echo(f"Last Heartbeat: {worker['last_heartbeat']}")
            
        click.echo(f"Created: {worker['created_at']}")
        click.echo(f"Updated: {worker['updated_at']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="associate")
@click.argument("worker_uid")
@click.argument("grid_uid")
def associate_worker(worker_uid, grid_uid):
    """Associate a worker with a grid"""
    try:
        client = APIClient()
        response = client.post(f"/api/workers/{worker_uid}/grid/{grid_uid}")
        click.echo(response["message"])
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

@worker_cli.command(name="delete")
@click.argument("uids", nargs=-1)  # Accept multiple UIDs
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
def delete_worker(uids, force):
    """Delete one or more workers"""
    if not uids:
        click.echo("Error: No worker UIDs provided")
        return
    
    try:
        client = APIClient()
        
        # If multiple UIDs, confirm once for all
        if len(uids) > 1 and not force:
            click.echo(f"You are about to delete {len(uids)} workers:")
            for uid in uids:
                try:
                    worker = client.get(f"/api/workers/{uid}")
                    click.echo(f"  - {worker['name']} ({uid})")
                except Exception:
                    click.echo(f"  - Unknown worker ({uid})")
            
            if not click.confirm("Are you sure you want to delete these workers?"):
                click.echo("Operation cancelled.")
                return
        
        # Delete each worker
        for uid in uids:
            try:
                # For single worker or forced deletion, no need for additional confirmation
                if len(uids) == 1 and not force:
                    try:
                        worker = client.get(f"/api/workers/{uid}")
                        click.echo(f"You are about to delete worker: {worker['name']} ({uid})")
                    except Exception:
                        click.echo(f"You are about to delete worker with UID: {uid}")
                    
                    if not click.confirm("Are you sure you want to delete this worker?"):
                        click.echo("Operation cancelled.")
                        continue
                
                response = client.delete(f"/api/workers/{uid}")
                click.echo(f"Worker {uid} deleted successfully")
            except Exception as e:
                click.echo(f"Error deleting worker {uid}: {str(e)}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@worker_cli.command(name="deploy")
@click.argument("uid")
def deploy_worker_cmd(uid):
    """Deploy a worker to Kubernetes"""
    try:
        client = APIClient()
        response = client.post(f"/api/workers/{uid}/deploy")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")
