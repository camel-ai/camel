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
import base64
import hashlib
import json
import logging
import os
import re
import tempfile
import textwrap
from typing import Any, Callable, Dict, List, Optional, Union, Type

from pydantic import BaseModel, ConfigDict, ValidationError
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool
from camel.types import Choice
from camel.types.agents import ToolCallingRecord
from camel.agents._types import ModelResponse, ToolCallRequest


from camel.logger import get_logger

logger = get_logger(__name__)


def generate_tool_prompt(tool_schema_list: List[Dict[str, Any]]) -> str:
    r"""Generates a tool prompt based on the provided tool schema list.

    Returns:
        str: A string representing the tool prompt.
    """
    tool_prompts = []

    for tool in tool_schema_list:
        tool_info = tool["function"]
        tool_name = tool_info["name"]
        tool_description = tool_info["description"]
        tool_json = json.dumps(tool_info, indent=4, ensure_ascii=False)

        prompt = (
            f"Use the function '{tool_name}' to '{tool_description}':\n"
            f"{tool_json}\n"
        )
        tool_prompts.append(prompt)

    tool_prompt_str = "\n".join(tool_prompts)

    final_prompt = textwrap.dedent(
        f"""\
        You have access to the following functions:

        {tool_prompt_str}

        If you choose to call a function ONLY reply in the following format with no prefix or suffix:

        <function=example_function_name>{{"example_name": "example_value"}}</function>

        Reminder:
        - Function calls MUST follow the specified format, start with <function= and end with </function>
        - Required parameters MUST be specified
        - Only call one function at a time
        - Put the entire function call reply on one line
        - If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls.
        """  # noqa: E501
    )
    return final_prompt


def extract_tool_call(
    content: str,
) -> Optional[Dict[str, Any]]:
    r"""Extract the tool call from the model response, if present.

    Args:
        response (Any): The model's response object.

    Returns:
        Optional[Dict[str, Any]]: The parsed tool call if present,
            otherwise None.
    """
    function_regex = r"<function=(\w+)>(.*?)</function>"
    match = re.search(function_regex, content)

    if not match:
        return None

    function_name, args_string = match.groups()
    try:
        args = json.loads(args_string)
        return {"function": function_name, "arguments": args}
    except json.JSONDecodeError as error:
        logger.error(f"Error parsing function arguments: {error}")
        return None


def safe_model_dump(obj) -> Dict[str, Any]:
    r"""Safely dump a Pydantic model to a dictionary.

    This method attempts to use the `model_dump` method if available,
    otherwise it falls back to the `dict` method.
    """
    # Check if the `model_dump` method exists (Pydantic v2)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    # Fallback to `dict()` method (Pydantic v1)
    elif hasattr(obj, "dict"):
        return obj.dict()
    else:
        raise TypeError("The object is not a Pydantic model")


def convert_to_function_tool(
    tool: Union[FunctionTool, Callable],
) -> FunctionTool:
    r"""Convert a tool to a FunctionTool from Callable."""
    return tool if isinstance(tool, FunctionTool) else FunctionTool(tool)


def convert_to_schema(
    tool: Union[FunctionTool, Callable, Dict[str, Any]],
) -> Dict[str, Any]:
    r"""Convert a tool to a schema from Callable or FunctionTool."""
    if isinstance(tool, FunctionTool):
        return tool.get_openai_tool_schema()
    elif callable(tool):
        return FunctionTool(tool).get_openai_tool_schema()
    else:
        return tool


def get_info_dict(
    session_id: Optional[str],
    usage: Optional[Dict[str, int]],
    termination_reasons: List[str],
    num_tokens: int,
    tool_calls: List[ToolCallingRecord],
    external_tool_call_requests: Optional[List[ToolCallRequest]] = None,
) -> Dict[str, Any]:
    r"""Returns a dictionary containing information about the chat session.

    Args:
        session_id (str, optional): The ID of the chat session.
        usage (Dict[str, int], optional): Information about the usage of
            the LLM.
        termination_reasons (List[str]): The reasons for the termination
            of the chat session.
        num_tokens (int): The number of tokens used in the chat session.
        tool_calls (List[ToolCallingRecord]): The list of function
            calling records, containing the information of called tools.
        external_tool_call_requests (Optional[List[ToolCallRequest]]): The
            requests for external tool calls.


    Returns:
        Dict[str, Any]: The chat session information.
    """
    return {
        "id": session_id,
        "usage": usage,
        "termination_reasons": termination_reasons,
        "num_tokens": num_tokens,
        "tool_calls": tool_calls,
        "external_tool_call_requests": external_tool_call_requests,
    }


