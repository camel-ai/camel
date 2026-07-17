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

import hashlib
import re
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Literal, Optional

from camel.logger import get_logger
from camel.storages.tool_result_storages import (
    BaseToolResultStore,
    InMemoryToolResultStore,
    ToolResultRecord,
)
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)

TOOL_RESULT_READ_TOOL_NAME = "camel_tool_result_read"
TOOL_RESULT_SEARCH_TOOL_NAME = "camel_tool_result_search"
TOOL_RESULT_LIST_TOOL_NAME = "camel_tool_result_list"
TOOL_RESULT_ACCESS_TOOL_NAMES = frozenset(
    {
        TOOL_RESULT_READ_TOOL_NAME,
        TOOL_RESULT_SEARCH_TOOL_NAME,
        TOOL_RESULT_LIST_TOOL_NAME,
    }
)

_REF_PATTERN = re.compile(
    r"^camel://tool-results/(?P<scope_id>[A-Za-z0-9_.-]+)/"
    r"(?P<result_id>[A-Za-z0-9_.-]+)$"
)
_UNSAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_id(value: str, fallback: str) -> str:
    safe = _UNSAFE_ID_PATTERN.sub("_", value or "").strip("._-")
    return (safe or fallback)[:96]


@dataclass(frozen=True)
class ToolResultExternalizationConfig:
    r"""Configuration for moving large tool outputs out of model context.

    Passing this configuration to :class:`~camel.agents.ChatAgent` enables
    externalization. The default store is process-local; provide a
    :class:`~camel.storages.BaseToolResultStore` implementation for durable or
    shared storage.

    Args:
        enabled (bool): Whether externalization is active.
        threshold_chars (int): Externalize outputs larger than this size.
        preview_chars (int): Number of original characters retained across
            the head and tail preview.
        ttl_seconds (Optional[int]): Lifetime of stored results. ``None`` keeps
            them until explicitly deleted.
        max_read_chars (int): Maximum characters returned by one read call.
        max_search_matches (int): Maximum matches returned by one search.
        max_search_context_chars (int): Maximum context characters on each
            side of a search match.
        max_list_results (int): Maximum results returned by one list call.
        auto_register_tools (bool): Add read/search/list tools to the agent.
        failure_mode (Literal["inline", "raise"]): Keep the original result
            inline or raise when storage fails.
        scope_id (Optional[str]): Optional stable namespace for sharing results
            across agents. Defaults to the owning agent ID.
        store (Optional[BaseToolResultStore]): Pluggable result storage.
    """

    enabled: bool = True
    threshold_chars: int = 20_000
    preview_chars: int = 2_000
    ttl_seconds: Optional[int] = 86_400
    max_read_chars: int = 20_000
    max_search_matches: int = 20
    max_search_context_chars: int = 500
    max_list_results: int = 50
    auto_register_tools: bool = True
    failure_mode: Literal["inline", "raise"] = "inline"
    scope_id: Optional[str] = None
    store: Optional[BaseToolResultStore] = None

    def __post_init__(self) -> None:
        if self.threshold_chars <= 0:
            raise ValueError("threshold_chars must be greater than 0")
        if self.preview_chars < 0:
            raise ValueError(
                "preview_chars must be greater than or equal to 0"
            )
        if self.preview_chars >= self.threshold_chars:
            raise ValueError(
                "preview_chars must be smaller than threshold_chars"
            )
        if self.ttl_seconds is not None and self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0 or None")
        if self.max_read_chars <= 0:
            raise ValueError("max_read_chars must be greater than 0")
        if self.max_search_matches <= 0:
            raise ValueError("max_search_matches must be greater than 0")
        if self.max_search_context_chars < 0:
            raise ValueError(
                "max_search_context_chars must be greater than or equal to 0"
            )
        if self.max_list_results <= 0:
            raise ValueError("max_list_results must be greater than 0")


@dataclass(frozen=True)
class ExternalizedToolResult:
    r"""Result of successfully externalizing one tool output."""

    ref: str
    preview: str
    record: ToolResultRecord


