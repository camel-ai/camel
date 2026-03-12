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

import copy
import os
from typing import Any, Dict, List, Optional, Union

from camel.configs import MoonshotConfig
from camel.logger import get_logger
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ModelType,
    StructuredOutputMode,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)

logger = get_logger(__name__)


class MoonshotModel(OpenAICompatibleModel):
    r"""Moonshot API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of Moonshot series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into :obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`MoonshotConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Moonshot service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Moonshot service.
            For Chinese users, use :obj:`https://api.moonshot.cn/v1`.
            For overseas users, the default endpoint will be used.
            (default: :obj:`https://api.moonshot.ai/v1`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required([("api_key", "MOONSHOT_API_KEY")])
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
            model_config_dict = MoonshotConfig().as_dict()
        api_key = api_key or os.environ.get("MOONSHOT_API_KEY")
        # Preserve default URL if not provided
        if url is None:
            url = (
                os.environ.get("MOONSHOT_API_BASE_URL")
                or "https://api.moonshot.ai/v1"
            )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

    @property
    def structured_output_mode(self) -> StructuredOutputMode:
        return StructuredOutputMode.JSON_OBJECT

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare request config with Moonshot-specific tool cleaning."""
        request_config = super()._prepare_request_config(tools)

        if tools:
            # Clean tools to remove null types (Moonshot API incompatibility)
            request_config["tools"] = self._clean_tool_schemas(
                request_config["tools"]
            )

        return request_config

    def _clean_tool_schemas(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        r"""Clean tool schemas to remove null types for Moonshot compatibility.

        Moonshot API doesn't accept {"type": "null"} in anyOf schemas.
        This method removes null type definitions from parameters.

        Args:
            tools (List[Dict[str, Any]]): Original tool schemas.

        Returns:
            List[Dict[str, Any]]: Cleaned tool schemas.
        """

        def remove_null_from_schema(schema: Any) -> Any:
            """Recursively remove null types from schema."""
            if isinstance(schema, dict):
                # Create a copy to avoid modifying the original
                result = {}

                for key, value in schema.items():
                    if key == 'type' and isinstance(value, list):
                        # Handle type arrays like ["string", "null"]
                        filtered_types = [t for t in value if t != 'null']
                        if len(filtered_types) == 1:
                            # Single type remains, convert to string
                            result[key] = filtered_types[0]
                        elif len(filtered_types) > 1:
                            # Multiple types remain, keep as array
                            result[key] = filtered_types
                        else:
                            # All were null, use string as fallback
                            logger.warning(
                                "All types in tool schema type array "
                                "were null, falling back to 'string' "
                                "type for Moonshot API compatibility. "
                                "Original tool schema may need review."
                            )
                            result[key] = 'string'
                    elif key == 'anyOf':
                        # Handle anyOf with null types
                        filtered = [
                            item
                            for item in value
                            if not (
                                isinstance(item, dict)
                                and item.get('type') == 'null'
                            )
                        ]
                        if len(filtered) == 1:
                            # If only one type remains, flatten it
                            return remove_null_from_schema(filtered[0])
                        elif len(filtered) > 1:
                            result[key] = [
                                remove_null_from_schema(item)
                                for item in filtered
                            ]
                        else:
                            # All were null, return string type as fallback
                            logger.warning(
                                "All types in tool schema anyOf were null, "
                                "falling back to 'string' type for "
                                "Moonshot API compatibility. Original "
                                "tool schema may need review."
                            )
                            return {"type": "string"}
                    else:
                        # Recursively process other values
                        result[key] = remove_null_from_schema(value)

                return result
            elif isinstance(schema, list):
                return [remove_null_from_schema(item) for item in schema]
            else:
                return schema

        cleaned_tools = copy.deepcopy(tools)
        for tool in cleaned_tools:
            if 'function' in tool and 'parameters' in tool['function']:
                params = tool['function']['parameters']
                if 'properties' in params:
                    params['properties'] = remove_null_from_schema(
                        params['properties']
                    )

        return cleaned_tools
