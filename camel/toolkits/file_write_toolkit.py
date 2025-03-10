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
from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class FileWriteToolkit(BaseToolkit):
    r"""A toolkit for writing and modifying file content.

    This toolkit implements two functions:
    - file_write: Overwrite or append content to a file.
    - file_str_replace: Replace specified string in a file.
    """

    def __init__(self, output_dir: str = "./model_outputs", timeout: Optional[float] = None):
        r"""Initialize FileWriteToolkit.

        Args:
            output_dir (str): The default directory for output files. (default: "./model_outputs")
            timeout (Optional[float]): The timeout for the toolkit. (default: None)
        """
        super().__init__(timeout=timeout)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolve_filepath(self, file: str) -> str:
        """
        If the given file path is not absolute, prepend the default output directory.
        """
        if not os.path.isabs(file):
            file = os.path.join(self.output_dir, file)
        return file

    def file_write(
        self,
        file: str,
        content: str,
        append: bool = False,
        leading_newline: bool = False,
        trailing_newline: bool = False,
        sudo: bool = False,
    ) -> str:
        r"""Overwrite or append content to a file. Use for creating new files, appending content, or modifying existing files.

        Args:
            file (str): Absolute path of the file to write to.
            content (str): Text content to write.
            append (bool, optional): Whether to use append mode. Defaults to False.
            leading_newline (bool, optional): Whether to add a leading newline. Defaults to False.
            trailing_newline (bool, optional): Whether to add a trailing newline. Defaults to False.
            sudo (bool, optional): Whether to use sudo privileges. (Not implemented in this demo)

        Returns:
            str: A confirmation message indicating the result.
        """
        # 处理前后换行
        if leading_newline:
            content = "\n" + content
        if trailing_newline:
            content = content + "\n"

        # 如果不是绝对路径，则拼接输出目录
        filepath = self._resolve_filepath(file)
        mode = "a" if append else "w"
        
        try:
            with open(filepath, mode, encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Successfully wrote content to {filepath}")
            return f"Successfully wrote content to file: {filepath}"
        except Exception as e:
            logger.error(f"Failed to write to file {filepath}: {e}")
            return f"Failed to write to file {filepath}: {e}"

    def file_str_replace(
        self,
        file: str,
        old_str: str,
        new_str: str,
        sudo: bool = False,
    ) -> str:
        r"""Replace specified string in a file. Use for updating specific content in files or fixing errors in code.

        Args:
            file (str): Absolute path of the file to perform replacement on.
            old_str (str): Original string to be replaced.
            new_str (str): New string to replace with.
            sudo (bool, optional): Whether to use sudo privileges. (Not implemented in this demo)

        Returns:
            str: A confirmation message indicating the result.
        """
        filepath = self._resolve_filepath(file)
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File {filepath} not found.")

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = content.replace(old_str, new_str)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"Successfully replaced text in {filepath}")
            return f"Successfully replaced text in file: {filepath}"
        except Exception as e:
            logger.error(f"Failed to replace text in file {filepath}: {e}")
            return f"Failed to replace text in file {filepath}: {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Return a list of FunctionTool objects representing the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.file_write),
            FunctionTool(self.file_str_replace),
        ]
