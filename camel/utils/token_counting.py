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

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from io import BytesIO
from math import ceil
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

from deprecation import deprecated  # type: ignore[import-untyped]
from PIL import Image

from camel.logger import get_logger
from camel.types import (
    ModelType,
    OpenAIImageType,
    OpenAIVisionDetailType,
    UnifiedModelType,
)
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from mistral_common.protocol.instruct.request import (  # type:ignore[import-not-found]
        ChatCompletionRequest,
    )

    from camel.messages import OpenAIMessage

LOW_DETAIL_TOKENS = 85
FIT_SQUARE_PIXELS = 2048
SHORTEST_SIDE_PIXELS = 768
SQUARE_PIXELS = 512
SQUARE_TOKENS = 170
EXTRA_TOKENS = 85

logger = get_logger(__name__)


def get_model_encoding(value_for_tiktoken: str):
    r"""Get model encoding from tiktoken.

    Args:
        value_for_tiktoken: Model value for tiktoken.

    Returns:
        tiktoken.Encoding: Model encoding.
    """
    import tiktoken

    try:
        encoding = tiktoken.encoding_for_model(value_for_tiktoken)
    except KeyError:
        if value_for_tiktoken in [
            ModelType.O1.value,
            ModelType.O1_MINI.value,
            ModelType.O1_PREVIEW.value,
        ]:
            encoding = tiktoken.get_encoding("o200k_base")
        else:
            logger.info("Model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
    return encoding


class BaseTokenCounter(ABC):
    r"""Base class for token counters of different kinds of models."""

    @abstractmethod
    def extract_usage_from_response(
        self, response: Any
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from model response.

        Args:
            response: The response object from the model API call.

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        pass

    def extract_usage_from_streaming_response(
        self, stream: Union[Iterator[Any], AsyncIterator[Any]]
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from streaming response.

        This method processes a streaming response to find usage data,
        typically available in the final chunk when stream_options
        include_usage is enabled.

        Args:
            stream: Iterator or AsyncIterator of streaming response chunks

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        try:
            # For sync streams
            if hasattr(stream, '__iter__') and not hasattr(
                stream, '__aiter__'
            ):
                return self._extract_usage_from_sync_stream(stream)
            # For async streams
            elif hasattr(stream, '__aiter__'):
                logger.warning(
                    "Async stream detected but sync method called. "
                    "Use extract_usage_from_async_streaming_response instead."
                )
                return None
            else:
                logger.debug("Unsupported stream type for usage extraction")
                return None
        except Exception as e:
            logger.debug(
                f"Failed to extract usage from streaming response: {e}"
            )
            return None

    async def extract_usage_from_async_streaming_response(
        self, stream: AsyncIterator[Any]
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from async streaming response.

        Args:
            stream: AsyncIterator of streaming response chunks

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        try:
            return await self._extract_usage_from_async_stream(stream)
        except Exception as e:
            logger.debug(
                f"Failed to extract usage from async streaming response: {e}"
            )
            return None

    def _extract_usage_from_sync_stream(
        self, stream: Iterator[Any]
    ) -> Optional[Dict[str, int]]:
        r"""Extract usage from a synchronous streaming response.

        Args:
            stream (Iterator[Any]): Provider-specific synchronous stream iterator.
        Returns:
            Optional[Dict[str, int]]: Usage with `prompt_tokens`, `completion_tokens`,
            `total_tokens`, or None if unavailable.
        """
        final_chunk = None
        try:
            for chunk in stream:
                final_chunk = chunk
                usage = self.extract_usage_from_response(chunk)
                if usage:
                    return usage

            if final_chunk:
                return self.extract_usage_from_response(final_chunk)

        except Exception as e:
            logger.debug(f"Error processing sync stream: {e}")

        return None

    async def _extract_usage_from_async_stream(
        self, stream: AsyncIterator[Any]
    ) -> Optional[Dict[str, int]]:
        r"""Extract usage from asynchronous stream by consuming all chunks."""
        final_chunk = None
        try:
            async for chunk in stream:
                final_chunk = chunk
                usage = self.extract_usage_from_response(chunk)
                if usage:
                    return usage

            if final_chunk:
                return self.extract_usage_from_response(final_chunk)

        except Exception as e:
            logger.debug(f"Error processing async stream: {e}")

        return None

    @abstractmethod
    @deprecated('Use extract_usage_from_response when possible')
    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        pass

    @abstractmethod
    def encode(self, text: str) -> List[int]:
        r"""Encode text into token IDs.

        Args:
            text (str): The text to encode.

        Returns:
            List[int]: List of token IDs.
        """
        pass

    @abstractmethod
    def decode(self, token_ids: List[int]) -> str:
        r"""Decode token IDs back to text.

        Args:
            token_ids (List[int]): List of token IDs to decode.

        Returns:
            str: Decoded text.
        """
        pass


class OpenAITokenCounter(BaseTokenCounter):
    def __init__(self, model: UnifiedModelType):
        r"""Constructor for the token counter for OpenAI models.

        Args:
            model (UnifiedModelType): Model type for which tokens will be
                counted.
        """
        self.model: str = model.value_for_tiktoken

        self.tokens_per_message: int
        self.tokens_per_name: int

        if self.model == "gpt-3.5-turbo-0301":
            # Every message follows <|start|>{role/name}\n{content}<|end|>\n
            self.tokens_per_message = 4
            # If there's a name, the role is omitted
            self.tokens_per_name = -1
        elif (
            ("gpt-3.5-turbo" in self.model)
            or ("gpt-4" in self.model)
            or ("gpt-5" in self.model)
        ):
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        elif (
            ("o1" in self.model)
            or ("o3" in self.model)
            or ("o4" in self.model)
        ):
            self.tokens_per_message = 2
            self.tokens_per_name = 1
        else:
            # flake8: noqa :E501
            raise NotImplementedError(
                "Token counting for OpenAI Models is not presently "
                f"implemented for model {model}. "
                "See https://github.com/openai/openai-python/blob/main/chatml"
                ".md for information on how messages are converted to tokens. "
                "See https://platform.openai.com/docs/models/gpt-4"
                "or https://platform.openai.com/docs/models/gpt-3-5"
                "for information about openai chat models."
            )

        self.encoding = get_model_encoding(self.model)

    def extract_usage_from_response(
        self, response: Any
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from OpenAI response.

        Args:
            response: OpenAI response object (ChatCompletion or similar)

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        try:
            if hasattr(response, 'usage') and response.usage is not None:
                usage = response.usage
                return {
                    'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(
                        usage, 'completion_tokens', 0
                    ),
                    'total_tokens': getattr(usage, 'total_tokens', 0),
                }

        except Exception as e:
            logger.debug(f"Failed to extract usage from OpenAI response: {e}")

        return None

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list with the
        help of package tiktoken.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        num_tokens = 0
        for message in messages:
            num_tokens += self.tokens_per_message
            for key, value in message.items():
                if not isinstance(value, list):
                    num_tokens += len(
                        self.encoding.encode(str(value), disallowed_special=())
                    )
                else:
                    for item in value:
                        if item["type"] == "text":
                            num_tokens += len(
                                self.encoding.encode(
                                    str(
                                        item["text"],
                                    ),
                                    disallowed_special=(),
                                )
                            )
                        elif item["type"] == "image_url":
                            image_str: str = item["image_url"]["url"]
                            detail = item["image_url"]["detail"]

                            # Only count tokens for base64 encoded images
                            # For URLs, we cannot reliably determine token count without fetching the image
                            if image_str.startswith("data:image"):
                                # Base64 encoded image
                                image_prefix_format = "data:image/{};base64,"
                                image_prefix: Optional[str] = None
                                for image_type in list(OpenAIImageType):
                                    # Find the correct image format
                                    image_prefix = image_prefix_format.format(
                                        image_type.value
                                    )
                                    if image_prefix in image_str:
                                        break
                                assert isinstance(image_prefix, str)
                                encoded_image = image_str.split(image_prefix)[
                                    1
                                ]
                                image_bytes = BytesIO(
                                    base64.b64decode(encoded_image)
                                )
                                image = Image.open(image_bytes)
                                num_tokens += self._count_tokens_from_image(
                                    image, OpenAIVisionDetailType(detail)
                                )
                            # Note: For regular URLs, token count cannot be determined without fetching the image
                            # The actual token usage will be reported by the API response
                if key == "name":
                    num_tokens += self.tokens_per_name

        # every reply is primed with <|start|>assistant<|message|>
        num_tokens += 3
        return num_tokens

    def _count_tokens_from_image(
        self, image: Image.Image, detail: OpenAIVisionDetailType
    ) -> int:
        r"""Count image tokens for OpenAI vision model. An :obj:`"auto"`
        resolution model will be treated as :obj:`"high"`. All images with
        :obj:`"low"` detail cost 85 tokens each. Images with :obj:`"high"` detail
        are first scaled to fit within a 2048 x 2048 square, maintaining their
        aspect ratio. Then, they are scaled such that the shortest side of the
        image is 768px long. Finally, we count how many 512px squares the image
        consists of. Each of those squares costs 170 tokens. Another 85 tokens are
        always added to the final total. For more details please refer to `OpenAI
        vision docs <https://platform.openai.com/docs/guides/vision>`_

        Args:
            image (PIL.Image.Image): Image to count number of tokens.
            detail (OpenAIVisionDetailType): Image detail type to count
                number of tokens.

        Returns:
            int: Number of tokens for the image given a detail type.
        """
        if detail == OpenAIVisionDetailType.LOW:
            return LOW_DETAIL_TOKENS

        width, height = image.size
        if width > FIT_SQUARE_PIXELS or height > FIT_SQUARE_PIXELS:
            scaling_factor = max(width, height) / FIT_SQUARE_PIXELS
            width = int(width / scaling_factor)
            height = int(height / scaling_factor)

        scaling_factor = min(width, height) / SHORTEST_SIDE_PIXELS
        scaled_width = int(width / scaling_factor)
        scaled_height = int(height / scaling_factor)

        h = ceil(scaled_height / SQUARE_PIXELS)
        w = ceil(scaled_width / SQUARE_PIXELS)
        total = EXTRA_TOKENS + SQUARE_TOKENS * h * w
        return total

    def encode(self, text: str) -> List[int]:
        r"""Encode text into token IDs.

        Args:
            text (str): The text to encode.

        Returns:
            List[int]: List of token IDs.
        """
        return self.encoding.encode(text, disallowed_special=())

    def decode(self, token_ids: List[int]) -> str:
        r"""Decode token IDs back to text.

        Args:
            token_ids (List[int]): List of token IDs to decode.

        Returns:
            str: Decoded text.
        """
        return self.encoding.decode(token_ids)


class AnthropicTokenCounter(BaseTokenCounter):
    @dependencies_required('anthropic')
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        r"""Constructor for the token counter for Anthropic models.

        Args:
            model (str): The name of the Anthropic model being used.
            api_key (Optional[str], optional): The API key for authenticating
                with the Anthropic service. If not provided, it will use the
                ANTHROPIC_API_KEY environment variable. (default: :obj:`None`)
            base_url (Optional[str], optional): The URL of the Anthropic
                service. If not provided, it will use the default Anthropic
                URL. (default: :obj:`None`)
        """
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key, base_url=base_url)
        self.model = model

    def extract_usage_from_response(
        self, response: Any
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from Anthropic response.

        Args:
            response: Anthropic response object (Message or similar)

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        try:
            if hasattr(response, 'usage') and response.usage is not None:
                usage = response.usage
                input_tokens = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
                return {
                    'prompt_tokens': input_tokens,
                    'completion_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                }

        except Exception as e:
            logger.debug(
                f"Failed to extract usage from Anthropic response: {e}"
            )

        return None

    @dependencies_required('anthropic')
    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list using
        loaded tokenizer specific for this type of model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        from anthropic.types import MessageParam

        return self.client.messages.count_tokens(
            messages=[
                MessageParam(
                    content=str(msg["content"]),
                    role="user" if msg["role"] == "user" else "assistant",
                )
                for msg in messages
            ],
            model=self.model,
        ).input_tokens

    def encode(self, text: str) -> List[int]:
        r"""Encode text into token IDs.

        Args:
            text (str): The text to encode.

        Returns:
            List[int]: List of token IDs.
        """
        raise NotImplementedError(
            "The Anthropic API does not provide direct access to token IDs. "
            "Use count_tokens_from_messages() for token counting instead."
        )

    def decode(self, token_ids: List[int]) -> str:
        r"""Decode token IDs back to text.

        Args:
            token_ids (List[int]): List of token IDs to decode.

        Returns:
            str: Decoded text.
        """
        raise NotImplementedError(
            "The Anthropic API does not provide functionality to decode token IDs."
        )


class LiteLLMTokenCounter(OpenAITokenCounter):
    def __init__(self, model_type: UnifiedModelType):
        r"""Constructor for the token counter for LiteLLM models.

        Args:
            model_type (UnifiedModelType): Model type for which tokens will be
                counted.
        """
        self.model_type = model_type
        self._token_counter = None
        self._completion_cost = None

    @property
    def token_counter(self):
        if self._token_counter is None:
            from litellm import token_counter

            self._token_counter = token_counter
        return self._token_counter

    @property
    def completion_cost(self):
        if self._completion_cost is None:
            from litellm import completion_cost

            self._completion_cost = completion_cost
        return self._completion_cost

    # Inherit extract_usage_from_response from OpenAITokenCounter since
    # LiteLLM standardizes usage format to OpenAI-compatible schema.

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list using
        the tokenizer specific to this type of model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in LiteLLM API format.

        Returns:
            int: Number of tokens in the messages.
        """
        return self.token_counter(model=self.model_type, messages=messages)

    def calculate_cost_from_response(self, response: dict) -> float:
        r"""Calculate the cost of the given completion response.

        Args:
            response (dict): The completion response from LiteLLM.

        Returns:
            float: The cost of the completion call in USD.
        """
        return self.completion_cost(completion_response=response)

    def encode(self, text: str) -> List[int]:
        r"""Encode text into token IDs.

        Args:
            text (str): The text to encode.

        Returns:
            List[int]: List of token IDs.
        """
        from litellm import encoding

        return encoding.encode(text, disallowed_special=())

    def decode(self, token_ids: List[int]) -> str:
        r"""Decode token IDs back to text.

        Args:
            token_ids (List[int]): List of token IDs to decode.

        Returns:
            str: Decoded text.
        """
        from litellm import encoding

        return encoding.decode(token_ids)


class MistralTokenCounter(BaseTokenCounter):
    def __init__(self, model_type: ModelType):
        r"""Constructor for the token counter for Mistral models.

        Args:
            model_type (ModelType): Model type for which tokens will be
                counted.
        """
        from mistral_common.tokens.tokenizers.mistral import (  # type:ignore[import-not-found]
            MistralTokenizer,
        )

        self.model_type = model_type

        # Determine the model type and set the tokenizer accordingly
        model_name = (
            "codestral-22b"
            if self.model_type
            in {
                ModelType.MISTRAL_CODESTRAL,
                ModelType.MISTRAL_CODESTRAL_MAMBA,
            }
            else self.model_type
        )

        self.tokenizer = MistralTokenizer.from_model(model_name)

    def extract_usage_from_response(
        self, response: Any
    ) -> Optional[Dict[str, int]]:
        r"""Extract native usage data from Mistral response.

        Args:
            response: Mistral response object

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
            None if usage data not available
        """
        try:
            if hasattr(response, 'usage') and response.usage is not None:
                usage = response.usage
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)
                return {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens,
                }

        except Exception as e:
            logger.debug(f"Failed to extract usage from Mistral response: {e}")

        return None

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list using
        loaded tokenizer specific for this type of model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Total number of tokens in the messages.
        """
        total_tokens = 0
        for msg in messages:
            tokens = self.tokenizer.encode_chat_completion(
                self._convert_response_from_openai_to_mistral(msg)
            ).tokens
            total_tokens += len(tokens)
        return total_tokens

    def _convert_response_from_openai_to_mistral(
        self, openai_msg: OpenAIMessage
    ) -> ChatCompletionRequest:
        r"""Convert an OpenAI message to a Mistral ChatCompletionRequest.

        Args:
            openai_msg (OpenAIMessage): An individual message with OpenAI
                format.

        Returns:
            ChatCompletionRequest: The converted message in Mistral's request
                format.
        """

        from mistral_common.protocol.instruct.request import (
            ChatCompletionRequest,  # type:ignore[import-not-found]
        )

        mistral_request = ChatCompletionRequest(  # type: ignore[type-var]
            model=self.model_type,
            messages=[openai_msg],
        )

        return mistral_request

    def encode(self, text: str) -> List[int]:
        r"""Encode text into token IDs.

        Args:
            text (str): The text to encode.

        Returns:
            List[int]: List of token IDs.
        """
        # Use the Mistral tokenizer to encode the text
        return self.tokenizer.encode_chat_completion(
            ChatCompletionRequest(
                model=self.model_type,
                messages=[
                    {
                        "role": "user",
                        "content": text,
                    }
                ],
            )
        )

    def decode(self, token_ids: List[int]) -> str:
        r"""Decode token IDs back to text.

        Args:
            token_ids (List[int]): List of token IDs to decode.

        Returns:
            str: Decoded text.
        """
        # Use the Mistral tokenizer to decode the tokens
        return self.tokenizer.decode(token_ids)
