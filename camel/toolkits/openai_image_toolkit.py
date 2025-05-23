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

import base64
import os
import uuid
from io import BytesIO
from typing import List, Optional

from openai import OpenAI
from PIL import Image

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class OpenAIImageToolkit(BaseToolkit):
    r"""A class representing a toolkit for image generation using OpenAI's
    Image Generation API..
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initializes a new instance of the OpenAIImageToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

    def base64_to_image(self, base64_string: str) -> Optional[Image.Image]:
        r"""Converts a base64 encoded string into a PIL Image object.

        Args:
            base64_string (str): The base64 encoded string of the image.

        Returns:
            Optional[Image.Image]: The PIL Image object or None if conversion
                fails.
        """
        try:
            # Decode the base64 string to get the image data
            image_data = base64.b64decode(base64_string)
            # Create a memory buffer for the image data
            image_buffer = BytesIO(image_data)
            # Open the image using the PIL library
            image = Image.open(image_buffer)
            return image
        except Exception as e:
            error_msg = (
                f"An error occurred while converting base64 to image: {e}"
            )
            logger.error(error_msg)
            return None

    def image_path_to_base64(self, image_path: str) -> str:
        r"""Converts the file path of an image to a Base64 encoded string.

        Args:
            image_path (str): The path to the image file.

        Returns:
            str: A Base64 encoded string representing the content of the image
                file.
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            error_msg = (
                f"An error occurred while converting image path to base64: {e}"
            )
            logger.error(error_msg)
            return error_msg

    def image_to_base64(self, image: Image.Image) -> str:
        r"""Converts an image into a base64-encoded string.

        This function takes an image object as input, encodes the image into a
        PNG format base64 string, and returns it.
        If the encoding process encounters an error, it prints the error
        message and returns None.

        Args:
            image: The image object to be encoded, supports any image format
                that can be saved in PNG format.

        Returns:
            str: A base64-encoded string of the image.
        """
        try:
            with BytesIO() as buffered_image:
                image.save(buffered_image, format="PNG")
                buffered_image.seek(0)
                image_bytes = buffered_image.read()
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                return base64_str
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            logger.error(error_msg)
            return error_msg

    def get_img(
        self, prompt: str, image_dir: str = "img", model: str = "gpt-image-1"
    ) -> str:
        r"""Generate an image using OpenAI's Image Generation model.
            The generated image is saved to the specified directory.

        Args:
            model (str): The model to use. Defaults to 'gpt-image-1'
            prompt (str): The text prompt based on which the image is
                generated.
            image_dir (str): The directory to save the generated image.
                Defaults to 'img'.

        Returns:
            str: The path to the saved image.
        """

        client = OpenAI()
        response = client.images.generate(
            model=model,
            prompt=prompt,
        )
        if response.data is None or len(response.data) == 0:
            error_msg = "No image data returned from OPENAI API."
            logger.error(error_msg)
            return error_msg
        image_b64 = response.data[0].b64_json
        image = self.base64_to_image(image_b64)  # type: ignore[arg-type]

        if image is None:
            error_msg = "Failed to convert base64 string to image."
            logger.error(error_msg)
            return error_msg

        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, f"{uuid.uuid4()}.png")
        image.save(image_path)

        return image_path

    def edit_img(
        self,
        prompt: str,
        image_path: str,
        mask_path: Optional[str] = None,
        image_dir: str = "img",
        model: str = "gpt-image-1",
    ) -> str:
        r"""Edit an existing image using OpenAI's image generation API.

        Args:
            prompt (str): The text prompt describing the modifications to the
                image.
            image_path (str): The file path to the input image to be edited.
            mask_path (Optional[str]): The file path to an optional mask image
                specifying editable regions. If None, the entire image may be
                modified based on the prompt and model. Defaults to None.
            image_dir (str): The directory to save the edited image.
            model (str): The OpenAI model to use for editing.
                Defaults to 'gpt-image-1'.

        Returns:
            str: The path to the saved image.
        """
        client = OpenAI()
        try:
            with open(image_path, "rb") as image_file:
                image = image_file.read()
            if mask_path:
                with open(mask_path, "rb") as mask_file:
                    mask = mask_file.read()
            response = client.images.edit(
                model=model,
                prompt=prompt,
                image=image,
                mask=mask,
                n=1,
                response_format="b64_json",
            )
            if response.data is None or len(response.data) == 0:
                error_msg = "No image data returned from OpenAI API."
                logger.error(error_msg)
                return error_msg
            image_b64 = response.data[0].b64_json
            edited_image = self.base64_to_image(image_b64)  # type: ignore[arg-type]
            if edited_image is None:
                error_msg = "Failed to convert base64 string to edited image."
                logger.error(error_msg)
                return error_msg

            os.makedirs(image_dir, exist_ok=True)
            image_path = os.path.join(image_dir, f"{uuid.uuid4()}.png")
            edited_image.save(image_path)
            return image_path
        except Exception as e:
            error_msg = f"An error occurred while editing image: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [FunctionTool(self.get_img), FunctionTool(self.edit_img)]
