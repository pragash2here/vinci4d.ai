import click
import json
import os
from datetime import datetime
from tabulate import tabulate
from cli.api_client import APIClient

@click.group(name="fn")
def fn_cli():
    """Manage functions"""
    pass

@fn_cli.command(name="list")
def list_functions():
    """List all functions"""
    try:
        client = APIClient()
        functions = client.get("/api/functions")
        
        if not functions:
            click.echo("No functions found")
            return
        
        # Format data for tabulate
        headers = ["UID", "Name", "Grid", "Status", "Resources", "Created"]
        table_data = []
        
        for fn in functions:
            # Format resources as a compact string
            resources = fn.get("resource_requirements", {})
            resource_str = ""
            if resources:
                if "cpu" in resources:
                    resource_str += f"CPU:{resources['cpu']} "
                if "memory" in resources:
                    memory_gb = resources['memory'] / 1024
                    resource_str += f"Mem:{memory_gb:.1f}GB "
                if "gpu" in resources and resources["gpu"]:
                    resource_str += "GPU "
                if "timeout" in resources:
                    hours = resources['timeout'] / 3600
                    resource_str += f"T:{hours:.1f}h"
            
            table_data.append([
                fn["uid"],
                fn["name"],
                fn["grid_uid"],
                fn["status"],
                resource_str.strip(),
                fn["created_at"].split("T")[0]  # Format date
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="create")
@click.option("--name", "-n", required=True, help="Function name")
@click.option("--grid", "-g", required=True, help="Grid UID")
@click.option("--script", "-s", required=True, help="Script path")
@click.option("--resources", "-r", required=True, help="Resource requirements (JSON string or file path)")
@click.option("--artifactory", "-a", help="Artifactory URL")
def create_function(name, grid, script, resources, artifactory):
    """Create a new function"""
    try:
        # Parse resources - could be a JSON string or a file path
        try:
            # First try to parse as JSON string
            resource_requirements = json.loads(resources)
        except json.JSONDecodeError:
            # If that fails, try to read from file
            if os.path.exists(resources):
                try:
                    with open(resources, 'r') as f:
                        resource_requirements = json.load(f)
                except Exception as e:
                    click.echo(f"Error reading resources file: {e}")
                    return
            else:
                click.echo("Resources must be valid JSON or a path to a JSON file")
                return
        
        # Read script file if it exists
        script_content = None
        if os.path.exists(script):
            with open(script, 'r') as f:
                script_content = f.read()
        
        client = APIClient()
        data = {
            "name": name,
            "grid_uid": grid,
            "script_path": script,
            "script_content": script_content,
            "artifactory_url": artifactory,
            "resource_requirements": resource_requirements
        }
        
        response = client.post("/api/functions", data)
        click.echo(f"Function created with UID: {response['uid']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="show")
@click.argument("uid")
def show_function(uid):
    """Show details of a specific function"""
    try:
        client = APIClient()
        function = client.get(f"/api/functions/{uid}")
        
        click.echo(f"Function: {function['name']} ({function['uid']})")
        click.echo(f"Grid: {function['grid_uid']}")
        click.echo(f"Script: {function['script_path']}")
        click.echo(f"Status: {function['status']}")
        
        # Get task count
        tasks = client.get("/api/tasks", {"function": uid})
        click.echo(f"Tasks: {len(tasks)}")
        
        click.echo(f"Resources: {json.dumps(function['resource_requirements'], indent=2)}")
        
        if function.get('artifactory_url'):
            click.echo(f"Artifactory: {function['artifactory_url']}")
            
        if function.get('started_at'):
            click.echo(f"Started: {function['started_at']}")
            
        if function.get('ended_at'):
            click.echo(f"Ended: {function['ended_at']}")
            
        click.echo(f"Created: {function['created_at']}")
        click.echo(f"Updated: {function['updated_at']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="start")
@click.argument("uid")
def start_function_cmd(uid):
    """Start a function"""
    try:
        client = APIClient()
        response = client.post(f"/api/functions/{uid}/start")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="cancel")
@click.argument("uid")
def cancel_function_cmd(uid):
    """Cancel a function"""
    try:
        client = APIClient()
        response = client.post(f"/api/functions/{uid}/cancel")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="status")
@click.argument("uid")
def check_function_status_cmd(uid):
    """Check function status"""
    try:
        client = APIClient()
        function = client.get(f"/api/functions/{uid}")
        click.echo(f"Function {uid} status: {function['status']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}") 