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
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from camel.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolOutputContext:
    r"""Tool output context information.

    Contains all necessary information about a tool's output
    to enable flexible processing.
    """

    tool_name: str
    tool_call_id: str
    raw_result: Any
    agent_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolOutputProcessor(ABC):
    r"""Abstract base class for tool output processors.

    Tool output processors enable custom handling of tool execution results,
    such as cleaning, formatting, caching, or other transformations.
    """

    @abstractmethod
    def can_process(self, context: ToolOutputContext) -> bool:
        r"""Determine if this processor can handle the given tool output.

        Args:
            context: Tool output context information.

        Returns:
            True if this processor can handle the output, False otherwise.
        """
        pass

    @abstractmethod
    def process(self, context: ToolOutputContext) -> ToolOutputContext:
        r"""Process the tool output and return modified context.

        Args:
            context: Tool output context to process.

        Returns:
            Modified tool output context.
        """
        pass


class SnapshotCleaningProcessor(ToolOutputProcessor):
    r"""Processor for cleaning snapshot data from browser tools.

    This processor removes verbose DOM markers and references from
    snapshot outputs while preserving essential information.
    """

    def __init__(self, enable_cleaning: bool = True):
        r"""Initialize snapshot cleaning processor.

        Args:
            enable_cleaning: Whether to enable snapshot cleaning.
        """
        self.enable_cleaning = enable_cleaning

    def can_process(self, context: ToolOutputContext) -> bool:
        r"""Check if this tool output contains snapshot data to clean."""
        if not self.enable_cleaning:
            return False

        # Check if it's a browser tool or contains snapshot data
        return (
            'browser' in context.tool_name.lower()
            or self._contains_snapshot_data(context.raw_result)
        )

    def process(self, context: ToolOutputContext) -> ToolOutputContext:
        r"""Clean snapshot data from the tool output."""
        if not self.enable_cleaning:
            return context

        original_size = len(str(context.raw_result))
        cleaned_result = self._clean_snapshot_content(context.raw_result)
        cleaned_size = len(str(cleaned_result))

        # Create new context with cleaned data
        new_context = ToolOutputContext(
            tool_name=context.tool_name,
            tool_call_id=context.tool_call_id,
            raw_result=cleaned_result,
            agent_id=context.agent_id,
            timestamp=context.timestamp,
            metadata={
                **context.metadata,
                'original_size': original_size,
                'cleaned_size': cleaned_size,
                'processor': 'SnapshotCleaningProcessor',
            },
        )

        logger.debug(
            f"Cleaned snapshot output for {context.tool_name}: "
            f"{original_size} -> {cleaned_size} chars"
        )

        return new_context

    def _contains_snapshot_data(self, result: Any) -> bool:
        r"""Check if the result contains snapshot data."""
        result_str = str(result)
        return '- ' in result_str and '[ref=' in result_str

    def _clean_snapshot_content(self, content: Any) -> Any:
        r"""Clean snapshot content by removing prefixes, references, and
        deduplicating lines.

        This method identifies snapshot lines (containing element keywords or
        references) and cleans them while preserving non-snapshot content.
        It also handles JSON-formatted tool outputs with snapshot fields.

        Args:
            content: The original snapshot content.

        Returns:
            The cleaned content with deduplicated lines.
        """
        if isinstance(content, str):
            return self._clean_text_snapshot(content)

        try:
            # Try to parse as JSON and clean nested snapshot fields
            if isinstance(content, (dict, list)):
                # Already parsed JSON data
                cleaned_data = self._clean_json_snapshot(content)
                return (
                    json.dumps(cleaned_data, ensure_ascii=False, indent=2)
                    if cleaned_data != content
                    else content
                )
            else:
                # Try to parse string as JSON
                data = json.loads(str(content))
                cleaned_data = self._clean_json_snapshot(data)
                return (
                    json.dumps(cleaned_data, ensure_ascii=False, indent=2)
                    if cleaned_data != data
                    else str(content)
                )
        except (json.JSONDecodeError, TypeError):
            return self._clean_text_snapshot(str(content))

    def _clean_json_snapshot(self, data: Any) -> Any:
        r"""Clean JSON data containing snapshot fields."""
        if isinstance(data, dict):
            result = {}
            modified = False

            for key, value in data.items():
                if key == 'snapshot' and isinstance(value, str):
                    # Clean the snapshot field
                    try:
                        decoded_value = value.encode().decode('unicode_escape')
                    except (UnicodeDecodeError, AttributeError):
                        decoded_value = value

                    if self._needs_cleaning(decoded_value):
                        result[key] = self._clean_text_snapshot(decoded_value)
                        modified = True
                    else:
                        result[key] = value
                else:
                    cleaned_value = self._clean_json_snapshot(value)
                    result[key] = cleaned_value
                    if cleaned_value != value:
                        modified = True

            return result if modified else data
        elif isinstance(data, list):
            list_result: List[Any] = []
            modified = False
            for item in data:
                cleaned_item = self._clean_json_snapshot(item)
                list_result.append(cleaned_item)
                if cleaned_item != item:
                    modified = True
            return list_result if modified else data
        else:
            return data

    def _needs_cleaning(self, text: str) -> bool:
        r"""Check if text needs cleaning based on snapshot markers."""
        return (
            '- ' in text
            and '[ref=' in text
            or any(
                elem + ':' in text
                for elem in [
                    'generic',
                    'img',
                    'banner',
                    'list',
                    'listitem',
                    'search',
                    'navigation',
                ]
            )
        )

    def _clean_text_snapshot(self, content: str) -> str:
        r"""Clean plain text snapshot content.

        This method:
        - Removes indentation and empty lines
        - Deduplicates lines
        - Cleans snapshot-specific markers

        Args:
            content: The snapshot text to clean.

        Returns:
            Cleaned content with deduplicated lines.
        """
        lines = content.split('\n')
        cleaned_lines = []
        seen = set()

        for line in lines:
            stripped_line = line.strip()

            if not stripped_line:
                continue

            # Skip metadata lines (like "- /url:", "- /ref:")
            if re.match(r'^-?\s*/\w+\s*:', stripped_line):
                continue

            is_snapshot_line = '[ref=' in stripped_line or re.match(
                r'^(?:-\s+)?\w+(?:[\s:]|$)', stripped_line
            )

            if is_snapshot_line:
                cleaned = self._clean_snapshot_line(stripped_line)
                if cleaned and cleaned not in seen:
                    cleaned_lines.append(cleaned)
                    seen.add(cleaned)
            else:
                if stripped_line not in seen:
                    cleaned_lines.append(stripped_line)
                    seen.add(stripped_line)

        return '\n'.join(cleaned_lines)

    def _clean_snapshot_line(self, line: str) -> str:
        r"""Clean a single snapshot line by removing prefixes and references.

        This method handles snapshot lines in the format:
        - [prefix] "quoted text" [attributes] [ref=...]: description

        It preserves:
        - Quoted text content (including brackets inside quotes)
        - Description text after the colon

        It removes:
        - Line prefixes (e.g., "- button", "- tooltip", "generic:")
        - Attribute markers (e.g., [disabled], [ref=e47])
        - Lines with only element types
        - All indentation

        Args:
            line: The original line content.

        Returns:
            The cleaned line content, or empty string if line should be
                removed.
        """
        original = line.strip()
        if not original:
            return ''

        # Check if line is just an element type marker
        if re.match(r'^(?:-\s+)?\w+\s*:?\s*$', original):
            return ''

        # Remove element type prefix
        line = re.sub(r'^(?:-\s+)?\w+[\s:]+', '', original)

        # Remove bracket markers while preserving quoted text
        quoted_parts = []

        def save_quoted(match):
            quoted_parts.append(match.group(0))
            return f'__QUOTED_{len(quoted_parts)-1}__'

        line = re.sub(r'"[^"]*"', save_quoted, line)
        line = re.sub(r'\s*\[[^\]]+\]\s*', ' ', line)

        for i, quoted in enumerate(quoted_parts):
            line = line.replace(f'__QUOTED_{i}__', quoted)

        # Clean up formatting
        line = re.sub(r'\s+', ' ', line).strip()
        line = re.sub(r'\s*:\s*', ': ', line)
        line = line.lstrip(': ').strip()

        return '' if not line else line


