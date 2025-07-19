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
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from PIL import Image

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.toolkits import BaseToolkit, FunctionTool
from camel.toolkits.base import RegisteredAgentToolkit
from camel.utils import dependencies_required

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class ScreenshotToolkit(BaseToolkit, RegisteredAgentToolkit):
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
        RegisteredAgentToolkit.__init__(self)

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

    def read_screenshot(
        self,
        screenshot_path: str,
        instruction: str = "",
    ) -> str:
        r"""Read a screenshot from a file.

        This method requires the toolkit to be registered with a ChatAgent
        via the `toolkits_to_register_agent` parameter.

        Args:
            screenshot_path (str): The path to the screenshot to read.
            instruction (str): The instruction for the read the screenshot.

        Returns:
            str: The response from the agent.
        """
        if self.agent is None:
            logger.error(
                "Cannot record screenshot in memory: No agent registered. "
                "Please pass this toolkit to ChatAgent via "
                "toolkits_to_register_agent parameter."
            )

        try:
            # Load the image from the path
            img = Image.open(screenshot_path)

            # Create a message with the screenshot image
            message = BaseMessage.make_user_message(
                role_name="User",
                content=instruction,
                image_list=[img],
            )

            # Record the message in agent's memory
            if self.agent is not None:
                response = self.agent.step(message)
                return response.msgs[0].content
            else:
                return "Error: No agent registered to process screenshot."
        except Exception as e:
            logger.error(f"Error recording screenshot: {e}")
            return f"Error recording screenshot: {e}"

    def take_screenshot(
        self,
        filename: str,
        save_to_file: bool = True,
        read_screenshot: bool = False,
        instruction: Optional[str] = None,
    ) -> str:
        r"""Take a screenshot of the entire screen.

        The screenshot can be saved to a file and is returned as a
        base64-encoded data URL.

        Args:
            filename (str): The name of the file for the screenshot. It must
                end with `.png`. The file is saved in a `screenshots`
                subdirectory within the toolkit's working directory.
                Example: "desktop_view.png".
            save_to_file (bool, optional): If `True`, the screenshot is saved
                to a file. Defaults to `True`.
            read_screenshot (bool, optional): If `True` and an agent is
                registered, the screenshot will be read by the agent.
                Defaults to `False`.
            instruction (Optional[str]): Optional instruction for the
                screenshot when reading. Only used if
                `read_screenshot` is `True`.

        Returns:

        """
        try:
            # Take screenshot of entire screen
            screenshot = self.ImageGrab.grab()

            # Save to file if requested
            file_path = None
            if save_to_file:
                # Create directory if it doesn't exist
                os.makedirs(self.screenshots_dir, exist_ok=True)

                file_path = os.path.join(self.screenshots_dir, filename)
                screenshot.save(file_path)
                logger.info(f"Screenshot saved to {file_path}")

            # Create result text
            result_text = "Screenshot captured successfully"
            if file_path:
                result_text += f" and saved to {file_path}"

            # Record in agent memory if requested
            if read_screenshot and file_path is not None:
                inst = instruction if instruction is not None else ""
                response = self.read_screenshot(file_path, inst)
                result_text += response

            return "screenshot taken successfully and be read by the agent"

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return "screenshot taken failed"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for screenshot operations.

        Returns:
            List[FunctionTool]: List of screenshot functions.
        """
        return [
            FunctionTool(self.take_screenshot),
            FunctionTool(self.read_screenshot),
        ]
