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
from typing import List, Literal, Optional, Union

from camel.interpreters import (
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    JupyterKernelInterpreter,
    MicrosandboxInterpreter,
    SubprocessInterpreter,
)
from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class CodeExecutionToolkit(BaseToolkit):
    r"""A toolkit for code execution.

    Args:
        sandbox (str): The environment type used to execute code.
            (default: `subprocess`)
        verbose (bool): Whether to print the output of the code execution.
            (default: :obj:`False`)
        unsafe_mode (bool):  If `True`, the interpreter runs the code
            by `eval()` without any security check. (default: :obj:`False`)
        import_white_list (Optional[List[str]]): A list of allowed imports.
            (default: :obj:`None`)
        require_confirm (bool): Whether to require confirmation before
            executing code. (default: :obj:`False`)
        timeout (Optional[float]): General timeout for toolkit operations.
            (default: :obj:`None`)
        microsandbox_config (Optional[dict]): Configuration for microsandbox
            interpreter. Available keys: 'server_url', 'api_key',
            'namespace', 'sandbox_name', 'timeout'.
            If None, uses default configuration. (default: :obj:`None`)
    """

    def __init__(
        self,
        sandbox: Literal[
            "internal_python",
            "jupyter",
            "docker",
            "subprocess",
            "e2b",
            "microsandbox",
        ] = "subprocess",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
        timeout: Optional[float] = None,
        # Microsandbox configuration dictionary
        microsandbox_config: Optional[dict] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.verbose = verbose
        self.unsafe_mode = unsafe_mode
        self.import_white_list = import_white_list or list()

        # Type annotation for interpreter to allow all possible types
        self.interpreter: Union[
            InternalPythonInterpreter,
            JupyterKernelInterpreter,
            DockerInterpreter,
            SubprocessInterpreter,
            E2BInterpreter,
            MicrosandboxInterpreter,
        ]

        if sandbox == "internal_python":
            self.interpreter = InternalPythonInterpreter(
                unsafe_mode=self.unsafe_mode,
                import_white_list=self.import_white_list,
            )
        elif sandbox == "jupyter":
            self.interpreter = JupyterKernelInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "docker":
            self.interpreter = DockerInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "subprocess":
            self.interpreter = SubprocessInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "e2b":
            self.interpreter = E2BInterpreter(require_confirm=require_confirm)
        elif sandbox == "microsandbox":
            # Extract parameters with proper types for microsandbox
            config = microsandbox_config or {}

            self.interpreter = MicrosandboxInterpreter(
                require_confirm=require_confirm,
                server_url=config.get("server_url"),
                api_key=config.get("api_key"),
                namespace=config.get("namespace", "default"),
                sandbox_name=config.get("sandbox_name"),
                timeout=config.get("timeout", 30),
            )
        else:
            raise RuntimeError(
                f"The sandbox type `{sandbox}` is not supported."
            )

    def execute_code(self, code: str, code_type: str = "python") -> str:
        r"""Execute a given code snippet.

        Args:
            code (str): The input code to the Code Interpreter tool call.
            code_type (str): The type of the code to be executed
                (e.g. node.js, python, etc). (default: obj:`python`)

        Returns:
            str: The text output from the Code Interpreter tool call.
        """
        output = self.interpreter.run(code, code_type)
        content = (
            f"Executed the code below:\n```{code_type}\n{code}\n```\n"
            f"> Executed Results:\n{output}"
        )
        if self.verbose:
            print(content)
        return content

    def execute_command(self, command: str) -> Union[str, tuple[str, str]]:
        r"""Execute a command can be used to resolve the dependency of the
        code. Useful if there's dependency issues when you try to execute code.

        Args:
            command (str): The command to execute.

        Returns:
            Union[str, tuple[str, str]]: The output of the command.
        """
        output = self.interpreter.execute_command(command)
        content = (
            f"Executed the command below:\n```sh\n{command}\n```\n"
            f"> Executed Results:\n{output}"
        )
        if self.verbose:
            print(content)
        return content

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.execute_code),
            FunctionTool(self.execute_command),
        ]
