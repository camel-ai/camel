# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import io
import shlex
import tarfile
import uuid
from pathlib import Path
from typing import Any, ClassVar, Dict, List, TYPE_CHECKING

import docker
from colorama import Fore

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.interpreter_error import InterpreterError

if TYPE_CHECKING:
    from docker.models.containers import Container


class DockerInterpreter(BaseInterpreter):
    r"""A class for executing code files or code strings in a docker container.

    This class handles the execution of code in different scripting languages
    (currently Python and Bash) within a docker container, capturing their
    stdout and stderr streams, and allowing user checking before executing code
    strings.
    """

    _CODE_EXECUTE_CMD_MAPPING: ClassVar[Dict[str, str]] = {
        "python": "python {file_name}",
        "bash": "bash {file_name}",
    }

    _CODE_EXTENSION_MAPPING: ClassVar[Dict[str, str]] = {
        "python": "py",
        "bash": "sh",
    }

    _CODE_TYPE_MAPPING: ClassVar[Dict[str, str]] = {
        "python": "python",
        "py3": "python",
        "python3": "python",
        "py": "python",
        "shell": "bash",
        "bash": "bash",
        "sh": "bash",
    }

    def __init__(
            self,
            require_confirm: bool = True,
            print_stdout: bool = False,
            print_stderr: bool = True,
    ) -> None:
        """Initializes a DockerInterpreter class with one docker container
        attached to it. All the code execution will be done in this container.

        Args:
            require_confirm (bool, optional): If True, prompt user before
                running code strings for security. (default: True)
            print_stdout (bool, optional): If True, print the standard
                output of the executed code. (default: False)
            print_stderr (bool, optional): If True, print the standard error
                of the executed code. (default: True)
        """
        self._require_confirm = require_confirm
        self._print_stdout = print_stdout
        self._print_stderr = print_stderr
        # create a docker container
        self._client = docker.from_env()

    def _create_new_container(self) -> Container:
        name = f"camel-interpreter-{uuid.uuid4()}"
        return self._client.containers.run(
            "python:3.10",
            detach=True,
            name=name,
            command="tail -f /dev/null",
        )

    def _create_file_in_container(self, content: str,
                                  container: Container) -> Path:
        # get a random name for the file
        filename = str(uuid.uuid4())
        # create a tar in memory
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content.encode('utf-8')))
        tar_stream.seek(0)
        # copy the tar into the container
        container.put_archive("/tmp", tar_stream)
        return Path(f"/tmp/{filename}")

    def _run_file_in_container(
            self,
            container: Container,
            file: Path,
            code_type: str,
    ) -> str:
        code_type = self._check_code_type(code_type)
        commands = shlex.split(
            self._CODE_EXECUTE_CMD_MAPPING[code_type].format(
                file_name=str(file)
            )
        )
        exec_result = container.exec_run(commands, stdout=self._print_stdout,
                                         stderr=self._print_stderr, demux=True)
        stdout, stderr = exec_result.output

        if self._print_stdout and stdout:
            print("======stdout======")
            print(Fore.GREEN + stdout.decode() + Fore.RESET)
            print("==================")
        if self._print_stderr and stderr:
            print("======stderr======")
            print(Fore.RED + stderr.decode() + Fore.RESET)
            print("==================")
        exec_result = f"{stdout.decode()}"
        exec_result += f"(stderr: {stderr.decode()})" if stderr else ""
        return exec_result

    def run(
            self,
            code: str,
            code_type: str,
    ) -> str:
        r"""Creates a temporary container, executes the given code in it, and
        captures the stdout and stderr streams. The container is removed after
        the code execution.

        Args:
            code (str): The code string to execute.
            code_type (str): The type of code to execute (e.g., 'python',
                'bash').

        Returns:
            str: A string containing the captured stdout and stderr of the
                executed code.

        Raises:
            InterpreterError: If the user declines to run the code or if the
                code type is unsupported.
        """
        code_type = self._check_code_type(code_type)

        # Print code for security checking
        if self._require_confirm:
            print(f"The following {code_type} code will run on your computer:")
            print(Fore.CYAN + code + Fore.RESET)
            while True:
                choice = input("Running code? [Y/n]:").lower()
                if choice in ["y", "yes", "ye", ""]:
                    break
                elif choice in ["no", "n"]:
                    raise InterpreterError(
                        "Execution halted: User opted not to run the code. "
                        "This choice stops the current operation and any "
                        "further code execution."
                    )

        container = None
        try:
            container = self._create_new_container()
            temp_file_path = self._create_file_in_container(code, container)
            result = self._run_file_in_container(container, temp_file_path,
                                                 code_type)
        except Exception as e:
            raise InterpreterError(
                f"Execution halted: {e}. "
                "This choice stops the current operation and any "
                "further code execution."
            ) from e
        finally:
            if container:
                container.remove(force=True)
        return result

    def _check_code_type(self, code_type: str) -> str:
        if code_type not in self._CODE_TYPE_MAPPING:
            raise InterpreterError(
                f"Unsupported code type {code_type}. Currently "
                f"`{self.__class__.__name__}` only supports "
                f"{', '.join(self._CODE_EXTENSION_MAPPING.keys())}."
            )
        return self._CODE_TYPE_MAPPING[code_type]

    def supported_code_types(self) -> List[str]:
        r"""Provides supported code types by the interpreter."""
        return list(self._CODE_EXTENSION_MAPPING.keys())

    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""Updates action space for *python* interpreter"""
        raise RuntimeError(
            "SubprocessInterpreter doesn't support " "`action_space`."
        )
