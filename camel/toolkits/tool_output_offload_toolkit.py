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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit

if TYPE_CHECKING:
    from camel.agents import ChatAgent

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

    This toolkit allows agents to proactively manage memory by:
    1. Listing recent tool outputs that could be summarized/offloaded
    2. Summarizing specific tool outputs and storing originals externally
    3. Retrieving original content when needed

    Unlike automatic threshold-based approaches, this is agent-driven -
    the LLM decides when outputs are too large or no longer relevant
    and should be offloaded.

    Args:
        working_directory: Directory for storing offloaded content.
            Defaults to CAMEL_WORKDIR/tool_output_offload or
            ./tool_output_offload.
        timeout: Timeout for toolkit operations.
        min_output_length: Minimum character length for outputs to appear
            in list_offloadable_outputs. Lower values allow more outputs.
            (default: :obj:`1000`)
        summary_prompt_template: Custom template for summarization prompts.
            Use {tool_name} and {content} placeholders.

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
        summary_prompt_template: Optional[str] = None,
    ):
        BaseToolkit.__init__(self, timeout=timeout)
        RegisteredAgentToolkit.__init__(self)

        self.min_output_length = min_output_length
        self.summary_prompt_template = summary_prompt_template

        # Storage for offloaded outputs metadata
        self._offloaded_outputs: Dict[str, OffloadedOutput] = {}

        # Cache for list_offloadable_outputs to map index -> record info
        self._last_offloadable_list: List[Dict[str, Any]] = []

        # Setup storage directory
        self._setup_storage(working_directory)

        # Lazy-initialized summary agent
        self._summary_agent: Optional["ChatAgent"] = None

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

    def _get_summary_agent(self) -> "ChatAgent":
        r"""Get or create the summarization agent."""
        if self._summary_agent is None:
            from camel.agents import ChatAgent

            self._summary_agent = ChatAgent(
                system_message=(
                    "You are a summarization assistant. Create concise "
                    "summaries of tool outputs while preserving key "
                    "information, data points, and actionable details."
                ),
                model=None,  # Uses default model
                agent_id=f"{self.__class__.__name__}_summarizer",
            )
        return self._summary_agent

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
            # Access memory storage
            memory = self._agent.memory
            chat_history_block = getattr(memory, "_chat_history_block", None)
            if chat_history_block is None:
                # Try alternative access
                chat_history_block = getattr(
                    memory, "chat_history_block", None
                )
            if chat_history_block is None:
                logger.warning("Could not access chat history block")
                return []

            storage = getattr(chat_history_block, "storage", None)
            if storage is None:
                logger.warning("Could not access storage")
                return []

            # Load records
            record_dicts = storage.load()

            tool_outputs = []
            for idx, record in enumerate(record_dicts):
                msg = record.get("message", {})
                # Check if this is a FunctionCallingMessage with result
                if (
                    msg.get("__class__") == "FunctionCallingMessage"
                    and "result" in msg
                    and msg["result"] is not None
                ):
                    result_str = self._serialize_result(msg["result"])
                    tool_outputs.append(
                        {
                            "index": idx,
                            "uuid": record.get("uuid", ""),
                            "tool_name": msg.get("func_name", "unknown"),
                            "tool_call_id": msg.get("tool_call_id", ""),
                            "result": msg["result"],
                            "result_str": result_str,
                            "timestamp": record.get("timestamp", 0),
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

    def _generate_summary(self, content: str, tool_name: str) -> str:
        r"""Generate a summary of tool output content using LLM.

        Args:
            content: The tool output content to summarize.
            tool_name: Name of the tool that produced the output.

        Returns:
            Generated summary string.
        """
        summary_agent = self._get_summary_agent()
        summary_agent.reset()

        prompt = self._create_summary_prompt(content, tool_name)
        response = summary_agent.step(prompt)

        return response.msgs[-1].content.strip()

    def _create_summary_prompt(self, content: str, tool_name: str) -> str:
        r"""Create the summarization prompt."""
        if self.summary_prompt_template:
            return self.summary_prompt_template.format(
                tool_name=tool_name,
                content=content,
            )

        return f"""Summarize the following output from the '{tool_name}' tool.

Create a concise summary that:
- Preserves key information, data points, and findings
- Notes important identifiers, values, or references
- Indicates the type and structure of the content
- Is useful for understanding what the original output contained

Keep the summary under 500 characters if possible.

Tool Output:
{content}

Summary:"""

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
        tool_name: str,
        tool_call_id: str,
    ) -> bool:
        r"""Replace a memory record's result with summarized content.

        Args:
            record_uuid: UUID of the record to replace.
            new_result: New result content (summary with reference).
            tool_name: Tool name for the message.
            tool_call_id: Tool call ID for the message.

        Returns:
            True if replacement succeeded, False otherwise.
        """
        if self._agent is None:
            return False

        try:
            memory = self._agent.memory
            chat_history_block = getattr(memory, "_chat_history_block", None)
            if chat_history_block is None:
                chat_history_block = getattr(
                    memory, "chat_history_block", None
                )
            if chat_history_block is None:
                return False

            storage = getattr(chat_history_block, "storage", None)
            if storage is None:
                return False

            # Load existing records
            existing_records = storage.load()

            # Find and update the target record
            updated = False
            for record in existing_records:
                if record.get("uuid") == record_uuid:
                    msg = record.get("message", {})
                    if msg.get("__class__") == "FunctionCallingMessage":
                        msg["result"] = new_result
                        updated = True
                        break

            if not updated:
                return False

            # Save back to storage
            storage.clear()
            storage.save(existing_records)

            return True

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
    ) -> str:
        r"""Summarize a tool output and offload the original to storage.

        This method:
        1. Generates a summary of the specified tool output
        2. Stores the original content to disk with a unique ID
        3. Replaces the tool output in memory with the summary + reference

        Args:
            index: Index from list_offloadable_outputs() to offload.

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
            # Generate summary
            summary = self._generate_summary(original_content, tool_name)

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
            if self._replace_in_memory(
                record_uuid, replacement, tool_name, tool_call_id
            ):
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
