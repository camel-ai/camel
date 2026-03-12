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
import textwrap
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from camel.messages import OpenAIMessage


def try_modify_message_with_format(
    message: OpenAIMessage,
    response_format: Optional[Type[BaseModel]],
) -> None:
    r"""Modifies the content of the message to include the instruction of using
    the response format.

    The message will not be modified in the following cases:
    - response_format is None
    - message content is not a string
    - message role is assistant

    Args:
        response_format (Optional[Type[BaseModel]]): The Pydantic model class.
        message (OpenAIMessage): The message to be modified.
    """
    if response_format is None:
        return

    if not isinstance(message["content"], str):
        return

    if message["role"] == "assistant":
        return

    json_schema = response_format.model_json_schema()
    updated_prompt = textwrap.dedent(
        f"""\
        {message["content"]}

        Please generate a JSON response adhering to the following JSON schema:
        {json_schema}
        Make sure the JSON response is valid and matches the EXACT structure defined in the schema. Your result should ONLY be a valid json object, WITHOUT ANY OTHER TEXT OR COMMENTS.
        """  # noqa: E501
    )
    message["content"] = updated_prompt


def pydantic_to_json_schema_response_format(
    response_format: Type[BaseModel],
) -> Dict[str, Any]:
    r"""Convert a Pydantic model class to a ``json_schema`` response_format
    dict suitable for ``chat.completions.create()``.

    The returned dict has the shape::

        {
            "type": "json_schema",
            "json_schema": {
                "name": "<ModelClassName>",
                "schema": { ... }
            }
        }

    Args:
        response_format (Type[BaseModel]): The Pydantic model class.

    Returns:
        Dict[str, Any]: The response_format dict for the API call.
    """
    schema = response_format.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_format.__name__,
            "schema": schema,
        },
    }


def parse_json_response_to_pydantic(
    content: Optional[str],
    response_format: Type[BaseModel],
) -> Optional[BaseModel]:
    r"""Parse a JSON string returned by the model into a Pydantic instance.

    Args:
        content (Optional[str]): The raw JSON string from the model response.
        response_format (Type[BaseModel]): The Pydantic model class to
            validate against.

    Returns:
        Optional[BaseModel]: The validated Pydantic instance, or ``None``
            if *content* is ``None`` or empty.
    """
    if not content:
        return None
    return response_format.model_validate_json(content)
