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
import logging
from abc import ABC, abstractmethod
from itertools import cycle
from typing import Any, Dict, List, Optional, Union

from openai import Stream

from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
    UnifiedModelType,
)
from camel.utils import BaseTokenCounter

logger = logging.getLogger(__name__)


class BaseModelBackend(ABC):
    r"""Base class for different model backends.
    It may be OpenAI API, a local LLM, a stub for unit tests, etc.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A config
            dictionary. (default: :obj:`{}`)
        api_key (Optional[str], optional): The API key for authenticating
            with the model service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token
            counter to use for the model. If not provided,
            :obj:`OpenAITokenCounter` will be used. (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        self.model_type: UnifiedModelType = UnifiedModelType(model_type)
        if model_config_dict is None:
            model_config_dict = {}
        self.model_config_dict = model_config_dict
        self._api_key = api_key
        self._url = url
        self._token_counter = token_counter
        self.check_model_config()

    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        pass

    @abstractmethod
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs the query to the backend model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        pass

    @abstractmethod
    def check_model_config(self):
        r"""Check whether the input model configuration contains unexpected
        arguments

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected argument for this model class.
        """
        pass

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count the number of tokens in the messages using the specific
        tokenizer.

        Args:
            messages (List[Dict]): message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        return self.token_counter.count_tokens_from_messages(messages)

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model.

        This method retrieves the maximum token limit either from the
        `model_config_dict` or from the model's default token limit.

        Returns:
            int: The maximum token limit for the given model.
        """
        return (
            self.model_config_dict.get("max_tokens")
            or self.model_type.token_limit
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False


class ModelManager:
    def __init__(
        self,
        models: Union[BaseModelBackend, List[BaseModelBackend]],
        scheduling_strategy: str = "round_robin",
    ):
        """
        Initialize the ModelManager with a list of models and
        a scheduling strategy.
        models: model backend or list of model backends
        (e.g., model instances, APIs)
        scheduling_strategy: name of function that defines how
         to select the next model.
        Defaults to round-robin if not provided.
        """
        if isinstance(models, list):
            self.models = models
        else:
            self.models = [models]
        self.models_cycle = cycle(self.models)
        # Set the scheduling strategy; default is round-robin
        try:
            self.scheduling_strategy = getattr(self, scheduling_strategy)
        except AttributeError:
            logger.warning(
                f"Provided strategy: {scheduling_strategy} is not implemented."
                f"Using default 'round robin'"
            )
            self.scheduling_strategy = self.round_robin

    @property
    def model_type(self):
        """Return type of the first model.
        Assuming that all models instances are the same type."""
        return self.models[0].model_type if self.models else None

    @property
    def model_config_dict(self):
        """Return model_config_dict of the first model.
        Assuming that all models instances are the same type."""
        return self.models[0].model_config_dict if self.models else None

    @model_config_dict.setter
    def model_config_dict(self, model_config_dict: Dict[str, Any]):
        """Set model_config_dict to all models."""
        for model in self.models:
            model.model_config_dict = model_config_dict

    @property
    def token_limit(self):
        """Return token_limit of the first model.
        Assuming that all models instances are the same type."""
        return self.models[0].token_limit if self.models else None

    @property
    def token_counter(self):
        """Return token_counter of the first model.
        Assuming that all models instances are the same type."""
        return self.models[0].token_counter if self.models else None

    def round_robin(self) -> BaseModelBackend:
        """Return models one by one in simple round-robin fashion."""
        return next(self.models_cycle)

    def run(self, messages):
        """
        Process a list of messages by selecting a model based on
        the scheduling strategy.
        Sends the entire list of messages to the selected model,
        and returns a single response.
        messages: List of lists of messages to be processed.
        """
        model = self.scheduling_strategy()

        # Pass all messages to the selected model and get the response
        response = model.run(messages)

        return response
