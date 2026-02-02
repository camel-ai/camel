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

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.tool_output_offload_templates import (
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
    r"""A toolkit for automatic tool output offloading and retrieval.

    This toolkit automatically offloads large tool outputs to disk storage
    when they exceed a configurable threshold, replacing them with summaries
    in memory. The agent can then retrieve the full content when needed.

    Key features:
    1. Automatic offloading when tool outputs exceed threshold
    2. Configurable summary length for replaced content
    3. Retrieval of original content via offload_id
    4. Listing of all offloaded outputs in the session

    Args:
        working_directory: Directory for storing offloaded content.
            Defaults to CAMEL_WORKDIR/tool_output_offload or
            ./tool_output_offload.
        timeout: Timeout for toolkit operations.
        auto_offload_threshold: Character length threshold for automatic
            offloading. Tool outputs exceeding this length will be
            automatically offloaded. Set to 0 to disable auto-offload.
            (default: :obj:`5000`)
        max_summary_length: Maximum character length for auto-generated
            summaries. The summary is created by truncating the original
            content. (default: :obj:`500`)

    Example:
        >>> from camel.agents import ChatAgent
        >>> from camel.toolkits import ToolOutputOffloadToolkit, SearchToolkit
        >>>
        >>> offload_toolkit = ToolOutputOffloadToolkit(
        ...     auto_offload_threshold=3000,
        ...     max_summary_length=300,
        ... )
        >>> agent = ChatAgent(
        ...     tools=SearchToolkit().get_tools() + offload_toolkit.get_tools(),
        ...     toolkits_to_register_agent=[offload_toolkit],
        ... )
    """  # noqa: E501

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        auto_offload_threshold: int = 5000,
        max_summary_length: int = 500,
    ):
        BaseToolkit.__init__(self, timeout=timeout)
        RegisteredAgentToolkit.__init__(self)

        self.auto_offload_threshold = auto_offload_threshold
        self.max_summary_length = max_summary_length

        # Storage for offloaded outputs metadata
        self._offloaded_outputs: Dict[str, OffloadedOutput] = {}

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

    def register_agent(self, agent: "ChatAgent") -> None:
        r"""Register a ChatAgent and install this toolkit as the tool output
        processor.

        This method overrides the base class to additionally install this
        toolkit's `process_tool_output` method as the agent's tool output
        processor. This allows automatic offloading of large tool outputs
        without requiring a dedicated constructor parameter in ChatAgent.

        Args:
            agent (ChatAgent): The ChatAgent instance to register.
        """
        super().register_agent(agent)
        # Install this toolkit as the agent's tool output processor
        agent._tool_output_processor = self.process_tool_output
        logger.info(
            f"Installed {self.__class__.__name__} as tool output processor"
        )

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

    def _generate_summary(self, content: str) -> str:
        r"""Generate a summary by truncating content to max_summary_length.

        Args:
            content: The original content to summarize.

        Returns:
            str: Truncated content with ellipsis if exceeds max length.
        """
        if len(content) <= self.max_summary_length:
            return content

        # Truncate and add ellipsis
        truncated = content[: self.max_summary_length - 3].rstrip()
        return truncated + "..."

    # ========= PUBLIC METHODS =========

    def process_tool_output(
        self,
        tool_name: str,
        tool_call_id: str,
        output: Any,
        record_uuid: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Process a tool output and auto-offload if it exceeds threshold.

        This method should be called after tool execution to check if the
        output should be automatically offloaded. If the output length exceeds
        `auto_offload_threshold`, it will be stored to disk and a summary
        will be returned instead.

        Args:
            tool_name: Name of the tool that produced the output.
            tool_call_id: The tool call ID from the execution.
            output: The tool output (string or serializable object).
            record_uuid: Optional UUID of the memory record (for memory
                replacement).
            timestamp: Optional timestamp of the tool execution.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - offloaded (bool): Whether the output was offloaded.
                - output (str): The output to use (original or replacement).
                - offload_id (str, optional): ID if offloaded.
                - original_length (int): Length of the original output.
        """
        # Serialize output to string
        output_str = self._serialize_result(output)
        original_length = len(output_str)

        # Check if auto-offload is disabled or output is below threshold
        if (
            self.auto_offload_threshold <= 0
            or original_length <= self.auto_offload_threshold
        ):
            return {
                "offloaded": False,
                "output": output_str,
                "original_length": original_length,
            }

        # Auto-offload: generate summary and store original
        try:
            offload_id = str(uuid.uuid4())
            summary = self._generate_summary(output_str)

            metadata = OffloadedOutput(
                offload_id=offload_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                record_uuid=record_uuid or "",
                original_length=original_length,
                summary=summary,
                file_path=str(self.outputs_dir / f"{offload_id}.txt"),
                timestamp=timestamp or datetime.now().timestamp(),
                offloaded_at=datetime.now().isoformat(),
            )

            # Store original content to disk
            self._store_original_content(output_str, offload_id, metadata)

            # Create replacement content
            replacement = REPLACEMENT_CONTENT.format(
                offload_id=offload_id,
                summary=summary,
                original_length=original_length,
            )

            logger.info(
                f"Auto-offloaded output from '{tool_name}': "
                f"{original_length} chars -> {len(replacement)} chars "
                f"(ID: {offload_id})"
            )

            return {
                "offloaded": True,
                "output": replacement,
                "offload_id": offload_id,
                "original_length": original_length,
            }

        except Exception as e:
            logger.error(f"Error during auto-offload: {e}")
            # Fall back to original output on error
            return {
                "offloaded": False,
                "output": output_str,
                "original_length": original_length,
                "error": str(e),
            }

    # ========= AGENT TOOL METHODS =========

    def retrieve_offloaded_tool_output(
        self,
        offload_id: str,
    ) -> Dict[str, Any]:
        r"""Retrieve full original content of a previously offloaded output.

        Call this when you need to access the complete original tool output
        that was automatically offloaded due to its size. The offload_id can
        be found in the summarized output or via list_offloaded_tool_outputs().

        This does not modify memory; it only returns the stored content.

        Args:
            offload_id (str): The unique ID of the offloaded output. This ID
                is included in the summarized content that replaced the
                original output.

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

        Only retrieval tools are exposed to the agent. Offloading is handled
        automatically via process_tool_output() when outputs exceed the
        configured threshold.

        Returns:
            List[FunctionTool]: A list containing retrieve and list tools.
        """
        return [
            FunctionTool(self.retrieve_offloaded_tool_output),
            FunctionTool(self.list_offloaded_tool_outputs),
        ]
