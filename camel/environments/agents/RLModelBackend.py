from typing import TYPE_CHECKING, Any
import os

from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import BaseTokenCounter, OpenAITokenCounter
from openai import AsyncOpenAI, AsyncStream, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from transformers.tokenization_utils_fast import PreTrainedTokenizerFast


if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
elif os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        from traceroot import trace as observe  # type: ignore[import]
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe


logger = get_logger(__name__)


class RLOpenAICompatibleModel(BaseModelBackend):
    r"""Constructor for model backend supporting AReaL OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`{}` will be used. (default: :obj:`None`)
        api_key (str): The API key for authenticating with the model service.
        url (str): The url to the model service.
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
        **kwargs (Any): Additional arguments to pass to the
            OpenAI client initialization. These can include parameters like
            'organization', 'default_headers', 'http_client', etc.
    """

    def __init__(
        self,
        model_type: ModelType | str,
        openai_client: AsyncOpenAI,
        tokenizer: "PreTrainedTokenizerFast",
        model_config_dict: dict[str, Any] | None = None,
        api_key: str | None = None,
        url: str | None = None,
        token_counter: BaseTokenCounter | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        api_key = api_key or os.environ.get("OPENAI_COMPATIBILITY_API_KEY")
        url = url or os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type,
            model_config_dict,
            api_key,
            url,
            token_counter,
            timeout,
            max_retries,
        )
        self.tokenizer = tokenizer
        self._client = openai_client

    @observe()
    def _run(
        self,
        messages: list[OpenAIMessage],
        response_format: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> (
        ChatCompletion
        | Stream[ChatCompletionChunk]
        | ChatCompletionStreamManager[BaseModel]
    ):
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
                `ChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
        """

        raise NotImplementedError("Not implemented")

    @observe()
    async def _arun(
        self,
        messages: list[OpenAIMessage],
        response_format: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> (
        ChatCompletion
        | AsyncStream[ChatCompletionChunk]
        | AsyncChatCompletionStreamManager[BaseModel]
    ):
        r"""Runs inference of OpenAI chat completion in async mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk],
                AsyncChatCompletionStreamManager[BaseModel]]:
                `ChatCompletion` in the non-stream mode,
                `AsyncStream[ChatCompletionChunk]` in the stream mode,
                or `AsyncChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
        """
        request_config = self.model_config_dict.copy()
        if tools:
            request_config["tools"] = tools
        result = await self._client.chat.completions.create(
            messages=messages,
            **request_config,
        )

        return result

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            OpenAITokenCounter: The token counter following the model's
                tokenization style.
        """

        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
