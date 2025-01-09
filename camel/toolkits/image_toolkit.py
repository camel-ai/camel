from typing import List

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from PIL import Image
import PIL

from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.models import ModelFactory, OpenAIModel
from camel.types import (
    ModelPlatformType,
    ModelType,
    RoleType,
    TaskType,
)
import openai
from retry import retry
import base64
from urllib.parse import urlparse
from loguru import logger


class ImageToolkit(BaseToolkit):
    r"""A class representing a toolkit for image comprehension operations.

    This class provides methods for understanding images, such as identifying
    objects, text in images.
    """
        
    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")


    @retry((openai.APITimeoutError, openai.APIConnectionError))
    def ask_image_by_path(self, question: str, image_path: str) -> str:
        r"""Ask a question about the image based on the image path.

        Args:
            question (str): The question to ask about the image.
            image_path (str): The path to the image file.

        Returns:
            str: The answer to the question based on the image.
        """
        logger.debug(f"Calling ask_image_by_path with question: `{question}` and image_path: `{image_path}`")
        parsed_url = urlparse(image_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        _image_url = image_path

        if not is_url:
            _image_url = f"data:image/jpeg;base64,{self._encode_image(image_path)}"

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for image relevant tasks."
            },
            {
                "role": "user",
                "content": [
                    {
                        'type': 'text',
                        'text': question
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': _image_url,
                        }
                    }
                ]
            },
        ]

        LLM = OpenAIModel(model_type=ModelType.DEFAULT)
        resp = LLM.run(messages)

        return resp.choices[0].message.content


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_image_by_path),
        ]

