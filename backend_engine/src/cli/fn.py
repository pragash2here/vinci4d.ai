import click
import json
import os
from datetime import datetime
from tabulate import tabulate
from cli.api_client import APIClient
import requests

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
        headers = ["UID", "Name", "Grid", "Status", "Docker Image", "Batch Size", "Resources", "Created"]
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
                fn.get("batch_size", 1),  # Add batch size
                resource_str.strip(),
                fn["created_at"].split("T")[0]  # Format date
            ])
        
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@fn_cli.command(name="create")
@click.argument("name")
@click.option("--grid", "-g", required=True, help="Grid UID")
@click.option("--script", "-s", required=True, help="Path to script file")
@click.option("--artifactory", "-a", help="Artifactory URL")
@click.option("--cpu", "-c", default=1, help="CPU cores required")
@click.option("--memory", "-m", default=1024, help="Memory required (MB)")
@click.option("--gpu", "-G", is_flag=True, help="Requires GPU")
@click.option("--docker-image", "-d", default="python:3.11-slim", help="Docker image to use")
@click.option("--batch-size", "-b", default=1, help="Number of parallel tasks to create")
def create_function_cmd(name, grid, script, artifactory, cpu, memory, gpu, docker_image, batch_size):
    """Create a new function"""
    try:
        # Expand user path (e.g., ~/script.py)
        script_path = os.path.expanduser(script)
        
        # Check if script file exists
        if not os.path.exists(script_path):
            click.echo(f"Error: Script file not found: {script_path}")
            return
        
        client = APIClient()
        
        # First, upload the script file
        click.echo("Uploading script file...")
        
        # Read the script file
        with open(script_path, 'rb') as f:
            script_content = f.read()
        
        # Create a multipart form-data request
        files = {'file': (os.path.basename(script_path), script_content, 'text/plain')}
        
        # Upload the file
        upload_response = client.post_file("/api/functions/upload", files=files)
        
        if "error" in upload_response:
            click.echo(f"Error uploading script: {upload_response['error']}")
            return
        
        click.echo(f"Script uploaded successfully: {upload_response['filename']}")
        
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
            "server_file_path": upload_response["file_path"],  # Use the server file path
            "resource_requirements": resources,
            "docker_image": docker_image,
            "batch_size": batch_size  # Add batch size
        }
        
        if artifactory:
            data["artifactory_url"] = artifactory
        
        # Create the function
        click.echo("Creating function...")
        function = client.post("/api/functions", data)
        
        click.echo(f"Function created with UID: {function['uid']}")
        click.echo(f"Name: {function['name']}")
        click.echo(f"Script path: {function['script_path']}")
        click.echo(f"Docker Image: {function['docker_image']}")
        click.echo(f"Batch Size: {function.get('batch_size', 1)}")  # Display batch size
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
        click.echo(f"Batch Size: {function.get('batch_size', 1)}")
        
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
@click.option('--params', '-p', help='JSON string with function parameters')
@click.option('--params-file', '-f', help='Path to JSON file with function parameters')
@click.option('--batch-size', '-b', type=int, help='Override batch size for this run')
def start_function_cmd(uid, params, params_file, batch_size):
    """Start a function with the given UID"""
    if params and params_file:
        click.echo("Error: Cannot specify both --params and --params-file")
        return
    
    # Load parameters from file if specified
    if params_file:
        try:
            with open(params_file, 'r') as f:
                params = f.read()
        except Exception as e:
            click.echo(f"Error reading params file: {e}")
            return
    
    # Parse JSON parameters
    params_dict = {}
    if params:
        try:
            import json
            params_dict = json.loads(params)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in parameters")
            return
    
    # Add batch size to parameters if specified
    if batch_size:
        params_dict['batch_size'] = batch_size
        # Convert back to JSON string
        params = json.dumps(params_dict)
    
    # Prepare request data
    data = {}
    if params:
        data['params'] = params
    
    client = APIClient()
    # Make API request
    try:
        response = client.post(f"/api/functions/{uid}/start", data)
        click.echo(f"Function {uid} started successfully")
    except Exception as e:
        click.echo(f"Error starting function: {str(e)}")

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

@fn_cli.command(name="delete")
@click.argument("uid")
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
def delete_function(uid, force):
    """Delete a function"""
    try:
        if not force:
            # Get function details first
            client = APIClient()
            try:
                function = client.get(f"/api/functions/{uid}")
                click.echo(f"You are about to delete function: {function['name']} ({uid})")
            except Exception:
                click.echo(f"You are about to delete function with UID: {uid}")
            
            # Ask for confirmation
            if not click.confirm("Are you sure you want to delete this function?"):
                click.echo("Operation cancelled.")
                return
        
        client = APIClient()
        response = client.delete(f"/api/functions/{uid}")
        click.echo(response["message"])
    except Exception as e:
        click.echo(f"Error: {str(e)}") 