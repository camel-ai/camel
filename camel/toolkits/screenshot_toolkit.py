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
from typing import List, Optional

from PIL import Image

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.toolkits import BaseToolkit, FunctionTool
from camel.toolkits.base import RegisteredAgentToolkit
from camel.utils import dependencies_required

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
        self.screenshots_dir = path
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def read_image(
        self,
        image_path: str,
        instruction: str = "",
    ) -> str:
        r"""Analyzes an image from a local file path.

        This function enables you to "see" and interpret an image from a
        file. It's useful for tasks where you need to understand visual
        information, such as reading a screenshot of a webpage or a diagram.

        Args:
            image_path (str): The local file path to the image.
                For example: 'screenshots/login_page.png'.
            instruction (str, optional): Specific instructions for what to look
                for or what to do with the image. For example: "What is the
                main headline on this page?" or "Find the 'Submit' button.".

        Returns:
            str: The response after analyzing the image, which could be a
                 description, an answer, or a confirmation of an action.
        """
        if self.agent is None:
            logger.error(
                "Cannot record screenshot in memory: No agent registered. "
                "Please pass this toolkit to ChatAgent via "
                "toolkits_to_register_agent parameter."
            )
            return (
                "Error: No agent registered. Please pass this toolkit to "
                "ChatAgent via toolkits_to_register_agent parameter."
            )

        try:
            image_path = str(Path(image_path).absolute())

            # Check if file exists before trying to open
            if not os.path.exists(image_path):
                error_msg = f"Screenshot file not found: {image_path}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Load the image from the path
            img = Image.open(image_path)

            # Create a message with the screenshot image
            message = BaseMessage.make_user_message(
                role_name="User",
                content=instruction,
                image_list=[img],
            )

            # Record the message in agent's memory
            response = self.agent.step(message)
            return response.msgs[0].content

        except Exception as e:
            logger.error(f"Error reading screenshot: {e}")
            return f"Error reading screenshot: {e}"

    def take_screenshot_and_read_image(
        self,
        filename: str,
        save_to_file: bool = True,
        read_image: bool = True,
        instruction: Optional[str] = None,
    ) -> str:
        r"""Captures a screenshot of the entire screen.

        This function can save the screenshot to a file and optionally analyze
        it. It's useful for capturing the current state of the UI for
        documentation, analysis, or to guide subsequent actions.

        Args:
            filename (str): The name for the screenshot file (e.g.,
                "homepage.png"). The file is saved in a `screenshots`
                subdirectory within the working directory. Must end with
                `.png`. (default: :obj:`None`)
            save_to_file (bool, optional): If `True`, saves the screenshot to
                a file. (default: :obj:`True`)
            read_image (bool, optional): If `True`, the agent will analyze
                the screenshot. `save_to_file` must also be `True`.
                (default: :obj:`True`)
            instruction (Optional[str], optional): A specific question or
                command for the agent regarding the screenshot, used only if
                `read_image` is `True`. For example: "Confirm that the
                user is logged in.".

        Returns:
            str: A confirmation message indicating success or failure,
                 including the file path if saved, and the agent's response
                 if `read_image` is `True`.
        """
        try:
            # Take screenshot of entire screen
            screenshot = self.ImageGrab.grab()

            # Save to file if requested
            file_path = None
            if save_to_file:
                # Create directory if it doesn't exist
                os.makedirs(self.screenshots_dir, exist_ok=True)

                # Create unique filename if file already exists
                base_path = os.path.join(self.screenshots_dir, filename)
                file_path = base_path
                counter = 1
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{counter}{ext}"
                    file_path = os.path.join(
                        self.screenshots_dir, unique_filename
                    )
                    counter += 1

                screenshot.save(file_path)
                logger.info(f"Screenshot saved to {file_path}")

            # Create result text
            result_text = "Screenshot captured successfully"
            if file_path:
                result_text += f" and saved to {file_path}"

            # Record in agent memory if requested
            if read_image and file_path is not None:
                inst = instruction if instruction is not None else ""
                response = self.read_image(
                    str(Path(file_path).absolute()), inst
                )
                result_text += f". Agent response: {response}"

            return result_text

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return f"Error taking screenshot: {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for screenshot operations.

        Returns:
            List[FunctionTool]: List of screenshot functions.
        """
        return [
            FunctionTool(self.take_screenshot_and_read_image),
            FunctionTool(self.read_image),
        ]
