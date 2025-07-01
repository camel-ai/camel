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
import json
import os
import uuid
from io import BytesIO
from typing import IO, List, Literal, Optional, Union

from openai import OpenAI
from PIL import Image

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)


@MCPServer()
class OpenAIImageToolkit(BaseToolkit):
    r"""A class representing a toolkit for image generation using OpenAI's
    Image Generation API.
    """

    @api_keys_required(
        [
            ("api_key", "OPENAI_API_KEY"),
        ]
    )
    def __init__(
        self,
        model: Optional[
            Literal["gpt-image-1", "dall-e-3", "dall-e-2"]
        ] = "gpt-image-1",
        timeout: Optional[float] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        size: Optional[
            Literal[
                "256x256",
                "512x512",
                "1024x1024",
                "1536x1024",
                "1024x1536",
                "1792x1024",
                "1024x1792",
                "auto",
            ]
        ] = "1024x1024",
        quality: Optional[
            Literal["auto", "high", "medium", "low", "standard", "hd"]
        ] = "auto",
        response_format: Optional[Literal["url", "b64_json"]] = "b64_json",
        n: Optional[int] = 1,
        background: Optional[
            Literal["transparent", "opaque", "auto"]
        ] = "auto",
        style: Optional[Literal["vivid", "natural"]] = None,
        image_save_path: Optional[str] = "image_save",
    ):
        r"""Initializes a new instance of the OpenAIImageToolkit class.

        Args:
            api_key (Optional[str]): The API key for authenticating
                with the OpenAI service. (default: :obj:`None`)
            url (Optional[str]): The url to the OpenAI service.
                (default: :obj:`None`)
            model (Optional[str]): The model to use.
                (default: :obj:`"gpt-image-1"`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            size (Optional[Literal["256x256", "512x512", "1024x1024",
                "1536x1024", "1024x1536", "1792x1024", "1024x1792",
                "auto"]]):
                The size of the image to generate.
                (default: :obj:`"1024x1024"`)
            quality (Optional[Literal["auto", "high", "medium", "low",
                "standard", "hd"]]):The quality of the image to
                generate. (default: :obj:`"auto"`)
            response_format (Optional[Literal["url", "b64_json"]]):
                The format of the response.(default: :obj:`"b64_json"`)
            n (Optional[int]): The number of images to generate.
                (default: :obj:`1`)
            background (Optional[Literal["transparent", "opaque", "auto"]]):
                The background of the image.(default: :obj:`"auto"`)
            style (Optional[Literal["vivid", "natural"]]): The style of the
                image.(default: :obj:`None`)
            image_save_path (Optional[str]): The path to save the generated
                image.(default: :obj:`"image_save"`)
        """
        super().__init__(timeout=timeout)
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")
        self.client = OpenAI(api_key=api_key, base_url=url)
        self.model = model
        self.size = size
        self.quality = quality
        self.response_format = response_format
        self.n = n
        self.background = background
        self.style = style
        self.image_save_path: str = image_save_path or "image_save"

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

    def _build_base_params(self, prompt: str) -> dict:
        r"""Build base parameters dict for OpenAI API calls.

        Args:
            prompt (str): The text prompt for the image operation.

        Returns:
            dict: Parameters dictionary with non-None values.
        """
        params = {"prompt": prompt, "model": self.model}

        if self.n is not None:
            params["n"] = self.n
        if self.size is not None:
            params["size"] = self.size
        if self.quality is not None:
            params["quality"] = self.quality
        if self.response_format is not None:
            params["response_format"] = self.response_format

        # Only add background parameter for models that support it (gpt-image-1)
        if self.background is not None and self.model == "gpt-image-1":
            params["background"] = self.background

        # Only add style parameter for models that support it (dall-e-3)
        if self.style is not None and self.model == "dall-e-3":
            params["style"] = self.style

        return params

    def _handle_api_response(self, response, image_name: str, operation: str) -> str:
        r"""Handle API response from OpenAI image operations.

        Args:
            response: The response object from OpenAI API.
            image_name (str): Name for the saved image file.
            operation (str): Operation type for success message ("generated" or "edited").

        Returns:
            str: Success message with image path/URL or error message.
        """
        if response.data is None or len(response.data) == 0:
            error_msg = "No image data returned from OpenAI API."
            logger.error(error_msg)
            return error_msg

        if self.response_format == "url":
            image_url = response.data[0].url
            return f"Image {operation} successfully. Image URL: {image_url}"
        else:
            image_b64 = response.data[0].b64_json
            if image_b64 is None:
                error_msg = "Expected base64 image data but got None"
                logger.error(error_msg)
                return error_msg

            # Save the image from base64
            image_bytes = base64.b64decode(image_b64)
            os.makedirs(self.image_save_path, exist_ok=True)
            image_path = os.path.join(
                self.image_save_path,
                f"{image_name}_{uuid.uuid4().hex}.png",
            )

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            operation_past = "generated" if operation == "generated" else "edited"
            return f"Image {operation_past} and saved to {image_path}"

    def generate_image(
        self,
        prompt: str,
        image_name: str = "image",
    ) -> str:
        r"""Generate an image using OpenAI's Image Generation models.
        The generated image will be saved locally (for ``b64_json`` response
        formats) or an image URL will be returned (for ``url`` response
        formats).

        Args:
            prompt (str): The text prompt to generate the image.
            image_name (str): The name of the image to save.
                (default: :obj:`"image"`)

        Returns:
            str: the content of the model response or format of the response.
        """
        try:
            params = self._build_base_params(prompt)
            response = self.client.images.generate(**params)
            return self._handle_api_response(response, image_name, "generated")
        except Exception as e:
            error_msg = f"An error occurred while generating image: {e}"
            logger.error(error_msg)
            return error_msg

    def edit_image(
        self,
        prompt: str,
        image_paths: Union[str, List[str]],
        image_name: str = "edited_image",
    ) -> str:
        r"""Edit an existing image (or images) using OpenAI's Image Edit API.

        Args:
            prompt (str): The text prompt describing the modifications to
                the image.
            image_paths (Union[str, List[str]]): List of file paths to the
                input images to be edited. for example:
                "['image1.png', 'image2.png']" or "image1.png,image2.png"
            image_name (str): The name of the output image.
                (default: :obj:`"edited_image"`)

        Returns:
            str: Path to the saved image (for ``b64_json`` responses) or a URL
                string, or an error message when something went wrong.
        """
        try:
            # Normalize incoming image paths into a list
            image_paths_list: List[str]

            if isinstance(image_paths, str):
                # Try to parse as JSON first
                try:
                    image_paths_list = json.loads(image_paths)
                    if not isinstance(image_paths_list, list):
                        raise ValueError()
                except Exception:
                    # If not JSON, try comma-separated values
                    if ',' in image_paths:
                        image_paths_list = [
                            path.strip() for path in image_paths.split(',')
                        ]
                    else:
                        # Single path
                        image_paths_list = [image_paths]
            elif isinstance(image_paths, list):
                image_paths_list = image_paths
            else:
                raise ValueError(
                    f"image_paths must be a list of strings or a string, "
                    f"got {type(image_paths)}"
                )

            # Open image files with proper resource management
            images: List[IO[bytes]] = []
            try:
                for path in image_paths_list:
                    images.append(open(path, "rb"))

                # Build parameters and add image-specific ones
                params = self._build_base_params(prompt)

                # For edit API, use the first image (or all images for gpt-image-1)
                if self.model == "gpt-image-1":
                    params["image"] = images  # type: ignore[assignment]
                else:
                    params["image"] = images[0]

                response = self.client.images.edit(**params)
                return self._handle_api_response(response, image_name, "edited")
            finally:
                # Ensure all opened files are closed
                for img in images:
                    img.close()
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
        return [
            FunctionTool(self.generate_image),
            FunctionTool(self.edit_image),
        ]
