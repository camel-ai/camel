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

from __future__ import annotations

import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Fallback tool name when we can't identify which tool the model tried to call
UNKNOWN_TOOL_NAME = "unknown_tool"


def _make_tool_call_id() -> str:
    """Generate a unique tool call ID."""
    return f"call_{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True, slots=True)
class ToolCallParseResult:
    """A parsed tool call request.

    For successful parses: name and input are populated, raw is None.
    For parse errors: name is extracted or UNKNOWN_TOOL_NAME, raw contains the unparseable content.
    """

    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    raw: str | None = None

    @property
    def is_error(self) -> bool:
        """Check if this represents a parse error."""
        return self.raw is not None

    @property
    def payload(self) -> str:
        """Get the tool call payload string to pass to the tool executor.

        For successful parses, returns JSON-encoded input.
        For errors, returns the raw content (so model sees its mistake).
        """
        if self.is_error:
            return self.raw or ""
        return json.dumps(self.input)


class ToolCallParser(ABC):
    """Base class for tool call parsers.

    Subclasses implement `parse` to extract tool calls from model output.
    Only JSONDecodeError is handled; Strands validates arguments downstream.

    Example:
        >>> parser = HermesToolCallParser()
        >>> results = parser.parse('<tool_call>{"name": "foo", "arguments": {}}</tool_call>')
        >>> print(results[0].name)
        foo
    """

    @property
    def message_separator(self) -> str:
        """Separator between messages in the chat template.

        Different tokenizers use different separators between messages.
        This is used during incremental tokenization to ensure the TITO
        trajectory matches what `apply_chat_template` would produce.

        Default is no separator.
        """
        return ""

    @abstractmethod
    def parse(self, text: str) -> list[ToolCallParseResult]:
        """Parse tool calls from model output text.

        Args:
            text: Model output text.

        Returns:
            List of parsed tool call results.
        """
        ...

    def __call__(self, text: str) -> list[dict[str, Any]]:
        """Parse tool calls (callable interface for backwards compatibility).

        Args:
            text: Model output text.

        Returns:
            List of successful tool calls as dicts.
        """
        results = self.parse(text)
        return [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in results if not tc.is_error]


class HermesToolCallParser(ToolCallParser):
    """Parser for Hermes/Qwen XML tool call format.

    Format: <tool_call>{"name": "func", "arguments": {"arg": value}}</tool_call>

    Used by:
    - Qwen/Qwen2/Qwen3 models
    - NousResearch/Hermes models
    - Models using similar XML-wrapped JSON tool call format

    Only handles JSONDecodeError; Strands validates arguments against tool schemas.

    Chat Template Notes:
        Qwen3's chat template uses newline as separator between messages:
        `<|im_start|>role\\ncontent<|im_end|>\\n<|im_start|>...`
        The message_separator property returns "\\n" to match this format.

    Attributes:
        bot_token: Opening tag for tool calls (default: "<tool_call>").
        eot_token: Closing tag for tool calls (default: "</tool_call>").
    """

    DEFAULT_BOT_TOKEN = "<tool_call>"  # tool call start tag
    DEFAULT_EOT_TOKEN = "</tool_call>"  # tool call end tag
    _NAME_PATTERN = re.compile(r'"name"\s*:\s*"([^"]+)"')  # tool call name regex

    def __init__(
        self,
        bot_token: str = DEFAULT_BOT_TOKEN,
        eot_token: str = DEFAULT_EOT_TOKEN,
    ) -> None:
        """Initialize the parser with optional custom tokens.

        Args:
            bot_token: Custom opening tag (default: "<tool_call>").
            eot_token: Custom closing tag (default: "</tool_call>").
        """
        self.bot_token = bot_token
        self.eot_token = eot_token
        self._pattern = re.compile(
            rf"{re.escape(self.bot_token)}\s*(.*?)\s*{re.escape(self.eot_token)}",
            re.DOTALL,
        )

    @property
    def message_separator(self) -> str:
        """Separator between messages in the chat template.

        Different tokenizers use different separators between messages.
        This is used during incremental tokenization to ensure the TITO
        trajectory matches what `apply_chat_template` would produce.

        Qwen models use newline `\n` as separator between messages.
        """
        return "\n"

    def parse(self, text: str) -> list[ToolCallParseResult]:
        """Parse tool calls from model output.

        Args:
            text: Model output text.

        Returns:
            List of tool call results (successful and errors).
        """
        tool_calls: list[ToolCallParseResult] = []

        for match in self._pattern.finditer(text):
            raw_content = match.group(1).strip()
            tool_call_id = _make_tool_call_id()

            # Only handle JSONDecodeError - let Strands validate the rest
            try:
                call_json = json.loads(raw_content)
            except json.JSONDecodeError as e:
                tool_calls.append(self._make_error_tool_call(raw_content, tool_call_id, e))
                continue

            # Extract name and arguments - be lenient, let Strands validate
            if isinstance(call_json, dict):
                name = call_json.get("name")
                arguments = call_json.get("arguments", {})
            else:
                name = None
                arguments = {}

            # Need a string name to yield toolUse event
            if not name or not isinstance(name, str):
                tool_calls.append(self._make_error_tool_call(raw_content, tool_call_id, ValueError("missing name")))
                continue

            # Pass arguments as-is - Strands validates against tool schema
            tool_calls.append(
                ToolCallParseResult(
                    id=tool_call_id,
                    name=name,
                    input=arguments if isinstance(arguments, dict) else {},
                )
            )

        return tool_calls

    def _make_error_tool_call(
        self,
        raw_content: str,
        tool_call_id: str,
        error: Exception,
    ) -> ToolCallParseResult:
        """Create an error tool call for parse failures."""
        # Try to extract tool name even from malformed JSON
        name_match = self._NAME_PATTERN.search(raw_content)
        name = name_match.group(1) if name_match else UNKNOWN_TOOL_NAME

        logger.warning(f"Tool call parse error: {error}")

        return ToolCallParseResult(
            id=tool_call_id,
            name=name,
            input={},
            raw=raw_content,
        )
