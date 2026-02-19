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

if TYPE_CHECKING:
    from camel.agents import ChatAgent

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
        summary: The summary provided by the model.
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
    r"""A toolkit for model-driven tool output offloading and retrieval.

    This toolkit allows the model to manage memory by offloading large tool
    outputs to disk storage. When tool outputs exceed a configurable threshold,
    a hint is automatically emitted suggesting the model use
    `summarize_and_offload`.

    Args:
        working_directory: Directory for storing offloaded content.
            Defaults to CAMEL_WORKDIR/tool_output_offload or
            ./tool_output_offload.
        timeout: Timeout for toolkit operations.
        hint_threshold: Character length threshold for showing offload hints.
            When a tool output exceeds this length, a hint is emitted
            suggesting the model call `summarize_and_offload`. Set to 0 to
            disable hints. (default: :obj:`5000`)

    Example:
        >>> from camel.agents import ChatAgent
        >>> from camel.toolkits import ToolOutputOffloadToolkit, BrowserToolkit
        >>>
        >>> offload_toolkit = ToolOutputOffloadToolkit(hint_threshold=3000)
        >>> agent = ChatAgent(
        ...     tools=BrowserToolkit().get_tools() + offload_toolkit.get_tools(),
        ...     toolkits_to_register_agent=[offload_toolkit],
        ... )
        >>> # Large outputs will now include hints to use summarize_and_offload
    """  # noqa: E501

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        hint_threshold: int = 5000,
    ):
        BaseToolkit.__init__(self, timeout=timeout)
        RegisteredAgentToolkit.__init__(self)

        self.hint_threshold = hint_threshold

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
        r"""Register a ChatAgent and install the tool output processor.

        This method overrides the base class to additionally install a
        processor that emits hints for large tool outputs, suggesting the
        model use `summarize_and_offload`.

        Args:
            agent (ChatAgent): The ChatAgent instance to register.
        """
        super().register_agent(agent)
        # Install the hint processor if threshold is set
        if self.hint_threshold > 0:
            agent._tool_output_processor = self.process_tool_output
            logger.info(
                f"Installed offload hint processor (threshold: "
                f"{self.hint_threshold} chars)"
            )

    def process_tool_output(
        self,
        tool_name: str,
        tool_call_id: str,
        output: Any,
    ) -> Optional[Dict[str, Any]]:
        r"""Process a tool output and emit a must-offload hint if needed.

        This method is called automatically after tool execution when the
        toolkit is registered with an agent. It preserves the original tool
        output and, for large outputs, provides a separate hint message
        (as a new memory item) requiring the model use `summarize_and_offload`.

        Args:
            tool_name: Name of the tool that produced the output.
            tool_call_id: The tool call ID from the execution.
            output: The tool output (string or serializable object).

        Returns:
            Optional[Dict[str, Any]]: None if output is None (caller should
                skip adding memory item), otherwise a dictionary containing:
                - output: The original tool output, unchanged.
                - hint_message (str, optional): A hint message that will be
                  added as a separate assistant message in memory, prompting
                  the model to offload the large output.
        """
        # Return None to signal caller to skip memory item
        if output is None:
            logger.debug(
                f"Tool '{tool_name}' (call_id: {tool_call_id}) returned None, "
                f"skipping memory item"
            )
            return None

        # Serialize and measure output
        output_str = self._serialize_result(output)
        output_length = len(output_str)

        # Check if must-offload hint should be emitted
        if output_length > self.hint_threshold:
            logger.info(
                f"Large tool output detected: '{tool_name}' "
                f"(call_id: {tool_call_id}) - {output_length:,} chars "
                f"(threshold: {self.hint_threshold:,})"
            )

            # Track pending offload for potential follow-up queries
            if not hasattr(self, "_pending_offloads"):
                self._pending_offloads: Dict[str, Dict[str, Any]] = {}
            self._pending_offloads[tool_call_id] = {
                "tool_name": tool_name,
                "output_length": output_length,
                "detected_at": datetime.now().isoformat(),
            }

            hint = (
                f"[OFFLOAD REQUIRED: The preceding tool call "
                f"'{tool_name}' (tool_call_id=\"{tool_call_id}\") "
                f"produced {output_length:,} chars, exceeding the "
                f"{self.hint_threshold:,} char threshold. "
                f"You MUST call summarize_and_offload("
                f"tool_call_id=\"{tool_call_id}\", "
                f"summary=\"<your summary>\") as a PARALLEL tool call "
                f"with your next tool action. "
                f"When this assistant message includes any tool calls, "
                f"do NOT provide the final user-facing answer in the same "
                f"message. Provide the final answer only in the next "
                f"assistant turn after tool results are returned. "
                f"Do NOT issue offload as a standalone call.]"
            )
            return {"output": output, "hint_message": hint}

        return {"output": output}

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
            ValueError: If agent is not set, memory doesn't support required
                methods, record not found, or record has no message/result
                attribute.
        """
        if self._agent is None:
            raise ValueError("Agent is not set.")

        memory = self._agent.memory
        if not hasattr(memory, "get_records") or not hasattr(
            memory, "replace_record_by_uuid"
        ):
            raise ValueError(
                "Memory does not support get_records() or "
                "replace_record_by_uuid(). "
                "Tool output offloading requires ChatHistoryMemory."
            )
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

    # ========= AGENT TOOL METHODS =========

    def summarize_and_offload(
        self,
        tool_call_id: str,
        summary: str,
    ) -> Dict[str, Any]:
        r"""Offload a previous tool output to disk and replace it with your
        summary in memory.

        Call this after you have seen and processed a large tool output that
        you want to compress. When a tool output exceeds the offload hint
        threshold, you MUST call this to offload it when the full tool
        output is not needed immediately. The offload MUST be issued as a
        parallel tool call in the same assistant message as your next tool
        action. If that assistant message includes any tool calls, do NOT
        include the final user-facing answer in that same message. Wait for
        tool results and provide the final answer in the next assistant turn.
        This makes the
        offload happen alongside that next step, so the decision uses the
        full tool output still in context and no separate LLM call is needed.
        Never offload as a standalone call.
        You provide the summary - this allows you to
        capture what's relevant for the current task rather than using generic
        truncation.

        This is useful for managing context window usage. After offloading,
        the original content is saved to disk and can be retrieved later with
        `retrieve_offloaded_tool_output()` if needed.

        Args:
            tool_call_id (str): The tool_call_id of the tool output to offload.
                This is returned in the tool call response when you invoke a
                tool.
            summary (str): Your summary of the tool output. Write a
                summary that helps future retrieval decisions by including:
                - What type of content this is (e.g., "HTML page",
                  "API response", "search results")
                - Key entities or topics covered (e.g., "blog post
                  about X", "list of 50 products")
                - What information is preserved vs. lost (e.g., "main content
                  preserved, navigation/ads removed")
                - When retrieval might be needed (e.g., "retrieve if exact URLs
                  or prices are needed")
                This replaces the original content in memory.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the offload succeeded.
                - offload_id (str): ID to retrieve original content later.
                - tool_name (str): Name of the tool that was offloaded.
                - original_length (int): Character count of original content.
                - summary_length (int): Character count of the summary.
                - message (str): Status message.
                - error (str, optional): Error message if failed.
        """
        if self._agent is None:
            return {
                "success": False,
                "error": "No agent registered. Cannot access memory.",
            }

        # Find the tool output in memory by tool_call_id
        tool_outputs = self._get_tool_outputs_from_memory()
        target_output = None
        for output in tool_outputs:
            if output["tool_call_id"] == tool_call_id:
                target_output = output
                break

        if target_output is None:
            available_ids = [o["tool_call_id"] for o in tool_outputs]
            return {
                "success": False,
                "error": f"Tool call ID '{tool_call_id}' not found in memory. "
                f"Available tool_call_ids: {available_ids}",
            }

        # Check if already offloaded
        for meta in self._offloaded_outputs.values():
            if meta.tool_call_id == tool_call_id:
                return {
                    "success": False,
                    "error": f"Tool output '{tool_call_id}' has already been "
                    f"offloaded (offload_id: {meta.offload_id}).",
                }

        try:
            offload_id = str(uuid.uuid4())
            original_content = target_output["result_str"]
            original_length = len(original_content)

            metadata = OffloadedOutput(
                offload_id=offload_id,
                tool_name=target_output["tool_name"],
                tool_call_id=tool_call_id,
                record_uuid=target_output["uuid"],
                original_length=original_length,
                summary=summary,
                file_path=str(self.outputs_dir / f"{offload_id}.txt"),
                timestamp=target_output["timestamp"],
                offloaded_at=datetime.now().isoformat(),
            )

            # Store original content to disk
            self._store_original_content(
                original_content, offload_id, metadata
            )

            # Create replacement content with rich metadata
            replacement = (
                f"[OFFLOADED OUTPUT]\n"
                f"- Tool: {target_output['tool_name']}\n"
                f"- Offload ID: {offload_id}\n"
                f"- Original size: {original_length:,} chars\n\n"
                f"Summary:\n{summary}\n\n"
                f"To access full content:\n"
                f"retrieve_offloaded_tool_output('{offload_id}')"
            )

            # Replace in memory
            self._replace_in_memory(target_output["uuid"], replacement)

            logger.info(
                f"Offloaded '{target_output['tool_name']}' output: "
                f"{original_length} chars -> {len(summary)} chars summary "
                f"(ID: {offload_id})"
            )

            return {
                "success": True,
                "offload_id": offload_id,
                "tool_name": target_output["tool_name"],
                "original_length": original_length,
                "summary_length": len(summary),
                "message": f"Successfully offloaded. Original content saved "
                f"with ID '{offload_id}'.",
            }

        except Exception as e:
            logger.error(f"Error during offload: {e}")
            return {
                "success": False,
                "error": f"Failed to offload: {e}",
            }

    def retrieve_offloaded_tool_output(
        self,
        offload_id: str,
    ) -> Dict[str, Any]:
        r"""Retrieve full original content of a previously offloaded output.

        Call this when you need to access the complete original tool output
        that was offloaded. The offload_id is included in the replacement
        text that was put in memory after offloading.

        Note: This returns the content but does NOT restore it to memory.
        The memory still contains your summary.

        Args:
            offload_id (str): The unique ID of the offloaded output, found in
                the replacement text after calling summarize_and_offload().

        Returns:
            Dict[str, Any]: A dictionary containing:
                - offload_id (str): The unique offload identifier.
                - tool_name (str): Name of the tool that produced the output.
                - content (str): The full original tool output content.
                - original_length (int): Character length of the content.
                - summary (str): The summary you provided during offload.
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
                    "error": f"Offload ID '{offload_id}' not found.",
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

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for the toolkit.

        Returns:
            List[FunctionTool]: Tools for model-driven offloading:
                - summarize_and_offload: Offload tool output with summary
                - retrieve_offloaded_tool_output: Get original content
        """
        return [
            FunctionTool(self.summarize_and_offload),
            FunctionTool(self.retrieve_offloaded_tool_output),
        ]
