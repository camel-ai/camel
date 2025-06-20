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
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Union


class BaseInterpreter(ABC):
    r"""An abstract base class for code interpreters."""

    @abstractmethod
    def run(self, code: str, code_type: str) -> str:
        r"""Executes the given code based on its type.

        Args:
            code (str): The code to be executed.
            code_type (str): The type of the code, which must be one of the
                types returned by `supported_code_types()`.

        Returns:
            str: The result of the code execution. If the execution fails, this
                should include sufficient information to diagnose and correct
                the issue.

        Raises:
            InterpreterError: If the code execution encounters errors that
                could be resolved by modifying or regenerating the code.
        """
        pass

    @abstractmethod
    def supported_code_types(self) -> List[str]:
        r"""Provides supported code types by the interpreter."""
        pass

    @abstractmethod
    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""Updates action space for *python* interpreter"""
        pass

    @abstractmethod
    def execute_command(self, command: str) -> Union[str, Tuple[str, str]]:
        r"""Executes a command in the interpreter.

        Args:
            command (str): The command to execute.

        Returns:
            Tuple[str, str]: A tuple containing the stdout and stderr of the
                command execution.
        """
        pass
