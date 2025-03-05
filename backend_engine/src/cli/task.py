import click
from tabulate import tabulate
from cli.api_client import APIClient

@click.group(name="task")
def task_cli():
    """Manage tasks"""
    pass

@task_cli.command(name="list")
@click.option("--function", "-f", help="Filter by function UID")
@click.option("--worker", "-w", help="Filter by worker UID")
@click.option("--status", "-s", help="Filter by status")
def list_tasks(function, worker, status):
    """List tasks with optional filters"""
    try:
        client = APIClient()
        params = {}
        if function:
            params["function"] = function
        if worker:
            params["worker"] = worker
        if status:
            params["status"] = status
            
        tasks = client.get("/api/tasks", params)
        
        if not tasks:
            click.echo("No tasks found")
            return
        
        # Format data for tabulate
        headers = ["UID", "Function", "Worker", "Status", "Created"]
        table_data = []
        
        for task in tasks:
            table_data.append([
                task["uid"],
                task.get("function_uid", "N/A"),
                task.get("worker_uid", "N/A"),
                task["status"],
                task["created_at"].split("T")[0]  # Format date
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@task_cli.command(name="show")
@click.argument("uid")
def show_task(uid):
    """Show details of a specific task"""
    try:
        client = APIClient()
        task = client.get(f"/api/tasks/{uid}")
        
        click.echo(f"Task: {task['uid']}")
        click.echo(f"Function: {task.get('function_uid', 'N/A')}")
        click.echo(f"Worker: {task.get('worker_uid', 'N/A')}")
        click.echo(f"Status: {task['status']}")
        
        if task.get('result'):
            click.echo(f"Result: {task['result']}")
            
        if task.get('error'):
            click.echo(f"Error: {task['error']}")
            
        click.echo(f"Created: {task['created_at']}")
        click.echo(f"Updated: {task['updated_at']}")
        
        if task.get('started_at'):
            click.echo(f"Started: {task['started_at']}")
            
        if task.get('ended_at'):
            click.echo(f"Ended: {task['ended_at']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