def handle_logprobs(choice: Choice) -> Optional[List[Dict[str, Any]]]:
    if choice.logprobs is None:
        return None

    tokens_logprobs = choice.logprobs.content

    if tokens_logprobs is None:
        return None

    return [
        {
            "token": token_logprob.token,
            "logprob": token_logprob.logprob,
            "top_logprobs": [
                (top_logprob.token, top_logprob.logprob)
                for top_logprob in token_logprob.top_logprobs
            ],
        }
        for token_logprob in tokens_logprobs
    ]


def try_format_message(
        message: BaseMessage, response_format: Type[BaseModel]
) -> bool:
    r"""Try to format the message if needed.

    Returns:
        bool: Whether the message is formatted successfully (or no format
            is needed).
    """
    if message.parsed:
        return True

    try:
        message.parsed = response_format.model_validate_json(
            message.content
        )
        return True
    except ValidationError:
        return False


def convert_response_format_to_prompt(
        response_format: Type[BaseModel]
) -> str:
    r"""Convert a Pydantic response format to a prompt instruction.

    Args:
        response_format (Type[BaseModel]): The Pydantic model class.

    Returns:
        str: A prompt instruction requesting the specific format.
    """
    try:
        # Get the JSON schema from the Pydantic model
        schema = response_format.model_json_schema()

        # Create a prompt based on the schema
        format_instruction = (
            "\n\nPlease respond in the following JSON format:\n" "{\n"
        )

        properties = schema.get("properties", {})
        for field_name, field_info in properties.items():
            field_type = field_info.get("type", "string")
            description = field_info.get("description", "")

            if field_type == "array":
                format_instruction += (
                    f'    "{field_name}": ["array of values"]'
                )
            elif field_type == "object":
                format_instruction += f'    "{field_name}": {{"object"}}'
            elif field_type == "boolean":
                format_instruction += f'    "{field_name}": true'
            elif field_type == "number":
                format_instruction += f'    "{field_name}": 0'
            else:
                format_instruction += f'    "{field_name}": "string value"'

            if description:
                format_instruction += f'  // {description}'

            # Add comma if not the last item
            if field_name != list(properties.keys())[-1]:
                format_instruction += ","
            format_instruction += "\n"

        format_instruction += "}"
        return format_instruction

    except Exception as e:
        logger.warning(
            f"Failed to convert response_format to prompt: {e}. "
            f"Using generic format instruction."
        )
        return (
            "\n\nPlease respond in a structured JSON format "
            "that matches the requested schema."
        )


def apply_prompt_based_parsing(
        response: ModelResponse,
    original_response_format: Type[BaseModel],
) -> None:
    r"""Apply manual parsing when using prompt-based formatting.

    Args:
        response: The model response to parse.
        original_response_format: The original response format class.
    """
    for message in response.output_messages:
        if message.content:
            try:
                # Try to extract JSON from the response content
                import json
                import re

                from pydantic import ValidationError

                # Try to find JSON in the content
                content = message.content.strip()

                # Try direct parsing first
                try:
                    parsed_json = json.loads(content)
                    message.parsed = (
                        original_response_format.model_validate(
                            parsed_json
                        )
                    )
                    continue
                except (json.JSONDecodeError, ValidationError):
                    pass

                # Try to extract JSON from text
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                json_matches = re.findall(json_pattern, content, re.DOTALL)

                for json_str in json_matches:
                    try:
                        parsed_json = json.loads(json_str)
                        message.parsed = (
                            original_response_format.model_validate(
                                parsed_json
                            )
                        )
                        # Update content to just the JSON for consistency
                        message.content = json.dumps(parsed_json)
                        break
                    except (json.JSONDecodeError, ValidationError):
                        continue

                if not message.parsed:
                    logger.warning(
                        f"Failed to parse JSON from response: "
                        f"{content}"
                    )

            except Exception as e:
                logger.warning(f"Error during prompt-based parsing: {e}")


def is_vision_error(exc: Exception) -> bool:
    r"""Check if the exception is likely related to vision/image is not
    supported by the model."""
    # TODO: more robust vision error detection
    error_msg = str(exc).lower()
    vision_keywords = [
        'vision',
        'image',
        'multimodal',
        'unsupported',
        'invalid content type',
        'image_url',
        'visual',
    ]
    return any(keyword in error_msg for keyword in vision_keywords)


