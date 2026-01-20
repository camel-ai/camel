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
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit

logger = get_logger(__name__)


@dataclass
class OffloadedOutput:
    r"""Metadata for an offloaded tool output.

    Attributes:
        offload_id: Unique identifier for the offloaded output.
        tool_name: Name of the tool that produced the output.
        tool_call_id: The tool call ID from the original execution.
        record_uuid: UUID of the original memory record.
        original_length: Character length of the original content.
        summary: Generated summary of the content.
        file_path: Path where original content is stored.
        timestamp: Original tool execution timestamp.
        offloaded_at: ISO format datetime when offloaded.
    """

    offload_id: str
    tool_name: str
    tool_call_id: str
    record_uuid: str
    original_length: int
    summary: str
    file_path: str
    timestamp: float
    offloaded_at: str


class ToolOutputOffloadToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""A toolkit for agent-driven tool output summarization and offloading.

    This toolkit allows agents to manage memory by:
    1. Listing recent tool outputs that could be summarized/offloaded
    2. Summarizing specific tool outputs and storing originals externally
    3. Retrieving original content when needed

    Args:
        working_directory: Directory for storing offloaded content.
            Defaults to CAMEL_WORKDIR/tool_output_offload or
            ./tool_output_offload.
        timeout: Timeout for toolkit operations.
        min_output_length: Minimum character length for outputs to appear
            in list_offloadable_outputs. Lower values allow more outputs.
            (default: :obj:`1000`)

    Example:
        >>> from camel.agents import ChatAgent
        >>> from camel.toolkits import ToolOutputOffloadToolkit, SearchToolkit
        >>>
        >>> offload_toolkit = ToolOutputOffloadToolkit()
        >>> agent = ChatAgent(
        ...     tools=SearchToolkit().get_tools() + offload_toolkit.get_tools(),
        ...     toolkits_to_register_agent=[offload_toolkit],
        ... )
    """  # noqa: E501

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        min_output_length: int = 1000,
    ):
        BaseToolkit.__init__(self, timeout=timeout)
        RegisteredAgentToolkit.__init__(self)

        self.min_output_length = min_output_length

        # Storage for offloaded outputs metadata
        self._offloaded_outputs: Dict[str, OffloadedOutput] = {}

        # Cache for list_offloadable_outputs to map index -> record info
        self._last_offloadable_list: List[Dict[str, Any]] = []

        # Setup storage directory
        self._setup_storage(working_directory)

    def _setup_storage(self, working_directory: Optional[str]) -> None:
        r"""Initialize storage paths and create session directories."""
        if working_directory:
            base_dir = Path(working_directory)
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                base_dir = Path(camel_workdir) / "tool_output_offload"
            else:
                base_dir = Path("tool_output_offload")

        # Create session directory with timestamp
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = base_dir / f"session_{session_id}"
        self.outputs_dir = self.session_dir / "outputs"

        # Create directories
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Index file path
        self.index_file = self.session_dir / "index.json"

        logger.info(f"ToolOutputOffloadToolkit storage: {self.session_dir}")

    def _get_tool_outputs_from_memory(self) -> List[Dict[str, Any]]:
        r"""Extract tool output records from agent's memory.

        Returns:
            List of dicts with keys: index, uuid, tool_name, tool_call_id,
            result, timestamp, length.
        """
        if self._agent is None:
            logger.warning("No agent registered with toolkit")
            return []

        try:
            memory = self._agent.memory
            if not hasattr(memory, "get_records"):
                logger.warning("Memory does not support get_records()")
                return []

            records = memory.get_records()
            tool_outputs = []
            for idx, record in enumerate(records):
                msg = getattr(record, "message", None)
                if (
                    msg is not None
                    and msg.__class__.__name__ == "FunctionCallingMessage"
                    and getattr(msg, "result", None) is not None
                ):
                    result = msg.result
                    result_str = self._serialize_result(result)
                    tool_outputs.append(
                        {
                            "index": idx,
                            "uuid": str(getattr(record, "uuid", "")),
                            "tool_name": getattr(msg, "func_name", "unknown"),
                            "tool_call_id": getattr(msg, "tool_call_id", ""),
                            "result": result,
                            "result_str": result_str,
                            "timestamp": getattr(record, "timestamp", 0),
                            "length": len(result_str),
                        }
                    )

            return tool_outputs

        except Exception as e:
            logger.error(f"Error accessing memory: {e}")
            return []

    def _serialize_result(self, result: Any) -> str:
        r"""Serialize a tool result to string."""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(result)

    def _store_original_content(
        self,
        content: str,
        offload_id: str,
        metadata: OffloadedOutput,
    ) -> str:
        r"""Store original content to file storage.

        Args:
            content: The original content to store.
            offload_id: Unique ID for the offloaded output.
            metadata: Metadata about the offloaded output.

        Returns:
            Path where content was stored.
        """
        # Store original content
        content_file = self.outputs_dir / f"{offload_id}.txt"
        content_file.write_text(content, encoding="utf-8")

        # Store metadata
        meta_file = self.outputs_dir / f"{offload_id}.meta.json"
        meta_file.write_text(
            json.dumps(asdict(metadata), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Update index
        self._offloaded_outputs[offload_id] = metadata
        self._save_index()

        return str(content_file)

    def _save_index(self) -> None:
        r"""Save the index of all offloaded outputs."""
        index_data = {
            oid: asdict(meta) for oid, meta in self._offloaded_outputs.items()
        }
        self.index_file.write_text(
            json.dumps(index_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _replace_in_memory(
        self,
        record_uuid: str,
        new_result: str,
    ) -> bool:
        r"""Replace a memory record's result with summarized content.

        Args:
            record_uuid: UUID of the record to replace.
            new_result: New result content (summary with reference).

        Returns:
            True if replacement succeeded, False otherwise.
        """
        if self._agent is None:
            return False

        try:
            memory = self._agent.memory
            if not (
                hasattr(memory, "replace_record_by_uuid")
                and hasattr(memory, "get_records")
            ):
                logger.warning(
                    "Memory does not support record replacement APIs."
                )
                return False

            records = memory.get_records()
            for record in records:
                if str(getattr(record, "uuid", "")) != record_uuid:
                    continue
                msg = getattr(record, "message", None)
                if msg is None:
                    return False
                new_record = record.model_copy(deep=True)
                if hasattr(new_record.message, "result"):
                    new_record.message.result = new_result
                else:
                    return False
                return memory.replace_record_by_uuid(record_uuid, new_record)

            return False

        except Exception as e:
            logger.error(f"Error replacing in memory: {e}")
            return False

    # ========= PUBLIC TOOL METHODS =========

    def list_offloadable_outputs(
        self,
        min_length: Optional[int] = None,
        max_results: int = 10,
    ) -> str:
        r"""List recent tool outputs that could be offloaded.

        Returns information about tool outputs in memory that are candidates
        for offloading (summarization + storage), ordered by size descending.

        Args:
            min_length: Minimum character length to consider. Uses instance
                default if not specified. (default: :obj:`None`)
            max_results: Maximum number of outputs to list. (default: :obj:`10`)

        Returns:
            str: Formatted string with tool output info (index, tool_name,
                length, preview). Returns message if no candidates found.
        """  # noqa: E501
        if min_length is None:
            min_length = self.min_output_length

        tool_outputs = self._get_tool_outputs_from_memory()

        # Filter by length and sort by size descending
        candidates = [o for o in tool_outputs if o["length"] >= min_length]
        candidates.sort(key=lambda x: x["length"], reverse=True)
        candidates = candidates[:max_results]

        # Cache for summarize_and_offload
        self._last_offloadable_list = candidates

        if not candidates:
            return (
                f"No tool outputs found with length >= {min_length} "
                f"characters. "
                f"Total tool outputs in memory: {len(tool_outputs)}."
            )

        # Format output
        lines = [
            f"Found {len(candidates)} offloadable tool outputs "
            f"(min length: {min_length}):\n"
        ]

        for i, output in enumerate(candidates):
            preview = output["result_str"][:100]
            if len(output["result_str"]) > 100:
                preview += "..."
            lines.append(
                f"\n[{i}] Tool: {output['tool_name']}\n"
                f"    Length: {output['length']} chars\n"
                f"    Preview: {preview}"
            )

        lines.append(
            "\n\nUse summarize_and_offload(index) to offload a specific "
            "output."
        )

        return "\n".join(lines)

    def summarize_and_offload(
        self,
        index: int,
        summary: str,
    ) -> str:
        r"""Summarize a tool output and offload the original to storage.

        This method:
        1. Generates a summary of the specified tool output
        2. Stores the original content to disk with a unique ID
        3. Replaces the tool output in memory with the summary + reference

        Args:
            index: Index from list_offloadable_outputs() to offload.
            summary: Summary created by the agent in the same turn.

        Returns:
            str: Success message with offload_id, or error message if failed.
        """
        if not self._last_offloadable_list:
            return (
                "No offloadable outputs cached. "
                "Please run list_offloadable_outputs() first."
            )

        if index < 0 or index >= len(self._last_offloadable_list):
            return (
                f"Invalid index {index}. "
                f"Valid range: 0-{len(self._last_offloadable_list) - 1}"
            )

        output = self._last_offloadable_list[index]
        original_content = output["result_str"]
        tool_name = output["tool_name"]
        record_uuid = output["uuid"]
        tool_call_id = output["tool_call_id"]
        timestamp = output["timestamp"]

        try:
            if not summary:
                return (
                    "Summary is required. Provide a concise summary in the "
                    "summary parameter."
                )

            # Create offload ID
            offload_id = str(uuid.uuid4())[:8]

            # Create metadata
            metadata = OffloadedOutput(
                offload_id=offload_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                record_uuid=record_uuid,
                original_length=len(original_content),
                summary=summary,
                file_path=str(self.outputs_dir / f"{offload_id}.txt"),
                timestamp=timestamp,
                offloaded_at=datetime.now().isoformat(),
            )

            # Store original content
            self._store_original_content(
                original_content, offload_id, metadata
            )

            # Create replacement content
            replacement = (
                f"[SUMMARIZED OUTPUT - ID: {offload_id}]\n\n"
                f"Summary: {summary}\n\n"
                f"Original length: {len(original_content)} chars\n"
                f'Use retrieve_offloaded_output("{offload_id}") '
                f"to get full content."
            )

            # Replace in memory
            if self._replace_in_memory(record_uuid, replacement):
                # Clear cache since memory changed
                self._last_offloadable_list = []

                return (
                    f"Successfully offloaded output from '{tool_name}'.\n"
                    f"Offload ID: {offload_id}\n"
                    f"Original: {len(original_content)} chars -> "
                    f"Summary: {len(summary)} chars\n"
                    f"Use retrieve_offloaded_output(\"{offload_id}\") "
                    f"to retrieve original."
                )
            else:
                return (
                    f"Failed to update memory. Original content saved with "
                    f"ID: {offload_id}, but memory was not modified."
                )

        except Exception as e:
            logger.error(f"Error during offload: {e}")
            return f"Error during offload: {e}"

    def retrieve_offloaded_output(
        self,
        offload_id: str,
    ) -> str:
        r"""Retrieve the original content of an offloaded tool output.

        Use this when you need the full original content that was previously
        summarized and offloaded.

        Args:
            offload_id: The unique ID returned when the output was offloaded.

        Returns:
            str: The original tool output content, or error message if not
                found.
        """
        # Check in-memory cache
        if offload_id in self._offloaded_outputs:
            file_path = self._offloaded_outputs[offload_id].file_path
        else:
            # Try to load from disk
            meta_file = self.outputs_dir / f"{offload_id}.meta.json"
            if meta_file.exists():
                try:
                    meta_data = json.loads(
                        meta_file.read_text(encoding="utf-8")
                    )
                    file_path = meta_data.get("file_path", "")
                except Exception:
                    return (
                        f"Error reading metadata for offload ID: {offload_id}"
                    )
            else:
                return (
                    f"Offload ID '{offload_id}' not found. "
                    f"Use list_offloaded_outputs() to see available IDs."
                )

        # Read content file
        content_file = Path(file_path)
        if not content_file.exists():
            content_file = self.outputs_dir / f"{offload_id}.txt"

        if content_file.exists():
            try:
                content = content_file.read_text(encoding="utf-8")
                return (
                    f"[Retrieved Original Content - ID: {offload_id}]\n\n"
                    f"{content}"
                )
            except Exception as e:
                return f"Error reading content file: {e}"
        else:
            return f"Content file not found for offload ID: {offload_id}"

    def list_offloaded_outputs(self) -> str:
        r"""List all previously offloaded outputs in current session.

        Returns:
            str: Formatted string with offload_id, tool_name, summary preview,
                and offload timestamp for each stored output.
        """
        if not self._offloaded_outputs:
            # Try to load from index file
            if self.index_file.exists():
                try:
                    index_data = json.loads(
                        self.index_file.read_text(encoding="utf-8")
                    )
                    for oid, meta in index_data.items():
                        self._offloaded_outputs[oid] = OffloadedOutput(**meta)
                except Exception as e:
                    logger.error(f"Error loading index: {e}")

        if not self._offloaded_outputs:
            return "No outputs have been offloaded in this session."

        lines = [
            f"Offloaded outputs ({len(self._offloaded_outputs)} total):\n"
        ]

        for offload_id, meta in self._offloaded_outputs.items():
            summary_preview = meta.summary[:80]
            if len(meta.summary) > 80:
                summary_preview += "..."

            lines.append(
                f"\n[{offload_id}] Tool: {meta.tool_name}\n"
                f"    Original size: {meta.original_length} chars\n"
                f"    Summary: {summary_preview}\n"
                f"    Offloaded at: {meta.offloaded_at}"
            )

        return "\n".join(lines)

    def get_offload_info(self) -> str:
        r"""Get information about current offload status and storage.

        Returns:
            str: Summary including: number of offloaded outputs, storage
                directory, total storage used, and number of potential
                candidates in memory.
        """
        # Count offloaded
        offloaded_count = len(self._offloaded_outputs)

        # Calculate storage used
        storage_bytes = 0
        if self.outputs_dir.exists():
            for f in self.outputs_dir.iterdir():
                if f.is_file():
                    storage_bytes += f.stat().st_size

        # Count candidates in memory
        tool_outputs = self._get_tool_outputs_from_memory()
        candidates = [
            o for o in tool_outputs if o["length"] >= self.min_output_length
        ]

        storage_kb = storage_bytes / 1024

        return (
            f"Tool Output Offload Status:\n"
            f"  Offloaded outputs: {offloaded_count}\n"
            f"  Storage directory: {self.session_dir}\n"
            f"  Storage used: {storage_kb:.1f} KB\n"
            f"  Tool outputs in memory: {len(tool_outputs)}\n"
            f"  Offloadable candidates (>={self.min_output_length} chars): "
            f"{len(candidates)}\n"
            f"  Min output length threshold: {self.min_output_length} chars"
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.list_offloadable_outputs),
            FunctionTool(self.summarize_and_offload),
            FunctionTool(self.retrieve_offloaded_output),
            FunctionTool(self.list_offloaded_outputs),
            FunctionTool(self.get_offload_info),
        ]