class ToolOutputManager:
    r"""Manages tool output processing through registered processors.

    Coordinates multiple output processors to handle tool results.
    """

    def __init__(self):
        """Initialize tool output manager."""
        self.processors: List[ToolOutputProcessor] = []

    def register_processor(self, processor: ToolOutputProcessor) -> None:
        """Register an output processor.

        Args:
            processor: The processor to register.
        """
        if processor not in self.processors:
            self.processors.append(processor)
            logger.debug(
                f"Registered processor: {processor.__class__.__name__}"
            )

    def process_tool_output(
        self,
        tool_name: str,
        tool_call_id: str,
        raw_result: Any,
        agent_id: str,
        timestamp: Optional[float] = None,
    ) -> ToolOutputContext:
        r"""Process tool output through registered processors.

        Args:
            tool_name: Name of the tool that produced the output.
            tool_call_id: Unique identifier for the tool call.
            raw_result: Raw output from the tool.
            agent_id: ID of the agent that made the tool call.
            timestamp: Timestamp of the tool call.

        Returns:
            Processed tool output context.
        """
        if timestamp is None:
            timestamp = time.time()

        context = ToolOutputContext(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            raw_result=raw_result,
            agent_id=agent_id,
            timestamp=timestamp,
        )

        # Apply all applicable processors
        for processor in self.processors:
            try:
                if processor.can_process(context):
                    context = processor.process(context)
            except Exception as e:
                logger.warning(
                    f"Processor {processor.__class__.__name__} "
                    f"failed for tool {tool_name}: {e}"
                )

        return context