def get_token_count(model_backend, content: str) -> int:
    r"""Get token count for content with fallback."""
    if hasattr(model_backend, 'token_counter'):
        return len(model_backend.token_counter.encode(content))
    else:
        return len(content.split())


def sanitize_messages_for_logging(messages):
    r"""Sanitize OpenAI messages for logging by replacing base64 image
    data with a simple message and a link to view the image.

    Args:
        messages (List[OpenAIMessage]): The OpenAI messages to sanitize.

    Returns:
        List[OpenAIMessage]: The sanitized OpenAI messages.
    """
    import hashlib
    import os
    import re
    import tempfile

    # Create a copy of messages for logging to avoid modifying the
    # original messages
    sanitized_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            sanitized_msg = msg.copy()
            # Check if content is a list (multimodal content with images)
            if isinstance(sanitized_msg.get('content'), list):
                content_list = []
                for item in sanitized_msg['content']:
                    if (
                        isinstance(item, dict)
                        and item.get('type') == 'image_url'
                    ):
                        # Handle image URL
                        image_url = item.get('image_url', {}).get(
                            'url', ''
                        )
                        if image_url and image_url.startswith(
                            'data:image'
                        ):
                            # Extract image data and format
                            match = re.match(
                                r'data:image/([^;]+);base64,(.+)',
                                image_url,
                            )
                            if match:
                                img_format, base64_data = match.groups()

                                # Create a hash of the image data to use
                                # as filename
                                img_hash = hashlib.md5(
                                    base64_data[:100].encode()
                                ).hexdigest()[:10]
                                img_filename = (
                                    f"image_{img_hash}.{img_format}"
                                )

                                # Save image to temp directory for viewing
                                try:
                                    import base64

                                    temp_dir = tempfile.gettempdir()
                                    img_path = os.path.join(
                                        temp_dir, img_filename
                                    )

                                    # Only save if file doesn't exist
                                    if not os.path.exists(img_path):
                                        with open(img_path, 'wb') as f:
                                            f.write(
                                                base64.b64decode(
                                                    base64_data
                                                )
                                            )

                                    # Create a file:// URL that can be
                                    # opened
                                    file_url = f"file://{img_path}"

                                    content_list.append(
                                        {
                                            'type': 'image_url',
                                            'image_url': {
                                                'url': f'{file_url}',
                                                'detail': item.get(
                                                    'image_url', {}
                                                ).get('detail', 'auto'),
                                            },
                                        }
                                    )
                                except Exception as e:
                                    # If saving fails, fall back to simple
                                    # message
                                    content_list.append(
                                        {
                                            'type': 'image_url',
                                            'image_url': {
                                                'url': '[base64 '
                                                + 'image - error saving: '
                                                + str(e)
                                                + ']',
                                                'detail': item.get(
                                                    'image_url', {}
                                                ).get('detail', 'auto'),
                                            },
                                        }
                                    )
                            else:
                                # If regex fails, fall back to simple
                                # message
                                content_list.append(
                                    {
                                        'type': 'image_url',
                                        'image_url': {
                                            'url': '[base64 '
                                            + 'image - invalid format]',
                                            'detail': item.get(
                                                'image_url', {}
                                            ).get('detail', 'auto'),
                                        },
                                    }
                                )
                        else:
                            content_list.append(item)
                    else:
                        content_list.append(item)
                sanitized_msg['content'] = content_list
            sanitized_messages.append(sanitized_msg)
        else:
            sanitized_messages.append(msg)
    return sanitized_messages


def create_token_usage_tracker() -> Dict[str, int]:
    r"""Creates a fresh token usage tracker for a step.

    Returns:
        Dict[str, int]: A dictionary for tracking token usage.
    """
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def update_token_usage_tracker(
        tracker: Dict[str, int], usage_dict: Dict[str, int]
) -> None:
    r"""Updates a token usage tracker with values from a usage dictionary.

    Args:
        tracker (Dict[str, int]): The token usage tracker to update.
        usage_dict (Dict[str, int]): The usage dictionary with new values.
    """
    tracker["prompt_tokens"] += usage_dict.get("prompt_tokens", 0)
    tracker["completion_tokens"] += usage_dict.get("completion_tokens", 0)
    tracker["total_tokens"] += usage_dict.get("total_tokens", 0)