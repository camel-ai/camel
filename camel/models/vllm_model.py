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
import subprocess
from typing import Any, Dict, Optional, Union

from camel.configs import VLLMConfig
from camel.logger import get_logger
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import BaseTokenCounter

logger = get_logger(__name__)


# flake8: noqa: E501
class VLLMModel(OpenAICompatibleModel):
    r"""vLLM service interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`VLLMConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the model service. vLLM doesn't need API key, it would be ignored
            if set. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service. If not
            provided, :obj:`"http://localhost:8000/v1"` will be used.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client initialization.

    References:
        https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = VLLMConfig().as_dict()
        self._url = url or os.environ.get("VLLM_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        self._model_type = model_type

        if not self._url:
            self._start_server()

        super().__init__(
            model_type=self._model_type,
            model_config_dict=model_config_dict,
            api_key="Not_Used",
            url=self._url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

    def _start_server(self) -> None:
        r"""Starts the vllm server in a subprocess."""
        try:
            subprocess.Popen(
                ["vllm", "server", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._url = "http://localhost:8000/v1"
            logger.info(
                f"vllm server started on {self._url} "
                f"for {self._model_type} model."
            )
        except Exception as e:
            logger.error(f"Failed to start vllm server: {e}.")
