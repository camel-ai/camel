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
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import httpx
from pydantic import BaseModel

from camel.configs import FunctionGemmaConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, CompletionUsage, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    update_current_observation,
)

# conditional observe import based on environment variables
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


class FunctionGemmaModel(BaseModelBackend):
    r"""FunctionGemma model backend for Ollama with custom tool calling format.

    FunctionGemma is a specialized Gemma model fine-tuned for function calling.
    It uses a custom chat template format that differs from OpenAI's format.
    This backend handles conversion between CAMEL's OpenAI-style tool schemas
    and FunctionGemma's native format.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created (e.g., "functiongemma").
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            of configuration options. If :obj:`None`,
            :obj:`FunctionGemmaConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): Not required for local Ollama.
            (default: :obj:`None`)
        url (Optional[str], optional): The URL to the Ollama server.
            (default: :obj:`http://localhost:11434`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = FunctionGemmaConfig().as_dict()

        url = url or os.environ.get(
            "OLLAMA_API_BASE_URL",
            "http://localhost:11434",
        )
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

        self._client = httpx.Client(timeout=self._timeout)
        self._async_client = httpx.AsyncClient(timeout=self._timeout)

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

    def _escape_string(self, s: str) -> str:
        r"""Wrap string values in <escape> tags for FunctionGemma format.

        Args:
            s (str): The string to escape.

        Returns:
            str: The escaped string.
        """
        return f"<escape>{s}<escape>"

    def _unescape_string(self, s: str) -> str:
        r"""Remove <escape> tags from string values.

        Args:
            s (str): The string to unescape.

        Returns:
            str: The unescaped string.
        """
        return s.replace("<escape>", "")

    def _type_to_function_gemma(self, json_type: Union[str, List[str]]) -> str:
        r"""Convert JSON schema type to FunctionGemma type (uppercase).

        Args:
            json_type (Union[str, List[str]]): The JSON schema type. Can be a
                string like "string" or a list like ["string", "null"] for
                optional parameters.

        Returns:
            str: The FunctionGemma type.
        """
        if isinstance(json_type, list):
            # handle union types like ["string", "null"]
            # use the first non-null type
            for t in json_type:
                if t != "null":
                    return t.upper()
            return "STRING"  # fallback
        return json_type.upper()

    def _format_parameter_properties(
        self,
        properties: Dict[str, Any],
        required: List[str],
    ) -> str:
        r"""Format parameter properties for FunctionGemma declaration.

        Args:
            properties (Dict[str, Any]): The properties dictionary.
            required (List[str]): List of required parameter names.

        Returns:
            str: Formatted properties string.
        """
        parts = []
        for name, prop in sorted(properties.items()):
            desc = prop.get("description", "")
            prop_type = prop.get("type", "string")

            param_str = (
                f"{name}:{{description:{self._escape_string(desc)},"
                f"type:{self._escape_string(self._type_to_function_gemma(prop_type))}}}"
            )
            parts.append(param_str)

        return ",".join(parts)

    def _convert_tool_to_function_gemma(self, tool: Dict[str, Any]) -> str:
        r"""Convert OpenAI tool schema to FunctionGemma declaration format.

        Args:
            tool (Dict[str, Any]): The OpenAI tool schema.

        Returns:
            str: The FunctionGemma declaration string.
        """
        func = tool.get("function", {})
        name = func.get("name", "")
        description = func.get("description", "")
        params = func.get("parameters", {})

        properties = params.get("properties", {})
        required = params.get("required", [])
        param_type = params.get("type", "object")

        # format properties
        props_str = self._format_parameter_properties(properties, required)

        # format required list
        req_parts = [self._escape_string(r) for r in required]
        req_str = ",".join(req_parts)

        type_escaped = self._escape_string(
            self._type_to_function_gemma(param_type)
        )
        desc_escaped = self._escape_string(description)

        declaration = (
            f"<start_function_declaration>"
            f"declaration:{name}{{description:{desc_escaped},"
            f"parameters:{{properties:{{{props_str}}},"
            f"required:[{req_str}],"
            f"type:{type_escaped}}}}}"
            f"<end_function_declaration>"
        )

        return declaration

    def _format_developer_turn(
        self,
        content: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        r"""Format the developer/system turn with function declarations.

        Args:
            content (str): The system message content.
            tools (Optional[List[Dict[str, Any]]]): List of tool schemas.

        Returns:
            str: Formatted developer turn.
        """
        result = "<start_of_turn>developer\n"
        if content:
            result += content
        if tools:
            for tool in tools:
                result += self._convert_tool_to_function_gemma(tool)
        result += "<end_of_turn>\n"
        return result

    def _format_user_turn(self, content: str) -> str:
        r"""Format a user message turn.

        Args:
            content (str): The user message content.

        Returns:
            str: Formatted user turn.
        """
        return f"<start_of_turn>user\n{content}<end_of_turn>\n"

    def _format_model_turn(self, message: OpenAIMessage) -> str:
        r"""Format an assistant/model message turn.

        Args:
            message (OpenAIMessage): The assistant message.

        Returns:
            str: Formatted model turn.
        """
        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls")

        result = f"<start_of_turn>model\n{content}"

        if tool_calls and isinstance(tool_calls, list):
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                func_name = func.get("name", "")
                args_raw = func.get("arguments", "{}")
                if isinstance(args_raw, str):
                    args: Dict[str, Any] = json.loads(args_raw)
                else:
                    args = dict(args_raw) if args_raw else {}

                # format arguments
                arg_parts = []
                for key, value in sorted(args.items()):
                    if isinstance(value, str):
                        arg_parts.append(f"{key}:{self._escape_string(value)}")
                    else:
                        arg_parts.append(f"{key}:{json.dumps(value)}")

                args_str = ",".join(arg_parts)
                result += (
                    f"<start_function_call>call:{func_name}{{{args_str}}}"
                    f"<end_function_call>"
                )

        result += "<end_of_turn>\n"
        return result

    def _format_tool_response(self, message: OpenAIMessage) -> str:
        r"""Format a tool response message.

        Args:
            message (OpenAIMessage): The tool response message.

        Returns:
            str: Formatted tool response.
        """
        content = message.get("content", "")
        name = message.get("name", "")

        # try to parse content as json for structured response
        try:
            if not isinstance(content, str):
                content = str(content) if content else ""
            result_data = json.loads(content)
            # check if it's a dict (structured response)
            if isinstance(result_data, dict):
                result_parts = []
                for key, value in sorted(result_data.items()):
                    if isinstance(value, str):
                        result_parts.append(
                            f"{key}:{self._escape_string(value)}"
                        )
                    else:
                        result_parts.append(f"{key}:{json.dumps(value)}")
                result_str = ",".join(result_parts)
            else:
                # scalar value (int, float, bool, list, etc.)
                if isinstance(result_data, str):
                    result_str = f"value:{self._escape_string(result_data)}"
                else:
                    result_str = f"value:{json.dumps(result_data)}"
        except (json.JSONDecodeError, TypeError):
            result_str = f"value:{self._escape_string(str(content))}"

        return (
            f"<start_function_response>response:{name}{{{result_str}}}"
            f"<end_function_response>"
        )

    def _format_messages(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        r"""Format all messages into a FunctionGemma prompt string.

        Args:
            messages (List[OpenAIMessage]): List of messages in OpenAI format.
            tools (Optional[List[Dict[str, Any]]]): List of tool schemas.

        Returns:
            str: Complete formatted prompt.
        """
        prompt = "<bos>"

        # check for system message
        system_content = ""
        start_idx = 0

        if messages and messages[0].get("role") in ["system", "developer"]:
            content = messages[0].get("content", "")
            if isinstance(content, str):
                system_content = content
            elif isinstance(content, list):
                # handle list content
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        system_content += item.get("text", "")
            start_idx = 1

        # add developer turn if we have system content or tools
        if system_content or tools:
            prompt += self._format_developer_turn(system_content, tools)

        # process remaining messages
        prev_role = None
        for msg in messages[start_idx:]:
            role = msg.get("role", "")

            if role == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt += self._format_user_turn(content)
                elif isinstance(content, list):
                    text_content = ""
                    for item in content:
                        is_text = (
                            isinstance(item, dict)
                            and item.get("type") == "text"
                        )
                        if is_text:
                            text_content += item.get("text", "")
                    prompt += self._format_user_turn(text_content)

            elif role == "assistant":
                prompt += self._format_model_turn(msg)

            elif role == "tool":
                prompt += self._format_tool_response(msg)

            prev_role = role

        # add generation prompt - but not after tool response
        # per FunctionGemma template, model continues after tool response
        if prev_role != "tool":
            prompt += "<start_of_turn>model\n"

        return prompt

    def _extract_function_calls(
        self,
        text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        r"""Extract function calls from model output.

        Args:
            text (str): The model output text.
            tools (Optional[List[Dict[str, Any]]]): Available tools to infer
                function names when the model outputs malformed calls.

        Returns:
            Tuple[str, List[Dict[str, Any]]]: Tuple of
                (remaining_content, list_of_tool_calls).
        """
        tool_calls = []

        # try standard format first:
        # <start_function_call>call:func_name{args}<end_function_call>
        pattern = (
            r"<start_function_call>call:(\w+)\{([^}]*)\}"
            r"(?:<end_function_call>)?"
        )
        match = re.search(pattern, text)

        if match:
            func_name, args_str = match.groups()
            args = self._parse_function_args(args_str)
            tool_call = {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
            }
            tool_calls.append(tool_call)
        else:
            # try alternate format the model might produce:
            # <start_function_response>call{args}<end_function_call>
            # or call:func_name{args} without proper tags
            alt_pattern = r"<start_function_\w+>call(?::(\w+))?\{([^}]*)\}"
            alt_match = re.search(alt_pattern, text)

            if alt_match:
                func_name, args_str = alt_match.groups()
                # if function name is missing, try to infer from tools
                if not func_name:
                    func_name = self._infer_function_name(args_str, tools)
                if func_name:
                    args = self._parse_function_args(args_str)
                    tool_call = {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": json.dumps(args, ensure_ascii=False),
                        },
                    }
                    tool_calls.append(tool_call)

        # remove all function call/response blocks from content
        content = re.sub(
            r"<start_function_call>.*?(?:<end_function_call>|$)",
            "",
            text,
            flags=re.DOTALL,
        )
        content = re.sub(
            r"<start_function_response>.*?(?:<end_function_call>|"
            r"<end_function_response>|$)",
            "",
            content,
            flags=re.DOTALL,
        )
        content = content.strip()

        return content, tool_calls

    def _infer_function_name(
        self,
        args_str: str,
        tools: Optional[List[Dict[str, Any]]],
    ) -> Optional[str]:
        r"""Infer the function name from available tools.

        Args:
            args_str (str): The arguments string from the model output.
            tools (Optional[List[Dict[str, Any]]]): Available tools.

        Returns:
            Optional[str]: The inferred function name, or None if not found.
        """
        if not tools:
            return None

        # if only one tool, use it
        if len(tools) == 1:
            func = tools[0].get("function", {})
            return func.get("name")

        # try to match by argument names
        parsed_args = self._parse_function_args(args_str)
        arg_names = set(parsed_args.keys())

        best_match = None
        best_score = 0

        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            properties = params.get("properties", {})
            tool_arg_names = set(properties.keys())

            # count matching argument names
            score = len(arg_names & tool_arg_names)
            if score > best_score:
                best_score = score
                best_match = func.get("name")

        return best_match

    def _parse_function_args(self, args_str: str) -> Dict[str, Any]:
        r"""Parse function arguments from FunctionGemma format.

        Args:
            args_str (str): The arguments string (e.g., "a:15,b:27").

        Returns:
            Dict[str, Any]: Parsed arguments dictionary.
        """
        args: Dict[str, Any] = {}
        if not args_str:
            return args

        # split by comma, but be careful with escaped strings
        current_key = ""
        current_value = ""
        in_escape = False
        parsing_key = True

        i = 0
        while i < len(args_str):
            char = args_str[i]

            # check for <escape> tag
            if args_str[i : i + 8] == "<escape>":
                in_escape = not in_escape
                i += 8
                continue

            if not in_escape:
                if char == ":" and parsing_key:
                    parsing_key = False
                    i += 1
                    continue
                elif char == "," and not parsing_key:
                    # save current pair
                    args[current_key] = self._parse_value(current_value)
                    current_key = ""
                    current_value = ""
                    parsing_key = True
                    i += 1
                    continue

            if parsing_key:
                current_key += char
            else:
                current_value += char

            i += 1

        # save last pair
        if current_key:
            args[current_key] = self._parse_value(current_value)

        return args

    def _parse_value(self, value: str) -> Any:
        r"""Parse a value string to appropriate Python type.

        Args:
            value (str): The value string.

        Returns:
            Any: Parsed value (int, float, bool, or str).
        """
        value = value.strip()

        # try to parse as number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # check for boolean
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # return as string
        return value

    def _to_chat_completion(  # type: ignore[override]
        self,
        response_text: str,
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Convert parsed response to OpenAI ChatCompletion format.

        Args:
            response_text (str): The model response text.
            model (str): The model name.
            tools (Optional[List[Dict[str, Any]]]): Available tools for
                function name inference.

        Returns:
            ChatCompletion: OpenAI-compatible ChatCompletion object.
        """
        content, tool_calls = self._extract_function_calls(
            response_text, tools
        )

        message: Dict[str, Any] = {
            "role": "assistant",
            "content": content if content else None,
        }

        if tool_calls:
            message["tool_calls"] = tool_calls

        finish_reason = "tool_calls" if tool_calls else "stop"

        choice = dict(
            index=0,
            message=message,
            finish_reason=finish_reason,
        )

        obj = ChatCompletion.construct(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            choices=[choice],
            created=int(time.time()),
            model=model,
            object="chat.completion",
            usage=CompletionUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
        )

        return obj

    def _call_ollama_generate(self, prompt: str) -> str:
        r"""Call Ollama's /api/generate endpoint with raw prompt.

        Args:
            prompt (str): The formatted prompt string.

        Returns:
            str: The model response text.

        Raises:
            RuntimeError: If the API request fails.
        """
        url = f"{self._url}/api/generate"

        options = {}
        if self.model_config_dict.get("temperature") is not None:
            options["temperature"] = self.model_config_dict["temperature"]
        if self.model_config_dict.get("top_p") is not None:
            options["top_p"] = self.model_config_dict["top_p"]
        if self.model_config_dict.get("top_k") is not None:
            options["top_k"] = self.model_config_dict["top_k"]
        if self.model_config_dict.get("num_predict") is not None:
            options["num_predict"] = self.model_config_dict["num_predict"]
        if self.model_config_dict.get("seed") is not None:
            options["seed"] = self.model_config_dict["seed"]

        data = {
            "model": str(self.model_type),
            "prompt": prompt,
            "raw": True,
            "stream": False,
        }

        if options:
            data["options"] = options

        # add default stop sequences if not provided
        stop_sequences = self.model_config_dict.get("stop")
        if stop_sequences:
            data["stop"] = stop_sequences
        else:
            # default stop sequences to prevent repetition
            data["stop"] = [
                "<end_of_turn>",
                "<start_of_turn>",
                "<end_function_call>",
            ]

        try:
            response = self._client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API request failed: {e}")

    async def _acall_ollama_generate(self, prompt: str) -> str:
        r"""Async call Ollama's /api/generate endpoint with raw prompt.

        Args:
            prompt (str): The formatted prompt string.

        Returns:
            str: The model response text.

        Raises:
            RuntimeError: If the API request fails.
        """
        url = f"{self._url}/api/generate"

        options = {}
        if self.model_config_dict.get("temperature") is not None:
            options["temperature"] = self.model_config_dict["temperature"]
        if self.model_config_dict.get("top_p") is not None:
            options["top_p"] = self.model_config_dict["top_p"]
        if self.model_config_dict.get("top_k") is not None:
            options["top_k"] = self.model_config_dict["top_k"]
        if self.model_config_dict.get("num_predict") is not None:
            options["num_predict"] = self.model_config_dict["num_predict"]
        if self.model_config_dict.get("seed") is not None:
            options["seed"] = self.model_config_dict["seed"]

        data = {
            "model": str(self.model_type),
            "prompt": prompt,
            "raw": True,
            "stream": False,
        }

        if options:
            data["options"] = options

        # add default stop sequences if not provided
        stop_sequences = self.model_config_dict.get("stop")
        if stop_sequences:
            data["stop"] = stop_sequences
        else:
            # default stop sequences to prevent repetition
            data["stop"] = [
                "<end_of_turn>",
                "<start_of_turn>",
                "<end_function_call>",
            ]

        try:
            response = await self._async_client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API request failed: {e}")

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Run inference using FunctionGemma via Ollama.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): Not supported for
                FunctionGemma. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            ChatCompletion: The model response in OpenAI ChatCompletion format.
        """
        update_current_observation(
            input={
                "messages": messages,
                "tools": tools,
            },
            model=str(self.model_type),
            model_parameters=self.model_config_dict,
        )

        self._log_and_trace()

        prompt = self._format_messages(messages, tools)
        logger.debug(f"FunctionGemma prompt:\n{prompt}")

        response_text = self._call_ollama_generate(prompt)
        logger.debug(f"FunctionGemma response:\n{response_text}")

        response = self._to_chat_completion(
            response_text, str(self.model_type), tools
        )
        update_current_observation(usage=response.usage)
        return response

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Async run inference using FunctionGemma via Ollama.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): Not supported for
                FunctionGemma. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            ChatCompletion: The model response in OpenAI ChatCompletion format.
        """
        update_current_observation(
            input={
                "messages": messages,
                "tools": tools,
            },
            model=str(self.model_type),
            model_parameters=self.model_config_dict,
        )

        self._log_and_trace()

        prompt = self._format_messages(messages, tools)
        logger.debug(f"FunctionGemma prompt:\n{prompt}")

        response_text = await self._acall_ollama_generate(prompt)
        logger.debug(f"FunctionGemma response:\n{response_text}")

        response = self._to_chat_completion(
            response_text, str(self.model_type), tools
        )
        update_current_observation(usage=response.usage)
        return response

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode.

        FunctionGemma does not currently support streaming.

        Returns:
            bool: Always False for FunctionGemma.
        """
        return False
