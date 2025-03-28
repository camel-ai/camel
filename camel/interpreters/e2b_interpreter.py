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
import os
from typing import Any, ClassVar, Dict, List, Optional

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.interpreter_error import InterpreterError
from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class E2BInterpreter(BaseInterpreter):
    r"""E2B Code Interpreter implementation.

    Args:
        require_confirm (bool, optional): If True, prompt user before running
            code strings for security. (default: :obj:`True`)
    """

    _CODE_TYPE_MAPPING: ClassVar[Dict[str, Optional[str]]] = {
        "python": None,
        "py3": None,
        "python3": None,
        "py": None,
        "shell": "bash",
        "bash": "bash",
        "sh": "bash",
        "java": "java",
        "javascript": "js",
        "r": "r",
    }

    @api_keys_required(
        [
            (None, "E2B_API_KEY"),
        ]
    )
    def __init__(
        self,
        require_confirm: bool = True,
    ) -> None:
        from e2b_code_interpreter import Sandbox

        self.require_confirm = require_confirm
        self._sandbox = Sandbox(api_key=os.environ.get("E2B_API_KEY"))

    def __del__(self) -> None:
        r"""Destructor for the E2BInterpreter class.

        This method ensures that the e2b sandbox is killed when the
        interpreter is deleted.
        """
        if (
            hasattr(self, '_sandbox')
            and self._sandbox is not None
            and self._sandbox.is_running()
        ):
            self._sandbox.kill()

    def run(
        self,
        code: str,
        code_type: str,
    ) -> str:
        r"""Executes the given code in the e2b sandbox.

        Args:
            code (str): The code string to execute.
            code_type (str): The type of code to execute (e.g., 'python',
                'bash').

        Returns:
            str: The string representation of the output of the executed code.

        Raises:
            InterpreterError: If the `code_type` is not supported or if any
                runtime error occurs during the execution of the code.
        """
        if code_type not in self._CODE_TYPE_MAPPING:
            raise InterpreterError(
                f"Unsupported code type {code_type}. "
                f"`{self.__class__.__name__}` only supports "
                f"{', '.join(list(self._CODE_TYPE_MAPPING.keys()))}."
            )
        # Print code for security checking
        if self.require_confirm:
            logger.info(
                f"The following {code_type} code will run on your "
                f"e2b sandbox: {code}"
            )
            while True:
                choice = input("Running code? [Y/n]:").lower()
                if choice in ["y", "yes", "ye"]:
                    break
                elif choice not in ["no", "n"]:
                    continue
                raise InterpreterError(
                    "Execution halted: User opted not to run the code. "
                    "This choice stops the current operation and any "
                    "further code execution."
                )

        if self._CODE_TYPE_MAPPING[code_type] is None:
            execution = self._sandbox.run_code(code)
        else:
            execution = self._sandbox.run_code(
                code=code, language=self._CODE_TYPE_MAPPING[code_type]
            )

        if execution.text and execution.text.lower() != "none":
            return execution.text

        if execution.logs:
            if execution.logs.stdout:
                return ",".join(execution.logs.stdout)
            elif execution.logs.stderr:
                return ",".join(execution.logs.stderr)

        return str(execution.error)

    def supported_code_types(self) -> List[str]:
        r"""Provides supported code types by the interpreter."""
        return list(self._CODE_TYPE_MAPPING.keys())

    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""Updates action space for *python* interpreter"""
        raise RuntimeError("E2B doesn't support " "`action_space`.")
