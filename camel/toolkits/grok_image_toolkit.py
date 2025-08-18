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
from typing import List, Literal, Optional, Union

from openai import OpenAI

from camel.logger import get_logger
from camel.utils import MCPServer, api_keys_required

from .openai_image_toolkit import OpenAIImageToolkit

logger = get_logger(__name__)


@MCPServer()
class GrokImageToolkit(OpenAIImageToolkit):
    r"""A class toolkit for image generation using Grok's
    Image Generation API.
    Ref: https://docs.x.ai/docs/guides/image-generations
    """

    @api_keys_required(
        [
            ("api_key", "XAI_API_KEY"),
            ("url", "XAI_API_BASE_URL"),
        ]
    )
    def __init__(
        self,
        model: Optional[
            Literal["grok-2-image", "grok-2-image-latest", "grok-2-image-1212"]
        ] = "grok-2-image-1212",
        timeout: Optional[float] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        response_format: Optional[Literal["url", "b64_json"]] = "b64_json",
    ):
        # NOTE: This class inherits from OpenAIImageToolkit because Grok's
        # Image Generation API is compatible with the OpenAI API format,
        # allowing us to reuse most of the parent class's functionality.
        # However, not all parameters from the parent class are supported by
        # Grok's API.

        # Unsupported parameters:
        #     - size: Grok does not support custom image dimensions
        #     - quality: Grok does not support quality settings
        #     - style: Grok does not support style settings
        r"""Initializes a new instance of the GrokImageToolkit class.

        Args:
            api_key (Optional[str]): The API key for authenticating
                with the Grok service. (default: :obj:`None`)
            url (Optional[str]): The url to the Grok service.
                (default: :obj:`None`)
            model (Optional[str]): The model to use.
                (default: :obj:`"grok-2-image-1212"`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        api_key = api_key or os.environ.get("XAI_API_KEY")
        url = url or os.environ.get("XAI_API_BASE_URL")
        self.client = OpenAI(base_url=url, api_key=api_key)
        self.model = model  # type: ignore[assignment]
        self.response_format = response_format

    def _build_base_params(self, prompt: str, n: Optional[int] = None) -> dict:
        r"""Build base parameters dict for Grok API calls.

        Args:
            prompt (str): The text prompt for the image operation.
            n (Optional[int]): The number of images to generate.

        Returns:
            dict: Parameters dictionary with non-None values.
        """
        params = {"prompt": prompt, "model": self.model}
        if n is not None:
            params["n"] = n  # type: ignore[assignment]

        return params

    def _handle_api_response(
        self,
        response,
        image_name: Union[str, List[str]],
        operation: str,
        source: str = "Grok",
    ) -> str:
        r"""Handle API response from Grok image operations.

        Args:
            response: The response object from Grok API.
            image_name (Union[str, List[str]]): Name(s) for the saved image
                file(s). If str, the same name is used for all images (will
                cause error for multiple images). If list, must have exactly
                the same length as the number of images generated.
            operation (str): Operation type for success message ("generated").
            source (str): Source of the image (default: "Grok").

        Returns:
            str: Success message with image path/URL or error message.
        """
        return super()._handle_api_response(
            response,
            image_name,
            operation,
            source="Grok",
        )
