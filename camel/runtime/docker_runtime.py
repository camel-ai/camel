import logging
from typing import List

import time
from pydantic import BaseModel
from camel.runtime import BaseRuntime
from camel.toolkits import FunctionTool
from pathlib import Path
from functools import wraps
import os
from random import randint
import requests
import tarfile
import io

logger = logging.getLogger(__name__)


class DockerRuntime(BaseRuntime):
    r"""A class representing a runtime environment using Docker.
    This class automatically wraps functions to be executed in a Docker container.

    Attributes:
        image (str): The name of the Docker image to use for the runtime.
        port (int): The port number to use for the runtime API.
    """

    def __init__(self, image: str, port: int = 8000, remove: bool = True, **kwargs):
        super().__init__()
        
        import docker  # type: ignore[import]
        from docker.types import Mount  # type: ignore[import]

        self.client = docker.from_env()
        self.container = None

        api_path = Path(__file__).parent / "api.py"
        self.mounts = dict()
        self.cp = {api_path: "/home"}
        self.entrypoint = dict()

        self.docker_config = kwargs
        self.image = image
        self.port = port if port > 0 else randint(10000, 20000)
        self.remove = remove

        if not self.client.images.list(name=self.image):
            logger.warning(f"Image {self.image} not found. Pulling from Docker Hub.")
            self.client.images.pull(self.image)

    def mount(self, path: str, mount_path: str) -> "DockerRuntime":
        path, mount_path = Path(path), Path(mount_path)
        assert path.exists(), f"Path {path} does not exist."
        assert path.is_dir(), f"Path {path} is not a directory."
        assert path.is_absolute(), f"Path {path} is not absolute."
        assert mount_path.is_absolute(), f"Mount path {mount_path} is not absolute."

        self.mounts[path] = mount_path
        return self

    def copy(self, source: str, dest: str) -> "DockerRuntime":
        source, dest = Path(source), Path(dest)
        assert source.exists(), f"Source {source} does not exist."

        self.cp[source] = dest
        return self

    def build(self) -> "DockerRuntime":
        if self.container:
            logger.warning("Container already exists. Nothing to build.")
            return self

        import docker  # type: ignore[import]
        from docker.types import Mount  # type: ignore[import]

        mounts = []
        for local_path, mount_path in self.mounts.items():
            mounts.append(
                Mount(target=str(mount_path), source=str(local_path), type="bind")
            )

        container_params = {
            "image": self.image,
            "detach": True,
            "mounts": mounts,
            "command": "sleep infinity",
            ** self.docker_config,  # Add any additional Docker configurations provided
        }
        container_params["ports"] = {"8000/tcp": self.port}
        try:
            self.container = self.client.containers.create(**container_params)
        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to create container: {str(e)}")

        try:
            self.container.start()
            # Wait for the container to start
            while self.container.status != "running":
                self.container.reload()
                logger.info(f"Container status: {self.container.status}")
                time.sleep(1)

        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to start container: {str(e)}")

        # Copy files to the container if specified
        for local_path, container_path in self.cp.items():
            logger.info(f"Copying {local_path} to {container_path}")
            try:
                with io.BytesIO() as tar_stream:
                    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                        tar.add(local_path, arcname=os.path.basename(local_path))
                    tar_stream.seek(0)
                    self.container.put_archive(
                        str(container_path), tar_stream.getvalue()
                    )
            except docker.errors.APIError as e:
                raise RuntimeError(
                    f"Failed to copy file {local_path} to container: {str(e)}"
                )

        exec = ["python3", "api.py", *list(self.entrypoint.values())]

        self.container.exec_run(exec, workdir="/home", detach=True)

        logger.info(f"Container started on port {self.port}")
        return self

    def add(self, funcs: FunctionTool | List[FunctionTool], entrypoint: str) -> "DockerRuntime":
        if not isinstance(funcs, list):
            funcs = [funcs]

        for func in funcs:
            inner_func = func.func

            # Create a wrapper that explicitly binds `func`
            @wraps(inner_func)
            def wrapper(*args, inner_func=inner_func, func=func, **kwargs):
                for key, value in kwargs.items():
                    if isinstance(value, BaseModel):
                        kwargs[key] = value.model_dump()

                resp = requests.post(
                    f"http://localhost:{self.port}/{func.get_function_name()}",
                    json=dict(args=args, kwargs=kwargs),
                )
                if resp.status_code != 200:
                    return {
                        "error": f"Failed to execute function: {func.get_function_name()}"
                    }
                return resp.json()

            func.func = wrapper
            self.tools_map[func.get_function_name()] = func
        self.entrypoint[func.get_function_name()] = entrypoint

        return self

    def reset(self) -> "DockerRuntime":
        return self.stop().build()

    def stop(self, remove: bool | None = None) -> "DockerRuntime":
        if self.container:
            self.container.stop()
            if remove is None:
                remove = self.remove
            if remove:
                logger.info("Removing container.")
                self.container.remove()
            self.container = None
        else:
            logger.warning("No container to stop.")
        return self

    @property
    def ok(self) -> bool:
        if not self.container:
            return False
        try:
            _ = requests.get(f"http://localhost:{self.port}")
            return True
        except requests.exceptions.ConnectionError:
            return False
    
    def wait(self, timeout: int = 10) -> bool:
        for _ in range(timeout):
            if self.ok:
                return True
            time.sleep(1)
        return False
        
    def __enter__(self) -> "DockerRuntime":
        if not self.container:
            return self.build()
        logger.warning("Container already exists. Returning existing container.")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
    
    