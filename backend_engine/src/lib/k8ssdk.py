import os
import yaml
import logging
import tempfile
import subprocess
from string import Template
from pathlib import Path

logger = logging.getLogger(__name__)

class K8sDeployer:
    """Class for deploying resources to Kubernetes"""
    
    def __init__(self, namespace="default"):
        """Initialize the deployer with a namespace"""
        self.namespace = namespace
        self.template_dir = Path(__file__).parent.parent
    
    def deploy_worker(self, worker):
        """Deploy a worker to Kubernetes"""
        try:
            # Load the worker template
            template_path = self.template_dir / "worker_template.yaml"
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Prepare template variables
            cpu_request = worker["cpu_total"] * 0.8  # Request 80% of total CPU
            memory_request = int(worker["memory_total"] * 0.8)  # Request 80% of total memory
            
            # Add GPU limit if GPU is available
            gpu_limit = ""
            if worker.get("gpu_id"):
                gpu_limit = f'nvidia.com/gpu: "1"'
            
            # Get docker image from spec
            docker_image = worker.get("spec", {}).get("docker_image", "python:3.11-slim")
            
            # Prepare template variables with vinci4dworker prefix
            worker_name = f"vinci4dworker-{worker['name']}"
            
            template_vars = {
                "WORKER_NAME": worker_name,
                "WORKER_UID": worker["uid"],
                "GRID_UID": worker["grid_uid"],
                "NAMESPACE": self.namespace,
                "DOCKER_IMAGE": docker_image,
                "CPU_REQUEST": str(cpu_request),
                "CPU_LIMIT": str(worker["cpu_total"]),
                "MEMORY_REQUEST": str(memory_request),
                "MEMORY_LIMIT": str(worker["memory_total"]),
                "GPU_LIMIT": gpu_limit,
                "BACKEND_ENGINE_URL": os.environ.get("BACKEND_ENGINE_URL", "http://backend-engine:8000"),
                "LOGSTORE_URL": os.environ.get("LOGSTORE_URL", "http://logstore:8000"),
                "ARTIFACTORY_URL": os.environ.get("ARTIFACTORY_URL", "http://artifactory:8000")
            }
            
            # Apply template
            template = Template(template_content)
            manifest = template.substitute(template_vars)
            
            # Write manifest to temporary file
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
                tmp.write(manifest.encode())
                tmp_path = tmp.name
            
            # Apply manifest using kubectl
            result = subprocess.run(
                ["kubectl", "apply", "-f", tmp_path],
                capture_output=True,
                text=True
            )
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            if result.returncode != 0:
                logger.error(f"Failed to deploy worker: {result.stderr}")
                return False
            
            logger.info(f"Worker {worker['uid']} deployed successfully as {worker_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error deploying worker: {e}")
            return False
    
    def delete_worker(self, worker_uid, worker_name=None):
        """Delete a worker from Kubernetes"""
        try:
            # If worker_name is provided, use it to construct the StatefulSet name
            # Otherwise, use the worker_uid
            if worker_name:
                statefulset_name = f"vinci4dworker-{worker_name}"
            else:
                statefulset_name = f"vinci4dworker-worker-{worker_uid}"
            
            # Delete the StatefulSet
            result = subprocess.run(
                ["kubectl", "delete", "statefulset", statefulset_name, "-n", self.namespace],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 and "not found" not in result.stderr:
                logger.error(f"Failed to delete worker StatefulSet: {result.stderr}")
                return False
            
            # Delete the Service
            result = subprocess.run(
                ["kubectl", "delete", "service", statefulset_name, "-n", self.namespace],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 and "not found" not in result.stderr:
                logger.error(f"Failed to delete worker Service: {result.stderr}")
                return False
            
            logger.info(f"Worker {worker_uid} deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting worker: {e}")
            return False
