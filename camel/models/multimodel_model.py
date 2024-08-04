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
from typing import Any, Dict, List, Optional, Union

from openai import Stream
from transformers import (
    AutoModel,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
)

from camel.configs import OPENAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenSourceTokenCounter,
)


class MultimodalModel(BaseModelBackend):
    r"""Class for interace with OpenAI-API-compatible servers running
    open-source multimodal models.
    """

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for model backends of Open-source models.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into :obj:`openai.ChatCompletion.create()`.
            api_key (Optional[str]): The API key for authenticating with the
                model service. (ignored for open-source models)
            url (Optional[str]): The url to the model service.
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenSourceTokenCounter` will
                be used.
        """
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )

        # Check whether the input model type is open-source
        if not model_type.is_open_source:
            raise ValueError(
                f"Model `{model_type}` is not a supported open-source model."
            )

        # Check whether input model path is empty
        model_path: Optional[str] = self.model_config_dict.get(
            "model_path", None
        )
        if not model_path:
            raise ValueError("Path to open-source model is not provided.")
        self.model_path: str = model_path

        # Check whether the model name matches the model type
        self.model_name: str = self.model_path.split('/')[-1]
        if not self.model_type.validate_model_name(self.model_name):
            raise ValueError(
                f"Model name `{self.model_name}` does not match model type "
                f"`{self.model_type.value}`."
            )

        # Load the server URL and check whether it is None
        server_url: Optional[str] = url or self.model_config_dict.get(
            "server_url", None
        )
        if not server_url:
            raise Warning(
                "URL to server running open-source LLM is not provided."
            )
        self.server_url: str = server_url

        import torch

        # Load the device to run the model on
        self.device: str = self.model_config_dict.get("device") or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self._client = (
            AutoModel.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            )
            .to(
                self.device
            )  # this moves the model to the specified device (GPU or CPU)
            .eval()  # this sets the model to evaluation mode
            .half()  # this converts the model parameters to half-precision floating point (FP16).  # noqa: E501
        )

        # Replace `model_config_dict` with only the params to be
        # passed to OpenAI API
        self.model_config_dict = self.model_config_dict["api_params"]

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenSourceTokenCounter(
                self.model_type, self.model_path
            )
        return self._token_counter

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI-API-style chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        messages_openai: List[OpenAIMessage] = messages

        if isinstance(self.token_counter, OpenSourceTokenCounter):
            tokenizer = self.token_counter.tokenizer
        elif isinstance(
            self.token_counter, PreTrainedTokenizer or PreTrainedTokenizerFast
        ):
            tokenizer = self.token_counter
        else:
            raise ValueError(
                f"Token counter {self.token_counter} is not supported."
            )

        image = [
            './examples/liuxiang.mp4',
        ]

        import torch

        with torch.autocast(device_type='cuda', dtype=torch.float16):
            response_str, _ = (
                self._client.chat(  # output param `his` is ignored
                    tokenizer,
                    messages_openai,
                    image,
                    do_sample=False,
                    num_beams=3,
                    use_meta=True,
                )
            )

        response = ChatCompletion(
            msg=response_str, terminated=False, info={}
        )  # TODO: modify this to return the correct response

        return response

    def check_model_config(self):
        r"""Check whether the model configuration is valid for open-source
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API, or it does not contain
                :obj:`model_path` or :obj:`server_url`.
        """
        if (
            "model_path" not in self.model_config_dict
            or "server_url" not in self.model_config_dict
        ):
            raise ValueError(
                "Invalid configuration for open-source model backend with "
                ":obj:`model_path` or :obj:`server_url` missing."
            )

        for param in self.model_config_dict["api_params"]:
            if param not in OPENAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into open-source model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
