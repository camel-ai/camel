# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import os
from typing import Any, Dict, Optional

import httpx
import requests

from camel.types import ModelType


class CogVideoModel:
    r"""CogVideo model API backend."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        url: Optional[str] = "http://localhost:8000/generate",
        use_gpu: bool = True,
    ) -> None:
        r"""Constructor for CogVideo backend

        Reference: https://github.com/THUDM/CogVideo

        Args:
            model_type (ModelType): Model for which backend is created
                such as CogVideoX-2B, CogVideoX-5B, etc.
            model_config_dict (Dict[str, Any]): A dictionary of parameters
                for the model configuration.
            url (Optional[str]): The URL to the model service.
                (default: 'http://localhost:8000/generate')
            use_gpu (bool): Whether to use GPU for inference. (default: True)
        """
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._url = url or os.environ.get("COGVIDEO_API_BASE_URL")
        if not self._url:
            raise ValueError("COGVIDEO_API_BASE_URL should be set.")
        self._use_gpu = use_gpu

    async def run(self, prompt: str, **kwargs: Any) -> str:
        r"""Run the CogVideo model to generate a video from a text prompt.

        Args:
            prompt (str): The text prompt to generate the video.
            **kwargs (Any): Additional arguments for the model request.

        Returns:
            str: The path or URL to the generated video.

        Raises:
            Exception: If there is an error in the request or response.
        """
        data = {
            "prompt": prompt,
            "model_type": self.model_type,
            "use_gpu": self._use_gpu,
            **self.model_config_dict,
            **kwargs,
        }

        if not isinstance(self._url, str):
            raise ValueError("URL should be a string.")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self._url, json=data)
                response.raise_for_status()
                video_url = response.json().get("video_url")
                if not video_url:
                    raise ValueError(
                        "No video URL returned by the model service."
                    )
                return video_url

            except requests.exceptions.RequestException as e:
                raise Exception("Error during CogVideo API call") from e
