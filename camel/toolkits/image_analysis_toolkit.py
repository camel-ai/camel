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
import logging
from io import BytesIO
from typing import List, Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

logger = logging.getLogger(__name__)


class ImageAnalysisToolkit(BaseToolkit):
    r"""A class representing a toolkit for image comprehension operations.

    This class provides methods for understanding images, such as identifying
    objects, text in images.
    """

    def __init__(self, model: BaseModelBackend):
        self.model = model

    def image_to_text(
        self, image_path: str, content: Optional[str] = None
    ) -> str:
        r"""Generates textual description of an image with optional custom
            prompt.
        Args:
            image_path (str): Local path or URL to an image file
                content (Optional[str]): Custom description prompt. Defaults
                to None.

        Returns:
            str: Natural language description
        """
        default_content = '''You are an image analysis expert. Provide a 
            detailed description including text if present.'''

        system_msg = BaseMessage.make_assistant_message(
            role_name="Senior Computer Vision Analyst",
            content=content if content else default_content,
        )

        return self._analyze_image(
            image_path=image_path,
            prompt="Please describe the contents of this image.",
            system_message=system_msg,
        )

    def ask_question_about_image(
        self, image_path: str, question: str, content: Optional[str] = None
    ) -> str:
        r"""Answers image questions with optional custom instructions.

        Args:
            image_path (str): Local path or URL to an image file
            question (str): Query about the image content
            content (Optional[str]): Custom analysis instructions. Defaults to
                None.

        Returns:
            str: Detailed answer based on visual understanding
        """
        default_content = """Answer questions about images by:
            1. Careful visual inspection
            2. Contextual reasoning
            3. Text transcription where relevant
            4. Logical deduction from visual evidence"""

        system_msg = BaseMessage.make_assistant_message(
            role_name="Visual QA Specialist",
            content=content if content else default_content,
        )

        return self._analyze_image(
            image_path=image_path,
            prompt=question,
            system_message=system_msg,
        )

    def _open_image(self, image_path: str) -> Image.Image:
        r"""Loads an image from either local path or URL.

        Args:
            image_path (str): Local path or URL to image.

        Returns:
            Image.Image: Loaded PIL Image object.

        Raises:
            ValueError: For invalid paths/URLs or unreadable images.
            requests.exceptions.RequestException: For URL fetch failures.
        """
        parsed = urlparse(image_path)

        if parsed.scheme in ("http", "https"):
            logger.debug(f"Fetching image from URL: {image_path}")
            try:
                response = requests.get(image_path, timeout=15)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))
            except requests.exceptions.RequestException as e:
                logger.error(f"URL fetch failed: {e}")
                raise
        else:
            logger.debug(f"Loading local image: {image_path}")
            try:
                with Image.open(image_path) as img:
                    # Load immediately to detect errors
                    img.load()
                    return img.copy()
            except Exception as e:
                logger.error(f"Image loading failed: {e}")
                raise ValueError(f"Invalid image file: {e}")

    def _analyze_image(
        self,
        image_path: str,
        prompt: str,
        system_message: BaseMessage,
    ) -> str:
        r"""Core analysis method handling image loading and processing.

        Args:
            image_path (str): Image location.
            prompt (str): Analysis query/instructions.
            system_message (BaseMessage): Agent role definition.

        Returns:
            str: Analysis result or error message.
        """
        try:
            image = self._open_image(image_path)
            logger.info(f"Analyzing image: {image_path}")

            from camel.agents.chat_agent import ChatAgent

            agent = ChatAgent(
                system_message=system_message,
                model=self.model,
            )

            user_msg = BaseMessage.make_user_message(
                role_name="User",
                content=prompt,
                image_list=[image],
            )

            response = agent.step(user_msg)
            return response.msgs[0].content

        except (ValueError, requests.exceptions.RequestException) as e:
            logger.error(f"Image handling error: {e}")
            return f"Image error: {e!s}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Analysis failed: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
            in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.image_to_text),
            FunctionTool(self.ask_question_about_image),
        ]
