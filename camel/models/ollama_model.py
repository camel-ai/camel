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

from camel.configs import OLLAMA_API_PARAMS, OllamaConfig
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import BaseTokenCounter


class OllamaModel(OpenAICompatibleModel):
    r"""Ollama service interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`OllamaConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the model service.  Ollama doesn't need API key, it would be
            ignored if set. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)

    References:
        https://github.com/ollama/ollama/blob/main/docs/openai.md
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = OllamaConfig().as_dict()
        url = url or os.environ.get("OLLAMA_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
        )

        if not self._url:
            self._start_server()

    def _start_server(self) -> None:
        r"""Starts the Ollama server in a subprocess."""
        try:
            subprocess.Popen(
                ["ollama", "server", "--port", "11434"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._url = "http://localhost:11434/v1"
            print(
                f"Ollama server started on {self._url} "
                f"for {self.model_type} model."
            )
        except Exception as e:
            print(f"Failed to start Ollama server: {e}.")

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Ollama API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OLLAMA_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Ollama model backend."
                )
