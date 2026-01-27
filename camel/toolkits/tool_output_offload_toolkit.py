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
from camel.toolkits.tool_output_offload_templates import (
    OFFLOAD_SUCCESS,
    OFFLOADABLE_LIST_FOOTER,
    OFFLOADABLE_LIST_HEADER,
    OFFLOADABLE_OUTPUT_ITEM,
    REPLACEMENT_CONTENT,
)

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
            in list_offloadable_tool_outputs. Lower values allow more outputs.
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

        # Cache for list_offloadable_tool_outputs to map index -> record info
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
    ) -> None:
        r"""Replace a memory record's result with summarized content.

        Args:
            record_uuid: UUID of the record to replace.
            new_result: New result content (summary with reference).

        Raises:
            ValueError: If agent is not set, record not found, or record
                has no message/result attribute.
        """
        if self._agent is None:
            raise ValueError("Agent is not set.")

        memory = self._agent.memory
        records = memory.get_records()

        for record in records:
            if str(getattr(record, "uuid", "")) != record_uuid:
                continue
            msg = getattr(record, "message", None)
            if msg is None:
                raise ValueError(
                    f"Record {record_uuid} has no message attribute."
                )
            new_record = record.model_copy(deep=True)
            if hasattr(new_record.message, "result"):
                new_record.message.result = new_result
            else:
                raise ValueError(
                    f"Record {record_uuid} message has no result attribute."
                )
            memory.replace_record_by_uuid(record_uuid, new_record)
            return

        raise ValueError(f"Record with UUID {record_uuid} not found.")

    # ========= PUBLIC TOOL METHODS =========

    def list_offloadable_tool_outputs(
        self,
        min_length: Optional[int] = None,
        max_results: int = 10,
        preview_length: int = 100,
    ) -> str:
        r"""List tool outputs in memory that can be offloaded to save context.

        Call this tool to inspect recent tool outputs stored in the agent's
        memory and identify large candidates suitable for offloading. This
        does not modify memory; it only returns a formatted list with indexes
        you can use for offloading.

        After calling this, use offload_tool_output_with_summary() with the
        returned index to offload a specific output. The index values are
        specific to the last call and may change if memory changes.

        Args:
            min_length: Minimum character length to consider for offloading.
                Smaller outputs are filtered out. Uses instance default if not
                specified. (default: :obj:`None`)
            max_results: Maximum number of outputs to list.
                (default: :obj:`10`)
            preview_length: Maximum length of the preview text shown for each
                output. (default: :obj:`100`)

        Returns:
            str: Formatted list showing index, tool name, output length, and
                preview for each candidate. Use the index with
                offload_tool_output_with_summary() to offload.
        """
        if min_length is None:
            min_length = self.min_output_length

        tool_outputs = self._get_tool_outputs_from_memory()

        # Filter by length
        candidates = [o for o in tool_outputs if o["length"] >= min_length]
        candidates = candidates[:max_results]

        # Cache for offload_tool_output_with_summary
        self._last_offloadable_list = candidates

        if not candidates:
            return (
                f"No tool outputs found with length >= {min_length} "
                f"characters. "
                f"Total tool outputs in memory: {len(tool_outputs)}."
            )

        # Format output
        lines = [
            OFFLOADABLE_LIST_HEADER.format(
                count=len(candidates), min_length=min_length
            )
        ]

        for i, output in enumerate(candidates):
            preview = output["result_str"][:preview_length]
            if len(output["result_str"]) > preview_length:
                preview += "..."
            lines.append(
                OFFLOADABLE_OUTPUT_ITEM.format(
                    index=i,
                    tool_name=output["tool_name"],
                    length=output["length"],
                    preview=preview,
                )
            )

        lines.append(OFFLOADABLE_LIST_FOOTER)

        return "\n".join(lines)

    def offload_tool_output_with_summary(
        self,
        index: int,
        summary: str,
    ) -> str:
        r"""Offload a tool output by replacing it with a summary in memory.

        Call this after list_offloadable_tool_outputs() to offload a specific
        output. You must provide a concise summary that captures the essential
        information from the original output. The summary replaces the original
        content in memory and includes a reference for later retrieval.

        The original content is saved to disk and can be retrieved later using
        retrieve_offloaded_tool_output() with the returned offload_id.

        Args:
            index: Index of the output to offload (from
                list_offloadable_tool_outputs() results).
            summary: A concise summary you create that captures the key
                information from the original output. This replaces the
                original in memory.

        Returns:
            str: Success message with offload_id for later retrieval, or error
                message if failed.
        """
        if not self._last_offloadable_list:
            return (
                "No offloadable outputs cached. "
                "Please run list_offloadable_tool_outputs() first."
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
            offload_id = str(uuid.uuid4())

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
            replacement = REPLACEMENT_CONTENT.format(
                offload_id=offload_id,
                summary=summary,
                original_length=len(original_content),
            )

            # Replace in memory
            try:
                self._replace_in_memory(record_uuid, replacement)
            except ValueError as e:
                logger.error(f"Failed to replace in memory: {e}")
                return (
                    f"Failed to update memory: {e}\n"
                    f"Original content saved with ID: {offload_id}, "
                    f"but memory was not modified."
                )

            # Clear cache since memory changed
            self._last_offloadable_list = []

            return OFFLOAD_SUCCESS.format(
                tool_name=tool_name,
                offload_id=offload_id,
                original_length=len(original_content),
                summary_length=len(summary),
            )

        except Exception as e:
            logger.error(f"Error during offload: {e}")
            return f"Error during offload: {e}"

    def retrieve_offloaded_tool_output(
        self,
        offload_id: str,
    ) -> Dict[str, Any]:
        r"""Retrieve full original content of a previously offloaded output.

        Call this when you need to access the complete original tool output
        that was previously offloaded. The offload_id was returned when you
        called offload_tool_output_with_summary(). This does not modify memory;
        it only returns the stored content.

        The retrieved content will be sent back to you for processing.

        Args:
            offload_id (str): The unique ID that was returned when the output
                was offloaded via offload_tool_output_with_summary().

        Returns:
            Dict[str, Any]: A dictionary containing:
                - offload_id (str): The unique offload identifier.
                - tool_name (str): Name of the tool that produced the output.
                - content (str): The full original tool output content.
                - original_length (int): Character length of the content.
                - summary (str): The summary created during offload.
                - file_path (str): Path where the content is stored.
                - offloaded_at (str): ISO format timestamp of when offloaded.
                - error (str, optional): Error message if retrieval failed.
        """
        # Check in-memory cache first
        metadata: Optional[OffloadedOutput] = None
        if offload_id in self._offloaded_outputs:
            metadata = self._offloaded_outputs[offload_id]
        else:
            # Try to load from disk
            meta_file = self.outputs_dir / f"{offload_id}.meta.json"
            if meta_file.exists():
                try:
                    meta_data = json.loads(
                        meta_file.read_text(encoding="utf-8")
                    )
                    metadata = OffloadedOutput(**meta_data)
                    # Cache it
                    self._offloaded_outputs[offload_id] = metadata
                except Exception as e:
                    logger.error(
                        f"Error reading metadata file for "
                        f"offload ID: {offload_id}: {e}"
                    )
                    return {
                        "offload_id": offload_id,
                        "error": f"Error reading metadata for offload ID: "
                        f"{offload_id}",
                    }
            else:
                return {
                    "offload_id": offload_id,
                    "error": f"Offload ID '{offload_id}' not found. "
                    f"Use list_offloaded_tool_outputs() to see available IDs.",
                }

        # Read content file
        file_path = metadata.file_path
        content_file = Path(file_path)
        if not content_file.exists():
            content_file = self.outputs_dir / f"{offload_id}.txt"

        if content_file.exists():
            try:
                content = content_file.read_text(encoding="utf-8")
                return {
                    "offload_id": offload_id,
                    "tool_name": metadata.tool_name,
                    "content": content,
                    "original_length": metadata.original_length,
                    "summary": metadata.summary,
                    "file_path": metadata.file_path,
                    "offloaded_at": metadata.offloaded_at,
                }
            except Exception as e:
                logger.error(f"Error reading content file: {e}")
                return {
                    "offload_id": offload_id,
                    "error": f"Error reading content file: {e}",
                }
        else:
            return {
                "offload_id": offload_id,
                "error": f"File not found for offload ID: {offload_id}",
            }

    def list_offloaded_tool_outputs(self) -> List[Dict[str, Any]]:
        r"""List all tool outputs that have been offloaded in this session.

        Call this to see what outputs have been previously offloaded and their
        offload_ids. Use the offload_id with retrieve_offloaded_tool_output()
        to get the full original content when needed.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing:
                - offload_id (str): Unique identifier for retrieval.
                - tool_name (str): Name of the tool that produced the output.
                - original_length (int): Character length of original content.
                - summary (str): The summary created during offload.
                - file_path (str): Path where the content is stored.
                - offloaded_at (str): ISO format timestamp of when offloaded.
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

        result: List[Dict[str, Any]] = []
        for offload_id, meta in self._offloaded_outputs.items():
            result.append(
                {
                    "offload_id": offload_id,
                    "tool_name": meta.tool_name,
                    "original_length": meta.original_length,
                    "summary": meta.summary,
                    "file_path": meta.file_path,
                    "offloaded_at": meta.offloaded_at,
                }
            )

        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.list_offloadable_tool_outputs),
            FunctionTool(self.offload_tool_output_with_summary),
            FunctionTool(self.retrieve_offloaded_tool_output),
            FunctionTool(self.list_offloaded_tool_outputs),
        ]
