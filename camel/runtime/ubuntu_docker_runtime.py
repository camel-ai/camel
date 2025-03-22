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

from camel.runtime.docker_runtime import DockerRuntime
from camel.toolkits import FunctionTool

logger = logging.getLogger(__name__)


class UbuntuDockerRuntime(DockerRuntime):
    r"""A specialized Docker runtime for Ubuntu-based environments.

    This runtime includes specific configurations and setup for Ubuntu
    containers,including proper Python path handling and environment setup.
    """

    def __init__(
        self,
        image: str,
        port: int = 0,
        remove: bool = True,
        python_path: str = "/usr/bin/python3",
        **kwargs,
    ):
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
                logger.info(
                    f"No command attribute found"
                    f"for function {func.get_function_name()}"
                )

        super().add(funcs, entrypoint, redirect_stdout, arguments)

        return self

    def _setup_default_mounts(self):
        """Setup default volume mounts for the container."""
        # Add any default mounts needed for Ubuntu environment
        pass

    def build(self, time_out: int = 15) -> "UbuntuDockerRuntime":
        """Build and initialize the Ubuntu container with proper setup."""
        logger.info("Starting container build...")

        super().build(time_out=time_out)

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
                    "PYTHON_EXECUTABLE": self.python_path,
                },
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
            local_file_path: Path to the Python file on the local filesystem.
            container_path: Path where the file should be copied
            in the container.If None, the file will be copied to /tmp/
            args: List of command-line arguments to pass to the Python script.
            env: Additional environment variables to set for the execution.
            callback: Optional function to process each line of output.
                     If None, output is printed to stdout.
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
        with open(local_path, 'rb'):
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
        if env:
            execution_env.update(env)

        logger.info(f"Executing Python file with command: {cmd}")

        # 始终使用流式输出
        exec_result = self.container.exec_run(
            cmd,
            environment=execution_env,
            stream=True,
            demux=True,  # 分离stdout和stderr
        )

        # 处理输出流
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
            # 可以考虑添加停止容器内进程的逻辑
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            raise

    def _create_archive_from_file(self, file_path: Union[str, Path]) -> bytes:
        """Create a tar archive from a single file for docker.put_archive().

        Args:
            file_path: Path to the file to archive

        Returns:
            Bytes of the tar archive
        """
        import io
        import tarfile

        file_path = Path(file_path)
        tar_stream = io.BytesIO()

        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tar.add(file_path, arcname=file_path.name)

        tar_stream.seek(0)
        return tar_stream.read()
