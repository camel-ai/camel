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

import queue
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.interpreter_error import InterpreterError

if TYPE_CHECKING:
    from jupyter_client import BlockingKernelClient, KernelManager

TIMEOUT = 30


class JupyterKernelInterpreter(BaseInterpreter):
    r"""A class for executing code strings in a Jupyter Kernel.

    Args:
        require_confirm (bool, optional): If `True`, prompt user before
            running code strings for security. Defaults to `True`.
        print_stdout (bool, optional): If `True`, print the standard
            output of the executed code. Defaults to `False`.
        print_stderr (bool, optional): If `True`, print the standard error
            of the executed code. Defaults to `True`.
    """

    def __init__(
        self,
        require_confirm: bool = True,
        print_stdout: bool = False,
        print_stderr: bool = True,
    ) -> None:
        self.require_confirm = require_confirm
        self.print_stdout = print_stdout
        self.print_stderr = print_stderr

        self.kernel_manager: Optional[KernelManager] = None
        self.client: Optional[BlockingKernelClient] = None

    def __del__(self) -> None:
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()
        if self.client:
            self.client.stop_channels()

    def _initialize_if_needed(self) -> None:
        if self.kernel_manager is not None:
            return

        from jupyter_client.manager import start_new_kernel

        self.kernel_manager, self.client = start_new_kernel()

    @staticmethod
    def _clean_ipython_output(output: str) -> str:
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', output)

    def _execute(self, code: str, timeout: float) -> str:
        outputs = []
        if self.kernel_manager is None or self.client is None:
            raise InterpreterError("jupyter client is not initialized.")
        self.client.execute(code)
        msg = self.client.get_iopub_msg(timeout=timeout)
        msg_content = msg["content"]

        if msg_content.get("execution_state", None) == "idle":
            return ""

        # continue polling the message
        result_msg = msg
        while True:
            result_msg = msg
            try:
                msg = self.client.get_iopub_msg(timeout=timeout)
                if msg["content"].get("execution_state", None) == "idle":
                    break
            except queue.Empty:
                outputs.append("Time out")
                break

        msg_type = result_msg.get("msg_type", None)
        if msg_type == "error":
            traceback = "\n".join(result_msg["content"]["traceback"])
            print(result_msg["content"].keys())
            print(result_msg["content"])
            outputs.append(traceback)
        elif msg_type == "stream":
            outputs.append(result_msg["content"]["text"])
        elif msg_type in ["execute_result", "display_data"]:
            outputs.append(result_msg["content"]["data"]["text/plain"])
            if "image/png" in result_msg["content"]["data"]:
                outputs.append(
                    f"\n![image](data:image/png;base64,{result_msg['content']['data']['image/png']})\n"
                )
        else:
            pass
        exec_result = "\n".join(outputs)

        exec_result = self._clean_ipython_output(exec_result)
        return exec_result

    def run(self, code: str, code_type: str) -> str:
        self._initialize_if_needed()
        if code_type == "bash":
            code = f"%%bash\n({code})"
        return self._execute(code, timeout=TIMEOUT)

    def supported_code_types(self) -> List[str]:
        r"""Provides supported code types by the interpreter."""
        return ["python", "bash"]

    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""Updates action space for *python* interpreter"""
        raise RuntimeError(
            "SubprocessInterpreter doesn't support " "`action_space`."
        )
