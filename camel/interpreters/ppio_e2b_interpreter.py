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


class PPIOE2BInterpreter(BaseInterpreter):
    r"""PPIO Agent E2B兼容沙箱解释器实现。

    这个解释器使用E2B兼容的协议连接到PPIO Agent沙箱服务。

    Args:
        require_confirm (bool, optional): 如果为True，在运行代码前提示用户确认
            以确保安全性。 (default: :obj:`True`)
        api_base_url (Optional[str], optional): PPIO Agent沙箱服务的API基础URL。
            如果未提供，将从环境变量PPIO_E2B_API_BASE_URL读取。
            (default: :obj:`None`)
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
        api_base_url: Optional[str] = None,
        timeout: Optional[int] = 300,  # 增加超时时间到5分钟
    ) -> None:
        from e2b_code_interpreter import Sandbox

        self.require_confirm = require_confirm
        self.api_base_url = api_base_url or os.environ.get("PPIO_E2B_API_BASE_URL")
        self.timeout = timeout
        
        # 创建Sandbox实例，支持自定义API base URL
        if self.api_base_url:
            logger.info(f"使用PPIO Agent沙箱服务: {self.api_base_url}")
            # 设置环境变量，让e2b-code-interpreter使用自定义的API base URL
            os.environ["E2B_API_BASE_URL"] = self.api_base_url
            self._sandbox = Sandbox(
                api_key=os.environ.get("E2B_API_KEY"),
                timeout=self.timeout
            )
        else:
            logger.info("使用默认E2B沙箱服务")
            self._sandbox = Sandbox(
                api_key=os.environ.get("E2B_API_KEY"),
                timeout=self.timeout
            )

    def __del__(self) -> None:
        r"""PPIOE2BInterpreter类的析构函数。

        这个方法确保当解释器被删除时，e2b沙箱被正确关闭。
        """
        try:
            if (
                hasattr(self, '_sandbox')
                and self._sandbox is not None
                and self._sandbox.is_running()
            ):
                self._sandbox.kill()
        except ImportError as e:
            logger.warning(f"沙箱清理时出错: {e}")

    def run(
        self,
        code: str,
        code_type: str = "python",
    ) -> str:
        r"""在PPIO Agent沙箱中执行给定的代码。

        Args:
            code (str): 要执行的代码字符串。
            code_type (str): 要执行的代码类型 (例如, 'python', 'bash')。
                (default: obj:`python`)

        Returns:
            str: 执行代码输出的字符串表示。

        Raises:
            InterpreterError: 如果`code_type`不被支持或在代码执行过程中
                发生任何运行时错误。
        """
        if code_type not in self._CODE_TYPE_MAPPING:
            raise InterpreterError(
                f"不支持的代码类型 {code_type}。 "
                f"`{self.__class__.__name__}` 只支持 "
                f"{', '.join(list(self._CODE_TYPE_MAPPING.keys()))}。"
            )
        
        # 打印代码用于安全检查
        if self.require_confirm:
            logger.info(
                f"以下 {code_type} 代码将在您的PPIO Agent沙箱中运行: {code}"
            )
            while True:
                choice = input("运行代码? [Y/n]:").lower()
                if choice in ["y", "yes", "ye"]:
                    break
                elif choice not in ["no", "n"]:
                    continue
                raise InterpreterError(
                    "执行已停止: 用户选择不运行代码。 "
                    "此选择停止当前操作和任何进一步的代码执行。"
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
        r"""提供解释器支持的代码类型。"""
        return list(self._CODE_TYPE_MAPPING.keys())

    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""更新*python*解释器的动作空间"""
        raise RuntimeError("E2B不支持 " "`action_space`。")

    def execute_command(self, command: str) -> str:
        r"""执行命令，可用于解决代码的依赖关系。

        Args:
            command (str): 要执行的命令。

        Returns:
            str: 命令的输出。
        """
        return self._sandbox.commands.run(command) 