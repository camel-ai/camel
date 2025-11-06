# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import logging
import sys
import time
from pathlib import Path
from typing import Callable, List, Optional, Union

from camel.runtimes.docker_runtime import DockerRuntime
from camel.toolkits import FunctionTool

logger = logging.getLogger(__name__)


class UbuntuDockerRuntime(DockerRuntime):
    r"""A specialized Docker runtime for Ubuntu-based environments.

    This runtime includes specific configurations and setup for Ubuntu
    containers, including proper Python path handling and environment setup.
    It provides methods for executing Python files, managing the container
    lifecycle, and handling file operations within the Ubuntu container.

    Attributes:
        python_path (str): Path to the Python interpreter in the container
        docker_config (dict): Configuration dict for Docker container setup
    """

    def __init__(
        self,
        image: str,
        port: int = 0,
        remove: bool = True,
        python_path: str = "/usr/bin/python3",
        **kwargs,
    ):
        r"""Initialize the Ubuntu Docker Runtime.

        Args:
            image (str): Docker image name to use
            port (int, optional): Port to expose. Defaults to 0 (random port)
            remove (bool, optional): Whether to remove container after use.
                                   Defaults to True
            python_path (str, optional): Path to Python interpreter.
                                       Defaults to "/usr/bin/python3"
            **kwargs: Additional arguments passed to DockerRuntime
        """
        super().__init__(image=image, port=port, remove=remove, **kwargs)

        self.python_path = python_path
        logger.info(
            f"Initializing UbuntuDockerRuntime with python_path: {python_path}"
        )

        # Set default environment variables for Ubuntu
        self.docker_config.setdefault("environment", {})
        self.docker_config["environment"].update(
            {
                "PYTHON_PATH": python_path,
                "PYTHON_EXECUTABLE": python_path,
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONUNBUFFERED": "1",
            }
        )
        logger.info(
            f"Environment variables set: {self.docker_config['environment']}"
        )

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
        r"""Add functions to the runtime with Ubuntu-specific modifications.

        Args:
            funcs: Function(s) to add to the runtime
            entrypoint: Entry point for function execution
            redirect_stdout: Whether to redirect stdout
            arguments: Optional arguments for function execution

        Returns:
            Self for method chaining
        """
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
                logger.info(
                    f"No command attribute found for function "
                    f"{func.get_function_name()}"
                )

        super().add(funcs, entrypoint, redirect_stdout, arguments)
        return self

    def _setup_default_mounts(self):
        r"""Setup default volume mounts for the container.

        This method can be extended to add Ubuntu-specific volume mounts.
        """
        pass

    def build(self, time_out: int = 15) -> "UbuntuDockerRuntime":
        r"""Build and initialize the Ubuntu container with proper setup.

        Args:
            time_out (int): Timeout in seconds for build operation

        Returns:
            Self for method chaining
        """
        logger.info("Starting container build...")

        super().build(time_out=time_out)

        if self.container:
            logger.info("Container built successfully, verifying setup...")

            # Verify Python installation
            exit_code, output = self.container.exec_run(
                [self.python_path, "--version"]
            )
            logger.info(f"Python version check result: {output.decode()}")
            if exit_code != 0:
                logger.error(
                    f"Python version check failed with exit code {exit_code}"
                )
                raise RuntimeError(
                    f"Python installation verification "
                    f"failed: {output.decode()}"
                )

            # Install required packages
            logger.info("Installing required packages...")
            exit_code, output = self.container.exec_run("apt-get update")
            if exit_code != 0:
                logger.error(
                    f"apt-get update failed with "
                    f"exit code {exit_code}: {output.decode()}"
                )
                raise RuntimeError(
                    f"Failed to update package lists: {output.decode()}"
                )

            exit_code, output = self.container.exec_run(
                "apt-get install -y curl"
            )
            if exit_code != 0:
                logger.error(
                    f"apt-get install curl failed with "
                    f"exit code {exit_code}: {output.decode()}"
                )
                raise RuntimeError(
                    f"Failed to install curl: {output.decode()}"
                )

            # Start API server with explicit Python path
            logger.info("Starting API server...")
            exec_result = self.container.exec_run(
                [self.python_path, "/home/api.py"],
                detach=True,
                environment={
                    "PYTHONPATH": str(
                        Path(self.python_path).parent
                        / "lib/python3.10/site-packages"
                    ),
                    "PYTHON_EXECUTABLE": self.python_path,
                },
            )
            logger.info("API server start result: %s", exec_result)

            # Wait for API server to start
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    exit_code, curl_result = self.container.exec_run(
                        "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs"
                    )
                    status_code = curl_result.decode().strip()
                    if exit_code == 0 and status_code.startswith('2'):
                        logger.info(
                            f"API server is running "
                            f"(status code: {status_code})"
                        )
                        break
                    else:
                        logger.debug(
                            f"API server not ready yet (status: {status_code})"
                        )
                except Exception as e:
                    logger.debug("Waiting for API server... %s", e)
                time.sleep(0.5)
            else:
                logger.warning("API server may not be running properly")

        return self

    def exec_python_file(
        self,
        local_file_path: str,
        container_path: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[dict] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        r"""Execute a Python file inside the Docker container.

        Args:
            local_file_path: Path to the Python file on the local filesystem
            container_path: Path where the file should be copied in the
            container If None, the file will be copied to /tmp/
            args: List of command-line arguments to pass to the Python script
            env: Additional environment variables to set for the execution
            callback: Optional function to process each line of output
                     If None, output is printed to stdout

        Raises:
            RuntimeError: If container is not running
            FileNotFoundError: If Python file is not found
        """
        if not self.container:
            raise RuntimeError("Container is not running. Call build() first.")

        local_path = Path(local_file_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Python file {local_file_path} not found")

        # Determine where to put the file in the container
        if container_path is None:
            container_path = f"/tmp/{local_path.name}"

        logger.info(
            f"Copying {local_file_path} to container at {container_path}"
        )

        # Copy the file to the container
        self.container.put_archive(
            path=str(Path(container_path).parent),
            data=self._create_archive_from_file(local_path),
        )

        # Prepare command
        cmd = [self.python_path, container_path]
        if args:
            cmd.extend(args)

        # Prepare environment
        execution_env = {
            "PYTHONPATH": "/usr/local/lib/python3.10/site-packages",
            "PYTHON_EXECUTABLE": self.python_path,
        }
        execution_env["PYTHONPATH"] = str(
            Path(self.python_path).parent / "lib/python3.10/site-packages"
        )
        if env:
            execution_env.update(env)

        logger.info(f"Executing Python file with command: {cmd}")

        # Always use streaming output
        exec_result = self.container.exec_run(
            cmd,
            environment=execution_env,
            stream=True,
            demux=True,  # Separate stdout and stderr
        )

        # Handle output streams
        try:
            for stdout, stderr in exec_result[1]:
                if stdout:
                    output = stdout.decode('utf-8')
                    if callback:
                        callback(output)
                    else:
                        print(output, end='')

                if stderr:
                    error = stderr.decode('utf-8')
                    if callback:
                        callback(f"ERROR: {error}")
                    else:
                        print(f"ERROR: {error}", end='', file=sys.stderr)
        except KeyboardInterrupt:
            logger.info("Execution interrupted by user")
            # Could add logic to stop container processes here
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            raise

    def _create_archive_from_file(self, file_path: Union[str, Path]) -> bytes:
        r"""Create a tar archive from a single file for docker.put_archive().

        Args:
            file_path: Path to the file to archive

        Returns:
            bytes: The tar archive as bytes
        """
        import io
        import tarfile

        file_path = Path(file_path)
        tar_stream = io.BytesIO()

        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tar.add(file_path, arcname=file_path.name)

        tar_stream.seek(0)
        return tar_stream.read()
