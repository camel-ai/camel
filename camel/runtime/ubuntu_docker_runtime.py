from typing import Optional, Union, List
from pathlib import Path
import logging
from camel.runtime.docker_runtime import DockerRuntime
from camel.toolkits import FunctionTool
import time

logger = logging.getLogger(__name__)

class UbuntuDockerRuntime(DockerRuntime):
    """A specialized Docker runtime for Ubuntu-based environments.
    
    This runtime includes specific configurations and setup for Ubuntu containers,
    including proper Python path handling and environment setup.
    """
    
    def __init__(
        self,
        image: str,
        port: int = 8000,
        remove: bool = True,
        python_path: str = "/usr/bin/python3",
        **kwargs
    ):
        super().__init__(image=image, port=port, remove=remove, **kwargs)
        
        self.python_path = python_path
        logger.info(f"Initializing UbuntuDockerRuntime with python_path: {python_path}")
        
        # Set default environment variables for Ubuntu
        self.docker_config.setdefault("environment", {})
        self.docker_config["environment"].update({
            "PYTHON_PATH": python_path,
            "PYTHON_EXECUTABLE": python_path,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONUNBUFFERED": "1"
        })
        logger.info(f"Environment variables set: {self.docker_config['environment']}")
        
        # Add default working directory
        self.docker_config.setdefault("working_dir", "/app")
        
        # Setup default volume mounts
        self._setup_default_mounts()

    def add(
        self,
        funcs: Union[FunctionTool, List[FunctionTool]],
        entrypoint: str,
        redirect_stdout: bool = False,
        arguments: Optional[dict] = None,
    ) -> "UbuntuDockerRuntime":
        """Override add method to modify code execution command."""
        if not isinstance(funcs, list):
            funcs = [funcs]
        
        # Modify the code execution command to use python3
        for func in funcs:
            logger.info(f"Processing function: {func.get_function_name()}")
            if hasattr(func, 'command'):
                logger.info(f"Original command: {func.command}")
                if isinstance(func.command, list):
                    if 'python' in func.command:
                        idx = func.command.index('python')
                        func.command[idx] = self.python_path
                        logger.info(f"Modified command: {func.command}")
            else:
                logger.info(f"No command attribute found for function {func.get_function_name()}")
        
        return super().add(funcs, entrypoint, redirect_stdout, arguments)

    def _setup_default_mounts(self):
        """Setup default volume mounts for the container."""
        # Add any default mounts needed for Ubuntu environment
        pass

    def build(self, time_out: int = 15) -> "UbuntuDockerRuntime":
        """Build and initialize the Ubuntu container with proper setup."""
        logger.info("Starting container build...")
        runtime = super().build(time_out=time_out)
        
        if self.container:
            logger.info("Container built successfully, verifying setup...")
            
            # Verify Python installation
            exit_code, output = self.container.exec_run(
                [self.python_path, "--version"]
            )
            logger.info(f"Python version check result: {output.decode()}")
            
            # Install required packages
            logger.info("Installing required packages...")
            self.container.exec_run("apt-get update")
            self.container.exec_run("apt-get install -y curl")
            
            # Start API server with explicit Python path
            logger.info("Starting API server...")
            exec_result = self.container.exec_run(
                [self.python_path, "/home/api.py"],
                detach=True,
                environment={
                    "PYTHONPATH": "/usr/local/lib/python3.10/site-packages",
                    "PYTHON_EXECUTABLE": self.python_path
                }
            )
            logger.info("API server start result: %s", exec_result)
            
            # Wait for API server to start
            for _ in range(10):
                try:
                    _, curl_result = self.container.exec_run(
                        "curl -s http://localhost:8000/docs"
                    )
                    if curl_result:
                        logger.info("API server is running")
                        break
                except Exception as e:
                    logger.debug("Waiting for API server... %s", e)
                time.sleep(1)
            else:
                logger.warning("API server may not be running properly")
        
        return runtime 