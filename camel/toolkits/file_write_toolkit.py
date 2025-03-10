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
    r"""A toolkit for writing text content to files.

    This toolkit provides methods to save text content to files, supporting the creation of new files or appending to existing ones.
    """

    def __init__(self, output_dir: str = "./", timeout: Optional[float] = None):
        r"""Initialize FileWriteToolkit.

        Args:
            output_dir (str): The default directory for output files. (default: :obj:`"./"`)
            timeout (Optional[float]): The timeout for the toolkit. (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    def _resolve_filepath(self, file: str) -> str:
        """
        If the given file path is not absolute, prepend the default output directory.
        """
        if not os.path.isabs(file):
            file = os.path.join(self.output_dir, file)
        return file

    def write_to_file(
        self, content: str, filename: str,
    ) -> str:
        r"""A fowerful tool to write content to a file.

        Args:
            content (str): The text content to write to the file.
            filename (str): The name of the file. If it does not contain a path, the default output directory will be used.

        Returns:
            str: A description of the operation result, including the path of the written file.
        """
        # Check if the filename contains a path
        if not os.path.dirname(filename):
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename
            # Ensure the directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Content successfully written to file: {filepath}"
        except Exception as e:
            return f"Error occurred while writing to file: {e}"
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
        # Check if the filename contains a path
        if not os.path.dirname(file):
            filepath = self._resolve_filepath(file)
        else:
            filepath = file
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
            List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.write_to_file),
            FunctionTool(self.file_str_replace),
        ]
