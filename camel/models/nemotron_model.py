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
from typing import Any, Optional, Union

from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class NemotronModel(OpenAICompatibleModel):
    r"""Nemotron model API backend with OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        api_key (Optional[str], optional): The API key for authenticating with
            the Nvidia service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Nvidia service.
            (default: :obj:`https://integrate.api.nvidia.com/v1`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.

    Notes:
        Nemotron model doesn't support additional model config like OpenAI.
    """

    @api_keys_required(
        [
            ("api_key", "NVIDIA_API_KEY"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        url = url or os.environ.get(
            "NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type,
            {},
            api_key,
            url,
            None,
            timeout,
            max_retries=max_retries,
            **kwargs,
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        raise NotImplementedError(
            "Nemotron model doesn't support token counter."
        )
