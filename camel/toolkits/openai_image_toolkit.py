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
import os
import uuid
from io import BytesIO
from typing import List, Literal, Optional

from openai import OpenAI
from PIL import Image

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)


@MCPServer()
class OpenAIImageToolkit(BaseToolkit):
    r"""A class toolkit for image generation using OpenAI's
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
            Literal["auto", "low", "medium", "high", "standard", "hd"]
        ] = "standard",
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
                (default: :obj:`"dall-e-3"`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            size (Optional[Literal["256x256", "512x512", "1024x1024",
                "1536x1024", "1024x1536", "1792x1024", "1024x1792",
                "auto"]]):
                The size of the image to generate.
                (default: :obj:`"1024x1024"`)
            quality (Optional[Literal["auto", "low", "medium", "high",
                "standard", "hd"]]):The quality of the image to
                generate. Different models support different values.
                (default: :obj:`"standard"`)
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
            # decode the base64 string to get the image data
            image_data = base64.b64decode(base64_string)
            # create a memory buffer for the image data
            image_buffer = BytesIO(image_data)
            # open the image with PIL
            image = Image.open(image_buffer)
            return image
        except Exception as e:
            logger.error(
                f"An error occurred while converting base64 to image: {e}"
            )
            return None

    def _build_base_params(self, prompt: str) -> dict:
        r"""Build base parameters dict for OpenAI API calls.

        Args:
            prompt (str): The text prompt for the image operation.

        Returns:
            dict: Parameters dictionary with non-None values.
        """
        params = {"prompt": prompt, "model": self.model}

        # basic parameters supported by all models
        if self.n is not None:
            params["n"] = self.n  # type: ignore[assignment]
        if self.size is not None:
            params["size"] = self.size

        # Model-specific parameter filtering based on model
        if self.model == "dall-e-2":
            # dall-e-2 supports: prompt, model, n, size, response_format
            if self.response_format is not None:
                params["response_format"] = self.response_format

        elif self.model == "dall-e-3":
            # dall-e-3 supports: prompt, model, n,
            # size, quality, response_format, style
            if self.quality is not None:
                params["quality"] = self.quality
            if self.response_format is not None:
                params["response_format"] = self.response_format
            if self.style is not None:
                params["style"] = self.style

        elif self.model == "gpt-image-1":
            # gpt-image-1 supports: prompt, model, n, size, quality, background
            # Note: gpt-image-1 seems to default to b64_json response format
            if self.quality is not None:
                params["quality"] = self.quality
            if self.background is not None:
                params["background"] = self.background

        return params

    def _handle_api_response(
        self, response, image_name: str, operation: str
    ) -> str:
        r"""Handle API response from OpenAI image operations.

        Args:
            response: The response object from OpenAI API.
            image_name (str): Name for the saved image file.
            operation (str): Operation type for success message ("generated").

        Returns:
            str: Success message with image path/URL or error message.
        """
        if response.data is None or len(response.data) == 0:
            error_msg = "No image data returned from OpenAI API."
            logger.error(error_msg)
            return error_msg

        results = []

        for i, image_data in enumerate(response.data):
            # check if response has URL or base64 data
            if hasattr(image_data, 'url') and image_data.url:
                image_url = image_data.url
                results.append(f"Image URL: {image_url}")
            elif hasattr(image_data, 'b64_json') and image_data.b64_json:
                image_b64 = image_data.b64_json

                # Save the image from base64
                image_bytes = base64.b64decode(image_b64)
                os.makedirs(self.image_save_path, exist_ok=True)

                # Add index to filename when multiple images
                if len(response.data) > 1:
                    filename = f"{image_name}_{i+1}_{uuid.uuid4().hex}.png"
                else:
                    filename = f"{image_name}_{uuid.uuid4().hex}.png"

                image_path = os.path.join(self.image_save_path, filename)

                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                results.append(f"Image saved to {image_path}")
            else:
                error_msg = (
                    f"No valid image data (URL or base64) found in image {i+1}"
                )
                logger.error(error_msg)
                results.append(error_msg)

        if results:
            count = len(response.data)
            if count == 1:
                return f"Image {operation} successfully. {results[0]}"
            else:
                return (
                    f"{count} images {operation} successfully:\n"
                    + "\n".join(
                        f"  {i+1}. {result}"
                        for i, result in enumerate(results)
                    )
                )
        else:
            error_msg = "No valid image data found in any response"
            logger.error(error_msg)
            return error_msg

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

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.generate_image),
            # could add edit_image function later
        ]
