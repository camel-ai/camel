import os
from typing import Any, Dict, Optional, Union, List
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    dependencies_required,
)
from camel.messages import OpenAIMessage
from camel.configs import LINKUP_API_PARAMS, LinkupConfig

class LinkupModel(BaseModelBackend):
    r"""Linkup API integrated into a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, typically a search model.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into Linkup's search API. If :obj:`None`, a default
            configuration will be used. (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Linkup service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Linkup service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, a default token counter will be used.
            (default: :obj:`None`)
    """
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        from linkup import LinkupClient

        # Initialize LinkupClient
        if model_config_dict is None:
            model_config_dict = LinkupConfig.as_dict()
        
        api_key = api_key or os.environ.get("LINKUP_API_KEY")
        url = url or os.environ.get("LINKUP_API_BASE_URL")
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )

        self.client = LinkupClient(api_key=self._api_key)

    def _convert_response_from_linkup_to_openai(
            self, 
            response: str) -> ChatCompletion:
        r"""Converts a Linkup `ChatResponse` to an OpenAI-style `ChatCompletion`
        response.

        Args:
            response (str): The response object from the Linkup API.

        Returns:
            ChatCompletion: An OpenAI-compatible chat completion response.
        """
        openai_response = ChatCompletion.construct(
            id=None,
            choices=[
                dict(
                    index=0,
                    message={
                        "role": "assistant",
                        "content": response,
                    },
                    finish_reason=None,
                )
            ],
            created=None,
            model=self.model_type,
            object="chat.completion",
        )

        return openai_response

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter
    
    def _convert_openai_to_linkup_messages(
        self,
        messages: List[OpenAIMessage],
    ) -> List[str]:
        r"""Converts OpenAI API messages to Linkup API messages.

        Args:
            messages (List[OpenAIMessage]): A list of messages in OpenAI
            format.

        Returns:
            List[str]: A list of messages converted to str format.
        """
        linkup_messages = []

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                continue
            elif role == "user":
                content = str(msg.get("content"))
                linkup_messages.append(content)
            elif role == "assistant":
                content = str(msg.get("content"))
                linkup_messages.append(content)
            else:
                raise ValueError(f"Unsupported message role: {role}")

        return linkup_messages
    
    @dependencies_required('LINKUP_API_KEY')
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Run inference of Anthropic chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion: Response in the OpenAI API format.
        """
        linkup_response = ""
        linkup_messages = self._convert_openai_to_linkup_messages(messages)
        for query in linkup_messages:
            item_response = self.client.search(
                query = query,
                **self.model_config_dict,
            )
            if self.model_config_dict.get('output_type') == "sourcedAnswer":
                linkup_response += item_response.answer + '\n'

        return self._convert_response_from_linkup_to_openai(linkup_response)

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to Linkup API. But Linkup API does not have any additional
        arguments to check.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Linkup API.
        """
        for param in self.model_config_dict:
            if param not in LINKUP_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Linkup model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
