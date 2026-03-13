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
import re
import textwrap
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from camel.messages import OpenAIMessage


def extract_thinking_from_content(
    content: str,
    reasoning_content: str | None = None,
) -> tuple[str, str | None]:
    r"""Extract ``<think>`` tags from content into reasoning_content.

    Used for both pre-processing (stripping ``<think>`` tags from
    input messages before sending to the model) and post-processing
    (extracting ``<think>`` tags from model output into the
    ``reasoning_content`` field).

    If the content contains ``<think>...</think>`` tags and
    ``reasoning_content`` is not already set, extracts the thinking
    content and returns cleaned content with the reasoning.

    Args:
        content (str): The response content that may contain
            ``<think>`` tags.
        reasoning_content (str | None): Existing reasoning content.
            If already set, no extraction is performed.
            (default: :obj:`None`)

    Returns:
        tuple[str, str | None]: A tuple of (cleaned_content,
            reasoning_content). If no extraction was needed, returns
            the original values unchanged.
    """
    if reasoning_content is not None:
        return content, reasoning_content
    if '<think>' not in content or '</think>' not in content:
        return content, reasoning_content

    think_match = re.search(r'<think>(.*?)</think>', content, flags=re.DOTALL)
    if think_match:
        extracted = think_match.group(1).strip()
        # Only set reasoning_content if there's actual content
        if extracted:
            reasoning_content = extracted
    content = re.sub(
        r'<think>.*?</think>', '', content, flags=re.DOTALL
    ).strip()
    return content, reasoning_content


def try_modify_message_with_format(
    message: OpenAIMessage,
    response_format: Type[BaseModel] | None,
) -> None:
    r"""Modifies the content of the message to include the instruction of using
    the response format.

    The message will not be modified in the following cases:
    - response_format is None
    - message content is not a string
    - message role is assistant

    Args:
        response_format (Type[BaseModel] | None): The Pydantic model class.
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
    _enforce_object_additional_properties_false(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_format.__name__,
            "schema": schema,
        },
    }


def _enforce_object_additional_properties_false(schema: Any) -> None:
    r"""Recursively enforce strict object schemas.

    OpenAI-compatible structured-output backends frequently reject object
    schemas that omit ``additionalProperties``. Mirror the stricter OpenAI
    Responses handling so the json_schema fallback remains usable for nested
    Pydantic models.
    """
    if isinstance(schema, dict):
        if (
            schema.get("type") == "object"
            and "additionalProperties" not in schema
        ):
            schema["additionalProperties"] = False

        for value in schema.values():
            _enforce_object_additional_properties_false(value)
    elif isinstance(schema, list):
        for item in schema:
            _enforce_object_additional_properties_false(item)


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
