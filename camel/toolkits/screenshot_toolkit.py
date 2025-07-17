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

import base64
import io
import os
import time
from pathlib import Path
from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils import dependencies_required
from camel.utils.tool_result import ToolResult

logger = get_logger(__name__)


class ScreenshotToolkit(BaseToolkit):
    r"""A toolkit for taking screenshots."""

    @dependencies_required('PIL')
    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initializes the ScreenshotToolkit.

        Args:
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, it will be determined by the
                `CAMEL_WORKDIR` environment variable (if set). If the
                environment variable is not set, it defaults to
                `camel_working_dir`.
            timeout (Optional[float]): Timeout for API requests in seconds.
                (default: :obj:`None`)
        """
        from PIL import ImageGrab

        super().__init__(timeout=timeout)

        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if working_directory:
            path = Path(working_directory)
        elif camel_workdir:
            path = Path(camel_workdir)
        else:
            path = Path("camel_working_dir")

        self.ImageGrab = ImageGrab
        self.screenshots_dir = path / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def take_screenshot(
        self,
        save_to_file: bool = True,
    ) -> ToolResult:
        r"""Take a screenshot of the entire screen and return it as a
        base64-encoded image.

        Args:
            save_to_file (bool): Whether to save the screenshot to a file.
                (default: :obj:`True`)

        Returns:
            ToolResult: An object containing:
                - text (str): A description of the screenshot.
                - images (List[str]): A list containing one base64-encoded
                  PNG image data URL.
        """
        try:
            # Take screenshot of entire screen
            screenshot = self.ImageGrab.grab()

            # Save to file if requested
            file_path = None
            if save_to_file:
                # Create directory if it doesn't exist
                os.makedirs(self.screenshots_dir, exist_ok=True)

                # Generate filename with timestamp
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"
                file_path = os.path.join(self.screenshots_dir, filename)
                screenshot.save(file_path)
                logger.info(f"Screenshot saved to {file_path}")

            # Convert to base64
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode(
                'utf-8'
            )
            img_data_url = f"data:image/png;base64,{img_base64}"

            # Create result text
            result_text = "Screenshot captured successfully"
            if file_path:
                result_text += f" and saved to {file_path}"

            return ToolResult(text=result_text, images=[img_data_url])

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ToolResult(text=f"Error taking screenshot: {e}", images=[])

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for screenshot operations.

        Returns:
            List[FunctionTool]: List of screenshot functions.
        """
        return [
            FunctionTool(self.take_screenshot),
        ]
