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

# Enables postponed evaluation of annotations (for string-based type hints)
from __future__ import annotations

from io import BytesIO
from typing import List, Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class ImageAnalysisToolkit(BaseToolkit):
    r"""A toolkit for comprehensive image analysis and understanding.
    The toolkit uses vision-capable language models to perform these tasks.
    """

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the ImageAnalysisToolkit.

        Args:
            model (Optional[BaseModelBackend]): The model backend to use for
                image analysis tasks. This model should support processing
                images for tasks like image description and visual question
                answering. If None, a default model will be created using
                ModelFactory. (default: :obj:`None`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        if model:
            self.model = model
        else:
            self.model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

    def image_to_text(
        self, image_path: str, sys_prompt: Optional[str] = None
    ) -> str:
        r"""Generates textual description of an image with optional custom
        prompt.

        Args:
            image_path (str): Local path or URL to an image file.
            sys_prompt (Optional[str]): Custom system prompt for the analysis.
                (default: :obj:`None`)

        Returns:
            str: Natural language description of the image.
        """
        default_content = '''You are an image analysis expert. Provide a 
            detailed description including text if present.'''

        system_msg = BaseMessage.make_assistant_message(
            role_name="Senior Computer Vision Analyst",
            content=sys_prompt if sys_prompt else default_content,
        )

        return self._analyze_image(
            image_path=image_path,
            prompt="Please describe the contents of this image.",
            system_message=system_msg,
        )

    def ask_question_about_image(
        self, image_path: str, question: str, sys_prompt: Optional[str] = None
    ) -> str:
        r"""Answers image questions with optional custom instructions.

        Args:
            image_path (str): Local path or URL to an image file.
            question (str): Query about the image content.
            sys_prompt (Optional[str]): Custom system prompt for the analysis.
                (default: :obj:`None`)

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
            content=sys_prompt if sys_prompt else default_content,
        )

        return self._analyze_image(
            image_path=image_path,
            prompt=question,
            system_message=system_msg,
        )

    def _load_image(self, image_path: str) -> Image.Image:
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
                return Image.open(image_path)
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
            system_message (BaseMessage): Custom system prompt for the
                analysis.

        Returns:
            str: Analysis result or error message.
        """
        try:
            image = self._load_image(image_path)
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
            agent.reset()
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
