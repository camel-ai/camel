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
from typing import IO, List, Literal, Optional, Union

from openai import OpenAI
from openai._types import NOT_GIVEN, FileTypes
from PIL import Image
from typing_extensions import cast as typing_cast

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

    def _validate_params(self, operation: str = "generate") -> None:
        r"""Validate parameters according to the selected model and the type of
        operation (generate or edit).

        Args:
            operation (str, optional): Either generate or edit.
                (default: :obj:`"generate"`)

        Raises:
            ValueError: If a parameter is not compatible with the selected
                model or the requested operation.
        """
        # Normalise strings to avoid case issues (all our literals are lower
        # case, but callers might pass upper-case by accident if **kwargs are
        # allowed in future revisions).
        model = (self.model or "").lower()
        size = (self.size or "").lower()
        quality = (self.quality or "").lower()  # type: ignore[arg-type]
        response_format = (self.response_format or "").lower()  # type: ignore[arg-type]
        background = (self.background or "").lower()  # type: ignore[arg-type]
        style = (self.style or "").lower() if self.style is not None else None

        # Shared checks -----------------------------------------------------
        if model not in {"gpt-image-1", "dall-e-3", "dall-e-2"}:
            raise ValueError(
                f"Unsupported model: {self.model}. "
                f"Choose from 'gpt-image-1', 'dall-e-3', or 'dall-e-2'."
            )

        if self.n is not None:
            if not (1 <= self.n <= 10):
                raise ValueError(
                    "Parameter 'n' must be between 1 and 10 inclusive."
                )

        # Model specific checks --------------------------------------------
        if model == "gpt-image-1":
            allowed_sizes = {"1024x1024", "1536x1024", "1024x1536", "auto"}
            allowed_qualities = {"auto", "high", "medium", "low"}
            if size not in allowed_sizes:
                raise ValueError(
                    f"Size '{self.size}' is not supported for gpt-image-1. "
                    f"Allowed: {sorted(allowed_sizes)}."
                )
            if quality not in allowed_qualities:
                raise ValueError(
                    f"Quality '{self.quality}' is not supported for "
                    f"gpt-image-1. "
                    f"Allowed: {sorted(allowed_qualities)}."
                )
            if self.response_format != "b64_json":
                raise ValueError(
                    "gpt-image-1 always returns base64 images. "
                    "'response_format' must be 'b64_json'."
                )
            if style is not None:
                raise ValueError(
                    "Parameter 'style' is not supported for gpt-image-1."
                )
            # background is supported, no further checks needed
            # (already type-hinted).

        elif model == "dall-e-3":
            if operation == "edit":
                raise ValueError(
                    "dall-e-3 does not support the image edit endpoint."
                )

            allowed_sizes = {"1024x1024", "1792x1024", "1024x1792"}
            allowed_qualities = {"hd", "standard"}
            allowed_styles = {"vivid", "natural"}
            if size not in allowed_sizes:
                raise ValueError(
                    f"Size '{self.size}' is not supported for dall-e-3. "
                    f"Allowed: {sorted(allowed_sizes)}."
                )
            if quality not in allowed_qualities:
                raise ValueError(
                    f"Quality '{self.quality}' is not supported for dall-e-3. "
                    f"Allowed: {sorted(allowed_qualities)}."
                )
            if self.n != 1:
                raise ValueError("dall-e-3 only supports n=1.")
            if background != "auto":
                raise ValueError(
                    "Parameter 'background' is not supported for dall-e-3."
                )
            if style is not None and style not in allowed_styles:
                raise ValueError(
                    f"Style '{self.style}' is not supported for dall-e-3. "
                    f"Allowed: {sorted(allowed_styles)}."
                )

        elif model == "dall-e-2":
            allowed_sizes = {"256x256", "512x512", "1024x1024"}
            if size not in allowed_sizes:
                raise ValueError(
                    f"Size '{self.size}' is not supported for dall-e-2. "
                    f"Allowed: {sorted(allowed_sizes)}."
                )
            if quality != "standard":
                raise ValueError(
                    "Parameter 'quality' must be 'standard' for dall-e-2."
                )
            if background != "auto":
                raise ValueError(
                    "Parameter 'background' is not supported for dall-e-2."
                )
            if style is not None:
                raise ValueError(
                    "Parameter 'style' is not supported for dall-e-2."
                )

        # Additional checks for response_format (for models that allow it).
        if model in {"dall-e-2", "dall-e-3"} and response_format not in {
            "url",
            "b64_json",
        }:
            raise ValueError(
                "'response_format' must be either 'url' or 'b64_json'."
            )

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

        # Validate parameters before making the request
        self._validate_params(operation="generate")
        try:
            # Call the OpenAI Images API with only the parameters supported
            # by each model variant. This avoids the need for type ignores or
            # casts while satisfying the static type checker.

            if self.model == "gpt-image-1":
                response = self.client.images.generate(
                    prompt=prompt,
                    model=self.model,
                    n=self.n if self.n is not None else NOT_GIVEN,
                    size=self.size if self.size is not None else NOT_GIVEN,
                    quality=self.quality
                    if self.quality is not None
                    else NOT_GIVEN,
                    background=self.background
                    if self.background is not None
                    else NOT_GIVEN,
                )
            elif self.model == "dall-e-3":
                response = self.client.images.generate(
                    prompt=prompt,
                    model=self.model,
                    n=self.n if self.n is not None else NOT_GIVEN,
                    size=self.size if self.size is not None else NOT_GIVEN,
                    quality=self.quality
                    if self.quality is not None
                    else NOT_GIVEN,
                    response_format=self.response_format
                    if self.response_format is not None
                    else NOT_GIVEN,
                    style=self.style if self.style is not None else NOT_GIVEN,
                )
            else:  # "dall-e-2"
                response = self.client.images.generate(
                    prompt=prompt,
                    model=self.model,
                    n=self.n if self.n is not None else NOT_GIVEN,
                    size=self.size if self.size is not None else NOT_GIVEN,
                    quality=self.quality
                    if self.quality is not None
                    else NOT_GIVEN,
                    response_format=self.response_format
                    if self.response_format is not None
                    else NOT_GIVEN,
                )

            if response.data is None or len(response.data) == 0:
                error_msg = "No image data returned from OPENAI API."
                logger.error(error_msg)
                return error_msg
            if self.response_format == "url":
                image_url = response.data[0].url
                return f"Image generated successfully. Image URL: {image_url}"
            else:
                image_b64 = response.data[0].b64_json
                image = self.base64_to_image(image_b64)  # type: ignore[arg-type]

                if image is None:
                    error_msg = "Failed to convert base64 string to image."
                    logger.error(error_msg)
                    return error_msg

                os.makedirs(self.image_save_path, exist_ok=True)
                image_path = os.path.join(
                    self.image_save_path,
                    f"{image_name}_{uuid.uuid4().hex}.png",
                )
                image.save(image_path)
                return f"Image saved to {image_path}"
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

        # Validate parameters before making the request
        self._validate_params(operation="edit")
        try:
            # Normalize incoming image paths into a list without changing the
            # runtime type of the original ``image_paths`` variable (to keep
            # mypy happy).
            image_paths_list: List[str]

            if isinstance(image_paths, str):
                # Try to parse as JSON first
                try:
                    import json

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

            # Open multiple image files
            images: List[IO[bytes]] = []
            for path in image_paths_list:
                images.append(open(path, "rb"))

            # Call the OpenAI Images Edit API with model-specific arguments.
            if self.model == "gpt-image-1":
                # Cast to FileTypes to satisfy the OpenAI SDK type requirements
                file_images: FileTypes = images  # type: ignore[assignment]

                # Cast size and quality to match edit API expectations
                edit_size = typing_cast(
                    Optional[
                        Literal[
                            "256x256",
                            "512x512",
                            "1024x1024",
                            "1536x1024",
                            "1024x1536",
                            "auto",
                        ]
                    ],
                    self.size,
                )
                edit_quality = typing_cast(
                    Optional[
                        Literal["standard", "low", "medium", "high", "auto"]
                    ],
                    self.quality,
                )

                response = self.client.images.edit(
                    image=file_images,
                    prompt=prompt,
                    model=self.model,
                    n=self.n if self.n is not None else NOT_GIVEN,
                    size=edit_size if edit_size is not None else NOT_GIVEN,
                    quality=edit_quality
                    if edit_quality is not None
                    else NOT_GIVEN,
                    background=self.background
                    if self.background is not None
                    else NOT_GIVEN,
                )
            else:  # "dall-e-2"
                single_image = images[0]

                # Cast size and quality to match edit API expectations
                edit_size = typing_cast(
                    Optional[
                        Literal[
                            "256x256",
                            "512x512",
                            "1024x1024",
                            "1536x1024",
                            "1024x1536",
                            "auto",
                        ]
                    ],
                    self.size,
                )
                edit_quality = typing_cast(
                    Optional[
                        Literal["standard", "low", "medium", "high", "auto"]
                    ],
                    self.quality,
                )

                response = self.client.images.edit(
                    image=single_image,
                    prompt=prompt,
                    model=self.model,
                    n=self.n if self.n is not None else NOT_GIVEN,
                    size=edit_size if edit_size is not None else NOT_GIVEN,
                    quality=edit_quality
                    if edit_quality is not None
                    else NOT_GIVEN,
                    response_format=self.response_format
                    if self.response_format is not None
                    else NOT_GIVEN,
                )

            # Close all opened files
            for img in images:
                img.close()

            if response.data is None or len(response.data) == 0:
                error_msg = "No image data returned from OpenAI API."
                logger.error(error_msg)
                return error_msg
            if self.response_format == "url":
                image_url = response.data[0].url
                return f"Image edited successfully. Image URL: {image_url}"
            else:
                image_b64 = response.data[0].b64_json
                # Ensure image_b64 is not None before decoding
                assert (
                    image_b64 is not None
                ), "Expected base64 image data but got None"

            # Save the image directly from base64
            image_bytes = base64.b64decode(image_b64)

            os.makedirs(self.image_save_path, exist_ok=True)
            image_path = os.path.join(
                self.image_save_path, f"{image_name}_{uuid.uuid4().hex}.png"
            )

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            return f"Edited image saved to {image_path}"
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