class ToolResultExternalizer:
    r"""Store large tool results and expose range read and search tools."""

    def __init__(
        self,
        config: ToolResultExternalizationConfig,
        default_scope_id: str,
    ) -> None:
        store = (
            config.store
            if config.store is not None
            else InMemoryToolResultStore()
        )
        self.config = replace(config, store=store)
        self.scope_id = _safe_id(
            config.scope_id or default_scope_id, fallback="agent"
        )
        self.store = store

    @staticmethod
    def is_access_tool(tool_name: str) -> bool:
        r"""Return whether a tool is one of the built-in access tools."""
        return tool_name in TOOL_RESULT_ACCESS_TOOL_NAMES

    def get_tools(self) -> List[FunctionTool]:
        r"""Return model-callable read, search, and list tools."""
        return [
            FunctionTool(self.camel_tool_result_read),
            FunctionTool(self.camel_tool_result_search),
            FunctionTool(self.camel_tool_result_list),
        ]

    def config_for_clone(
        self, preserve_scope: bool
    ) -> ToolResultExternalizationConfig:
        r"""Return a config that shares storage and optionally the scope."""
        if self.config.scope_id is not None or preserve_scope:
            return replace(self.config, scope_id=self.scope_id)
        return self.config

    def externalize(
        self,
        content: str,
        tool_name: str,
        tool_call_id: str,
        mime_type: str = "text/plain",
    ) -> Optional[ExternalizedToolResult]:
        r"""Externalize content when it exceeds the configured threshold."""
        if (
            not self.config.enabled
            or len(content) <= self.config.threshold_chars
        ):
            return None
        if self.is_access_tool(tool_name):
            return None

        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        safe_call_id = _safe_id(tool_call_id, fallback="tool")
        result_id = f"tr_{safe_call_id}_{digest[:16]}"
        ref = f"camel://tool-results/{self.scope_id}/{result_id}"
        created_at = time.time()
        expires_at = (
            created_at + self.config.ttl_seconds
            if self.config.ttl_seconds is not None
            else None
        )
        record = ToolResultRecord(
            result_id=result_id,
            scope_id=self.scope_id,
            ref=ref,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            content=content,
            created_at=created_at,
            expires_at=expires_at,
            original_chars=len(content),
            sha256=digest,
            mime_type=mime_type,
        )
        preview = self._make_preview(record)
        if len(preview) >= len(content):
            return None
        try:
            self.store.save(record)
        except Exception:
            if self.config.failure_mode == "raise":
                raise
            logger.warning(
                "Failed to externalize output from tool '%s'; "
                "keeping it inline",
                tool_name,
                exc_info=True,
            )
            return None

        return ExternalizedToolResult(
            ref=ref,
            preview=preview,
            record=record,
        )

    def _make_preview(self, record: ToolResultRecord) -> str:
        preview_chars = self.config.preview_chars
        if preview_chars <= 0:
            body = ""
        elif len(record.content) <= preview_chars:
            body = record.content
        else:
            head_chars = (preview_chars + 1) // 2
            tail_chars = preview_chars // 2
            body = (
                "--- BEGIN PREVIEW HEAD ---\n"
                f"{record.content[:head_chars]}\n"
                "--- END PREVIEW HEAD ---\n\n"
                "--- BEGIN PREVIEW TAIL ---\n"
                f"{record.content[-tail_chars:] if tail_chars else ''}\n"
                "--- END PREVIEW TAIL ---"
            )

        header = [
            "[CAMEL tool result externalized]",
            f"tool_name: {record.tool_name}",
            f"original_chars: {record.original_chars}",
            f"ref: {record.ref}",
            f"sha256: {record.sha256[:16]}",
            (
                "Use camel_tool_result_search to locate relevant text, then "
                "camel_tool_result_read to read only the needed range."
            ),
        ]
        return "\n".join(header) + (f"\n\n{body}" if body else "")

    def _parse_ref(self, ref: str) -> tuple[str, str]:
        match = _REF_PATTERN.fullmatch(str(ref).strip())
        if match is None:
            raise ValueError(
                "ref must be a camel://tool-results/<scope>/<result> URI"
            )
        scope_id = match.group("scope_id")
        result_id = match.group("result_id")
        if scope_id != self.scope_id:
            raise PermissionError("tool result belongs to another scope")
        return scope_id, result_id

    def _get_record(self, ref: str) -> ToolResultRecord:
        scope_id, result_id = self._parse_ref(ref)
        record = self.store.get(scope_id, result_id)
        if record is None:
            raise KeyError(f"tool result not found or expired: {ref}")
        return record

    def read(
        self, ref: str, offset: int = 0, limit: int = 20_000
    ) -> Dict[str, Any]:
        r"""Read a bounded character range from an externalized result."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        record = self._get_record(ref)
        effective_limit = min(limit, self.config.max_read_chars)
        content = record.content[offset : offset + effective_limit]
        next_offset = offset + len(content)
        return {
            "ref": ref,
            "content": content,
            "offset": offset,
            "offset_unit": "unicode_code_point",
            "limit": effective_limit,
            "returned_chars": len(content),
            "total_chars": record.original_chars,
            "has_more": next_offset < record.original_chars,
            "next_offset": (
                next_offset if next_offset < record.original_chars else None
            ),
            "metadata": record.metadata_dict(),
        }

    def search(
        self,
        ref: str,
        query: str,
        limit: int = 20,
        context_chars: int = 300,
        case_sensitive: bool = False,
    ) -> Dict[str, Any]:
        r"""Search exact text inside an externalized result."""
        if not query:
            raise ValueError("query must not be empty")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if context_chars < 0:
            raise ValueError(
                "context_chars must be greater than or equal to 0"
            )

        record = self._get_record(ref)
        effective_limit = min(limit, self.config.max_search_matches)
        effective_context = min(
            context_chars, self.config.max_search_context_chars
        )
        haystack = record.content if case_sensitive else record.content.lower()
        needle = query if case_sensitive else query.lower()
        matches: List[Dict[str, Any]] = []
        start = 0
        while len(matches) < effective_limit:
            offset = haystack.find(needle, start)
            if offset < 0:
                break
            left = max(0, offset - effective_context)
            right = min(
                len(record.content), offset + len(query) + effective_context
            )
            matches.append(
                {
                    "offset": offset,
                    "offset_unit": "unicode_code_point",
                    "snippet_start": left,
                    "snippet_end": right,
                    "snippet": record.content[left:right],
                }
            )
            start = offset + max(1, len(query))
        return {"ref": ref, "query": query, "matches": matches}

    def list(
        self, tool_name: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        r"""List externalized results in this scope without their bodies."""
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        effective_limit = min(limit, self.config.max_list_results)
        records = self.store.list(self.scope_id, tool_name, effective_limit)
        return {
            "scope_id": self.scope_id,
            "tool_results": records,
        }

    def camel_tool_result_read(
        self, ref: str, offset: int = 0, limit: int = 20_000
    ) -> str:
        r"""Read part of an externalized tool result by its CAMEL reference.

        Use this after a tool response says it was externalized. Prefer a
        bounded range, and use search first when the needed offset is unknown.

        Args:
            ref (str): Exact ``camel://tool-results/...`` reference.
            offset (int): Unicode character offset to start reading from.
            limit (int): Maximum characters to return. The configured safety
                cap still applies.

        Returns:
            str: The requested content and pagination metadata.
        """
        try:
            result = self.read(ref, offset=offset, limit=limit)
        except (KeyError, PermissionError, ValueError) as error:
            return f"Error reading externalized tool result: {error}"
        header = [
            "[CAMEL externalized tool result chunk]",
            f"ref: {result['ref']}",
            f"offset: {result['offset']}",
            f"returned_chars: {result['returned_chars']}",
            f"total_chars: {result['total_chars']}",
            f"has_more: {str(result['has_more']).lower()}",
            f"next_offset: {result['next_offset']}",
        ]
        return "\n".join(header) + "\n\n" + result["content"]

    def camel_tool_result_search(
        self,
        ref: str,
        query: str,
        limit: int = 20,
        context_chars: int = 300,
        case_sensitive: bool = False,
    ) -> str:
        r"""Search within an externalized tool result and return snippets.

        Args:
            ref (str): Exact ``camel://tool-results/...`` reference.
            query (str): Exact text to find.
            limit (int): Maximum number of matches.
            context_chars (int): Context characters around each match.
            case_sensitive (bool): Whether matching should preserve case.

        Returns:
            str: Matching snippets and offsets for follow-up range reads.
        """
        try:
            result = self.search(
                ref,
                query,
                limit=limit,
                context_chars=context_chars,
                case_sensitive=case_sensitive,
            )
        except (KeyError, PermissionError, ValueError) as error:
            return f"Error searching externalized tool result: {error}"
        matches = result["matches"]
        if not matches:
            return f'No matches found for "{query}" in {ref}.'
        sections = [f'Found {len(matches)} match(es) for "{query}" in {ref}:']
        for index, match in enumerate(matches, start=1):
            sections.append(
                f"## Match {index} (offset {match['offset']})\n"
                f"{match['snippet']}"
            )
        return "\n\n".join(sections)

    def camel_tool_result_list(
        self, tool_name: Optional[str] = None, limit: int = 50
    ) -> str:
        r"""List externalized tool results available to this agent.

        Args:
            tool_name (Optional[str]): Optional exact tool-name filter.
            limit (int): Maximum number of results.

        Returns:
            str: Result references and lightweight metadata.
        """
        try:
            result = self.list(tool_name=tool_name, limit=limit)
        except ValueError as error:
            return f"Error listing externalized tool results: {error}"
        items = result["tool_results"]
        if not items:
            suffix = f' for tool "{tool_name}"' if tool_name else ""
            return f"No externalized tool results found{suffix}."
        lines = [f"Found {len(items)} externalized tool result(s):"]
        for index, item in enumerate(items, start=1):
            lines.append(
                f"{index}. {item['tool_name']} "
                f"original_chars={item['original_chars']}\n"
                f"ref: {item['ref']}"
            )
        return "\n\n".join(lines)
