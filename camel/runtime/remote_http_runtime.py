import atexit
from functools import wraps
import json
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional
from pydantic import BaseModel

import requests
import subprocess
from subprocess import Popen
from camel.runtime import BaseRuntime
from camel.toolkits.function_tool import FunctionTool

logger = logging.getLogger(__name__)

class RemoteHttpRuntime(BaseRuntime):
    r"""A runtime that runs functions in a remote HTTP server.
    You need to run the API server in the remote server first.

    Attributes:
        host (str): The host of the remote server.
        port (int): The port of the remote server.
        python_exec (str): The python executable to run the API server.
    """

    def __init__(self, host: str, port: int = 8000, python_exec: str = "python3"):
        super().__init__()
        self.host = host
        self.port = port
        self.python_exec = python_exec
        self.api_path = Path(__file__).parent / "api.py"
        self.entrypoint: Dict[str, str] = dict()
        self.process: Optional[Popen] = None

    def build(self) -> "RemoteHttpRuntime":
        r"""Build the API server.
        
        Returns:
            RemoteHttpRuntime: The current runtime.
        """
        self.process = subprocess.Popen([self.python_exec, str(self.api_path)] + list(self.entrypoint.values()))
        atexit.register(self._cleanup)
        return self

    def _cleanup(self):
        r"""Clean up the API server when exiting."""

        if self.process and self.process.poll() is None: 
            self.process.terminate()
            self.process.wait()
            self.process = None

    def add(  # type: ignore[override]
        self,
        funcs: FunctionTool | List[FunctionTool],
        entrypoint: str,
        return_stdout: bool = False,
    ) -> "RemoteHttpRuntime":
        r"""Add a function or list of functions to the runtime.

        Args:
            funcs (FunctionTool or List[FunctionTool]): The function or
                list of functions to add.
            entrypoint (str): The entrypoint for the function.
            return_stdout (bool): Whether to return the stdout of the function.

        Returns:
            RemoteHttpRuntime: The current runtime.
        """
        if not isinstance(funcs, list):
            funcs = [funcs]
        if "(" in entrypoint:
            _, params = entrypoint.split("(")
            params = f"dict({params}"
            try:
                _ = eval(params)
            except Exception as e:
                logger.error(f"Error evaluating parameters: {e}")
                raise Exception(
                    "Currently DockerRuntime only supports dict"
                    "parameters for entrypoint."
                )

        for func in funcs:
            inner_func = func.func

            # Create a wrapper that explicitly binds `func`
            @wraps(inner_func)
            def wrapper(
                *args, func=func, return_stdout=return_stdout, **kwargs
            ):
                for key, value in kwargs.items():
                    if isinstance(value, BaseModel):
                        kwargs[key] = value.model_dump()

                resp = requests.post(
                    f"http://{self.host}:{self.port}/{func.get_function_name()}",
                    json=dict(
                        args=args, kwargs=kwargs, return_stdout=return_stdout
                    ),
                )
                if resp.status_code != 200:
                    logger.error(
                        f"""ailed to execute function: 
                        {func.get_function_name()}, 
                        status code: {resp.status_code}, 
                        response: {resp.text}"""
                    )
                    return {
                        "error": f"""Failed to execute function:
                        {func.get_function_name()}, 
                        response: {resp.text}"""
                    }
                data = resp.json()
                if return_stdout:
                    print(data["stdout"])
                return json.loads(data["output"])

            func.func = wrapper
            self.tools_map[func.get_function_name()] = func
        self.entrypoint[func.get_function_name()] = entrypoint

        return self

    @property
    def ok(self) -> bool:
        r"""Check if the API Server is running.

        Returns:
            bool: Whether the API Server is running.
        """
        try:
            _ = requests.get(f"http://{self.host}:{self.port}")
            return True
        except requests.exceptions.ConnectionError:
            return False

    def wait(self, timeout: int = 10) -> bool:
        r"""Wait for the API Server to be ready.

        Args:
            timeout (int): The number of seconds to wait.

        Returns:
            bool: Whether the API Server is ready.
        """
        for _ in range(timeout):
            if self.ok:
                return True
            time.sleep(1)
        return False

    def __del__(self):
        r"""Clean up the API server when the object is deleted."""
        self._cleanup()

    def stop(self) -> "RemoteHttpRuntime":
        r"""Stop the API server.
        
        Returns:
            RemoteHttpRuntime: The current runtime.
        """
        self._cleanup()
        return self

    def reset(self) -> "RemoteHttpRuntime":
        r"""Reset the API server.
        
        Returns:
            RemoteHttpRuntime: The current runtime.
        """
        return self.stop().build()

    @property
    def docs(self) -> str:
        r"""Get the URL for the API documentation.

        Returns:
            str: The URL for the API documentation.
        """
        return f"http://{self.host}:{self.port}/docs"
