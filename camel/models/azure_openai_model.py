# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Union,
)

from openai import AsyncAzureOpenAI, AzureOpenAI

from camel.configs import ChatGPTConfig
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.models.openai_model import OpenAIModel
from camel.types import ModelType
from camel.utils import (
    BaseTokenCounter,
    is_langfuse_available,
)

AzureADTokenProvider = Callable[[], str]


class AzureOpenAIModel(OpenAIModel):
    r"""Azure OpenAI API in a unified BaseModelBackend interface.

    Inherits all Responses API, chat completion, and streaming methods
    from :obj:`OpenAIModel`. Only the client initialization and
    Azure-specific configuration are different.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, Should be the deployment name you chose when you deployed
            an azure model.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        api_version (Optional[str], optional): The api version for the model.
            (default: :obj:`None`)
        azure_ad_token (Optional[str], optional): Your Azure Active Directory
            token, https://www.microsoft.com/en-us/security/business/
            identity-access/microsoft-entra-id. (default: :obj:`None`)
        azure_ad_token_provider (Optional[AzureADTokenProvider], optional): A
            function that returns an Azure Active Directory token, will be
            invoked on every request. (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        client (Optional[Any], optional): A custom synchronous AzureOpenAI
            client instance. If provided, this client will be used instead of
            creating a new one. Useful for RL frameworks like AReaL or rLLM
            that provide Azure OpenAI-compatible clients. The client should
            implement the AzureOpenAI client interface with
            `.chat.completions.create()` and `.beta.chat.completions.parse()`
            methods. (default: :obj:`None`)
        async_client (Optional[Any], optional): A custom asynchronous
            AzureOpenAI client instance. If provided, this client will be
            used instead of creating a new one. The client should implement
            the AsyncAzureOpenAI client interface. (default: :obj:`None`)
        azure_deployment_name (Optional[str], optional): **Deprecated**.
            Use `model_type` parameter instead. This parameter is kept for
            backward compatibility and will be removed in a future version.
            (default: :obj:`None`)
        api_mode (Literal["chat_completions", "responses"], optional):
            Azure OpenAI API mode to use. Supported values:
            `"chat_completions"` (default) and `"responses"`. The
            `"responses"` mode uses the Azure OpenAI Responses API, which
            supports stateful response chaining via
            `previous_response_id`. (default: :obj:`"chat_completions"`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization. Ignored if custom clients are provided.

    References:
        https://learn.microsoft.com/en-us/azure/ai-services/openai/
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        api_version: Optional[str] = None,
        azure_ad_token_provider: Optional["AzureADTokenProvider"] = None,
        azure_ad_token: Optional[str] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        azure_deployment_name: Optional[str] = None,
        api_mode: Literal["chat_completions", "responses"] = (
            "chat_completions"
        ),
        **kwargs: Any,
    ) -> None:
        # Handle deprecated azure_deployment_name parameter
        if azure_deployment_name is not None:
            warnings.warn(
                "The 'azure_deployment_name' parameter is deprecated. "
                "Please use 'model_type' parameter instead. "
                "The 'azure_deployment_name' parameter is being ignored.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Handle deprecated AZURE_DEPLOYMENT_NAME environment variable
        if os.environ.get("AZURE_DEPLOYMENT_NAME") is not None:
            warnings.warn(
                "The 'AZURE_DEPLOYMENT_NAME' environment variable is "
                "deprecated. Please use the 'model_type' parameter "
                "instead. The 'AZURE_DEPLOYMENT_NAME' environment "
                "variable is being ignored.",
                DeprecationWarning,
                stacklevel=2,
            )

        if api_mode not in {"chat_completions", "responses"}:
            raise ValueError(
                "api_mode must be 'chat_completions' or 'responses', "
                f"got: {api_mode}"
            )
        self._api_mode = api_mode
        self._responses_previous_response_id_by_session: Dict[str, str] = {}
        self._responses_last_message_count_by_session: Dict[str, int] = {}

        if model_config_dict is None:
            model_config_dict = ChatGPTConfig().as_dict()
        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        url = url or os.environ.get("AZURE_OPENAI_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        # Skip OpenAIModel.__init__ (requires OPENAI_API_KEY) and create
        # BaseModelBackend directly for Azure-specific setup.
        BaseModelBackend.__init__(
            self,
            model_type,
            model_config_dict,
            api_key,
            url,
            token_counter,
            timeout,
        )

        self.api_version = api_version or os.environ.get("AZURE_API_VERSION")
        self._azure_ad_token = azure_ad_token or os.environ.get(
            "AZURE_AD_TOKEN"
        )
        self.azure_ad_token_provider = azure_ad_token_provider
        if self.api_version is None:
            raise ValueError(
                "Must provide either the `api_version` argument "
                "or `AZURE_API_VERSION` environment variable."
            )

        # Use custom clients if provided, otherwise create new ones
        if client is not None:
            # Use the provided custom sync client
            self._client = client
        else:
            # Create default sync client
            if is_langfuse_available():
                from langfuse.openai import AzureOpenAI as LangfuseOpenAI

                self._client = LangfuseOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )
            else:
                self._client = AzureOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )

        if async_client is not None:
            # Use the provided custom async client
            self._async_client = async_client
        else:
            # Create default async client
            if is_langfuse_available():
                from langfuse.openai import (
                    AsyncAzureOpenAI as LangfuseAsyncOpenAI,
                )

                self._async_client = LangfuseAsyncOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )
            else:
                self._async_client = AsyncAzureOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )

    def _sanitize_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        r"""No-op (Azure does not need)"""
        return config_dict

    def _adapt_messages_for_o1_models(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""No-op (Azure does not need)"""
        return messages
