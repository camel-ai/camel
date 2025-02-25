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
import warnings
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, AsyncStream, OpenAI, Stream
from pydantic import BaseModel

from camel.configs import OPENAI_API_PARAMS, ChatGPTConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)

UNSUPPORTED_PARAMS = {
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "logprobs",
    "top_logprobs",
    "logit_bias",
}


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of GPT_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter` will
            be used. (default: :obj:`None`)
    """

    @api_keys_required(
        [
            ("api_key", "OPENAI_API_KEY"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = ChatGPTConfig().as_dict()
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")

        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )

        self._client = OpenAI(
            timeout=180,
            max_retries=3,
            base_url=self._url,
            api_key=self._api_key,
        )
        self._async_client = AsyncOpenAI(
            timeout=180,
            max_retries=3,
            base_url=self._url,
            api_key=self._api_key,
        )

    def _sanitize_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize the model configuration for O1 models."""

        if self.model_type in [
            ModelType.O1,
            ModelType.O1_MINI,
            ModelType.O1_PREVIEW,
            ModelType.O3_MINI,
        ]:
            warnings.warn(
                "Warning: You are using an O1 model (O1_MINI or O1_PREVIEW), "
                "which has certain limitations, reference: "
                "`https://platform.openai.com/docs/guides/reasoning`.",
                UserWarning,
            )
            return {
                k: v
                for k, v in config_dict.items()
                if k not in UNSUPPORTED_PARAMS
            }
        return config_dict

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(self.model_type)
        return self._token_counter

    def preprocess_messages(
        self, messages: Union[List[OpenAIMessage], str]
    ) -> Any:  # type: ignore[override]
        # If messages is a string, it indicates a JSONL file path or content,
        # so no preprocessing is needed.
        if isinstance(messages, str):
            return messages
        # Otherwise, call the parent class implementation for preprocessing.
        return super().preprocess_messages(messages)

    def _process_batch_messages(self, batch_str: str) -> Any:
        """Process batch messages using the OpenAI Batch API.

        Args:
            batch_str (str): A JSONL file path or a JSONL string.

        Returns:
            Any: The metadata of the batch job as a Batch object.
        """
        import io
        import os

        # Check if batch_str is a file path.
        if os.path.exists(batch_str):
            with open(batch_str, "rb") as f:
                file_content = f.read()
            file_obj = io.BytesIO(file_content)
            file_obj.name = os.path.basename(batch_str)
        else:
            # Treat as JSONL string content.
            file_obj = io.BytesIO(batch_str.encode("utf-8"))
            file_obj.name = "batchinput.jsonl"

        # Upload the JSONL file with purpose "batch".
        batch_input_file = self._client.files.create(
            file=file_obj, purpose="batch"
        )
        batch_input_file_id = batch_input_file.id

        # Create a batch job with a fixed 24h completion window.
        batch_job = self._client.batches.create(
            input_file_id=batch_input_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"description": "Batch job"},
        )
        return batch_job

    def check_batch_process_status(
        self, batch_response: Any
    ) -> Union[str, Dict[str, Any]]:
        """Check the status of a batch job and return its output if complete.

        Args:
            batch_response (Batch): The Batch object returned by run().

        Returns:
            Union[str, Dict[str, Any]]: If the batch job is completed and an
            output file is available, returns its content as a string;
            otherwise, returns a dict with the current status and metadata.
        """
        # Ensure the input is a valid Batch object.
        if not hasattr(batch_response, "id"):
            raise TypeError("Invalid batch object provided.")

        # Retrieve the updated batch status.
        batch = self._client.batches.retrieve(batch_response.id)

        # If batch is complete, return the output file content.
        if batch.status == "completed":
            if not batch.output_file_id:
                raise ValueError(
                    "Batch completed but no output file id found."
                )
            file_resp = self._client.files.content(batch.output_file_id)
            return file_resp.text

        # Otherwise, return the current status and batch metadata.
        return {"status": batch.status, "batch": batch}

    def _run(
        self,
        messages: Union[List[OpenAIMessage], str],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:  # type: ignore[override]
        r"""Run inference of OpenAI chat completion.

        If `messages` is a string, it is treated as a JSONL file
        (path or content) for batch processing via OpenAI's Batch API.
        Otherwise, if it is a list of OpenAIMessage, the original
        single-request logic is used.

        Args:
            messages (Union[List[OpenAIMessage], str]): Either a list of
                OpenAIMessage for a single query, or a string representing
                a JSONL file (path or JSONL string) for batch processing.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The tools schema for the
                request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                For single queries, returns ChatCompletion or Stream;
                for batch, returns batch job metadata.
        """
        # If messages is a string, process it as a batch.
        if isinstance(messages, str):
            return self._process_batch_messages(messages)
        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        if response_format:
            return self._request_parse(messages, response_format, tools)
        else:
            return self._request_chat_completion(messages, tools)

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion in async mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """
        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        if response_format:
            return await self._arequest_parse(messages, response_format, tools)
        else:
            return await self._arequest_chat_completion(messages, tools)

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            for tool in tools:
                function_dict = tool.get('function', {})
                function_dict.pop("strict", None)
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            for tool in tools:
                function_dict = tool.get('function', {})
                function_dict.pop("strict", None)
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        request_config = self.model_config_dict.copy()

        request_config["response_format"] = response_format
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return self._client.beta.chat.completions.parse(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        request_config = self.model_config_dict.copy()

        request_config["response_format"] = response_format
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return await self._async_client.beta.chat.completions.parse(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to OpenAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OPENAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into OpenAI model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
