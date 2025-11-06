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

import inspect
import json
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel

from camel.logger import get_logger
from camel.runtimes import BaseRuntime
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class DaytonaRuntime(BaseRuntime):
    r"""A runtime that executes functions in a Daytona sandbox environment.
    Requires the Daytona server to be running and an API key configured.

    Args:
        api_key (Optional[str]): The Daytona API key for authentication. If not
            provided, it will try to use the DAYTONA_API_KEY environment
            variable. (default: :obj:`None`)
        api_url (Optional[str]): The URL of the Daytona server. If not
            provided, it will try to use the DAYTONA_API_URL environment
            variable. If none is provided, it will use "http://localhost:8000".
            (default: :obj:`None`)
        language (Optional[str]): The programming language for the sandbox.
            (default: :obj:`"python"`)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        language: Optional[str] = "python",
    ):
        from daytona_sdk import Daytona, DaytonaConfig, Sandbox

        super().__init__()
        self.api_key = api_key or os.environ.get('DAYTONA_API_KEY')
        self.api_url = api_url or os.environ.get('DAYTONA_API_URL')
        self.language = language
        self.config = DaytonaConfig(api_key=self.api_key, api_url=self.api_url)
        self.daytona = Daytona(self.config)
        self.sandbox: Optional[Sandbox] = None
        self.entrypoint: Dict[str, str] = dict()

    def build(self) -> "DaytonaRuntime":
        r"""Create and start a Daytona sandbox.

        Returns:
            DaytonaRuntime: The current runtime.
        """
        from daytona_sdk import CreateSandboxBaseParams

        try:
            params = CreateSandboxBaseParams(language=self.language)
            self.sandbox = self.daytona.create(params)
            if self.sandbox is None:
                raise RuntimeError("Failed to create sandbox.")
            logger.info(f"Sandbox created with ID: {self.sandbox.id}")
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e!s}")
            raise RuntimeError(f"Daytona sandbox creation failed: {e!s}")
        return self

    def _cleanup(self):
        r"""Clean up the sandbox when exiting."""
        if self.sandbox:
            try:
                self.daytona.delete(self.sandbox)
                logger.info(f"Sandbox {self.sandbox.id} removed")
                self.sandbox = None
            except Exception as e:
                logger.error(f"Failed to remove sandbox: {e!s}")

    def add(
        self,
        funcs: Union[FunctionTool, List[FunctionTool]],
        entrypoint: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> "DaytonaRuntime":
        r"""Add a function or list of functions to the runtime.

        Args:
            funcs (Union[FunctionTool, List[FunctionTool]]): The function or
                list of functions to add.
            entrypoint (str): The entrypoint for the function.
            arguments (Optional[Dict[str, Any]]): The arguments for the
                function. (default: :obj:`None`)

        Returns:
            DaytonaRuntime: The current runtime.
        """
        if not isinstance(funcs, list):
            funcs = [funcs]
        if arguments is not None:
            entrypoint += json.dumps(arguments, ensure_ascii=False)

        def make_wrapper(inner_func: Callable, func_name: str, func_code: str):
            r"""Creates a wrapper for a function to execute it in the
            Daytona sandbox.

            Args:
                inner_func (Callable): The function to wrap.
                func_name (str): The name of the function.
                func_code (str): The source code of the function.

            Returns:
                Callable: A wrapped function that executes in the sandbox.
            """

            @wraps(inner_func)
            def wrapper(*args, **kwargs):
                if not self.sandbox:
                    raise RuntimeError(
                        "Sandbox not initialized. Call build() first."
                    )

                try:
                    for key, value in kwargs.items():
                        if isinstance(value, BaseModel):
                            kwargs[key] = value.model_dump()
                    args_str = json.dumps(args, ensure_ascii=True)
                    kwargs_str = json.dumps(kwargs, ensure_ascii=True)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to serialize arguments: {e!s}")
                    return {"error": f"Argument serialization failed: {e!s}"}

                # Upload function code to the sandbox
                script_path = f"/home/daytona/{func_name}.py"
                try:
                    self.sandbox.fs.upload_file(
                        script_path, func_code.encode()
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to upload function {func_name}: {e!s}"
                    )
                    return {"error": f"Upload failed: {e!s}"}

                exec_code = (
                    f"import sys\n"
                    f"sys.path.append('/home/daytona')\n"
                    f"import json\n"
                    f"from {func_name} import {func_name}\n"
                    f"args = json.loads('{args_str}')\n"
                    f"kwargs = json.loads('{kwargs_str}')\n"
                    f"result = {func_name}(*args, **kwargs)\n"
                    f"print(json.dumps(result) if result is not "
                    f"None else 'null')"
                )

                # Execute the function in the sandbox
                try:
                    response = self.sandbox.process.code_run(exec_code)
                    return (
                        json.loads(response.result)
                        if response.result
                        else None
                    )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to decode JSON response for {func_name}"
                    )
                    return {"error": f"JSON decoding failed: {e!s}"}
                except Exception as e:
                    logger.error(
                        f"Failed to execute function {func_name}: {e!s}"
                    )
                    return {"error": f"Execution failed: {e!s}"}

            return wrapper

        for func in funcs:
            inner_func = func.func
            func_name = func.get_function_name()
            func_code = inspect.getsource(inner_func).strip()

            func.func = make_wrapper(inner_func, func_name, func_code)
            self.tools_map[func_name] = func
            self.entrypoint[func_name] = entrypoint

        return self

    def info(self) -> str:
        r"""Get information about the current sandbox.

        Returns:
            str: Information about the sandbox.

        Raises:
            RuntimeError: If the sandbox is not initialized.
        """
        if self.sandbox is None:
            raise RuntimeError("Sandbox not initialized.")
        return (
            f"Sandbox {self.sandbox.id}:\n"
            f"State: {self.sandbox.state}\n"
            f"Resources: {self.sandbox.cpu} CPU, {self.sandbox.memory} RAM"
        )

    def __del__(self):
        r"""Clean up the sandbox when the object is deleted."""
        if hasattr(self, 'sandbox'):
            self._cleanup()

    def stop(self) -> "DaytonaRuntime":
        r"""Stop and remove the sandbox.

        Returns:
            DaytonaRuntime: The current runtime.
        """
        self._cleanup()
        return self

    def reset(self) -> "DaytonaRuntime":
        r"""Reset the sandbox by stopping and rebuilding it.

        Returns:
            DaytonaRuntime: The current runtime.
        """
        return self.stop().build()

    @property
    def docs(self) -> str:
        r"""Get the URL for the Daytona API documentation.

        Returns:
            str: The URL for the API documentation.
        """
        return "https://www.daytona.io/docs/python-sdk/daytona/"
