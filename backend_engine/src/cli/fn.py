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
        headers = ["UID", "Name", "Grid", "Status", "Docker Image", "Resources", "Created"]
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
                fn.get("docker_image", "default"),
                resource_str.strip(),
                fn["created_at"].split("T")[0]  # Format date
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="create")
@click.argument("name")
@click.option("--grid", "-g", required=True, help="Grid UID")
@click.option("--script", "-s", required=True, help="Path to script")
@click.option("--artifactory", "-a", help="Artifactory URL")
@click.option("--cpu", "-c", default=1, help="CPU cores required")
@click.option("--memory", "-m", default=1024, help="Memory required (MB)")
@click.option("--gpu", "-G", is_flag=True, help="Requires GPU")
@click.option("--docker-image", "-d", default="default", help="Docker image to use")
def create_function_cmd(name, grid, script, artifactory, cpu, memory, gpu, docker_image):
    """Create a new function"""
    try:
        # Prepare resource requirements
        resources = {
            "cpu": cpu,
            "memory": memory,
            "gpu": gpu
        }
        
        # Prepare function data
        data = {
            "name": name,
            "grid_uid": grid,
            "script_path": script,
            "resource_requirements": resources,
            "docker_image": docker_image
        }
        
        if artifactory:
            data["artifactory_url"] = artifactory
        
        client = APIClient()
        function = client.post("/api/functions", data)
        
        click.echo(f"Function created with UID: {function['uid']}")
        click.echo(f"Name: {function['name']}")
        click.echo(f"Docker Image: {function['docker_image']}")
        click.echo(f"Status: {function['status']}")
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
        click.echo(f"Docker Image: {function.get('docker_image', 'default')}")
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