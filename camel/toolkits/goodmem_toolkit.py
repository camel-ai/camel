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
import base64
import json
import os
import time
from typing import Any, Dict, List, Optional

import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit, manual_timeout
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

# Mapping of file extensions to MIME types for memory content upload.
_MIME_TYPES: Dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "txt": "text/plain",
    "html": "text/html",
    "md": "text/markdown",
    "csv": "text/csv",
    "json": "application/json",
    "xml": "application/xml",
    "doc": "application/msword",
    "docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    "xls": "application/vnd.ms-excel",
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": (
        "application/vnd.openxmlformats-officedocument"
        ".presentationml.presentation"
    ),
}


def _get_mime_type(extension: str) -> Optional[str]:
    r"""Returns the MIME type for a given file extension.

    Args:
        extension (str): The file extension (with or without leading dot).

    Returns:
        Optional[str]: The corresponding MIME type, or None if unknown.
    """
    return _MIME_TYPES.get(extension.lower().lstrip("."))


@MCPServer()
class GoodMemToolkit(BaseToolkit):
    r"""A toolkit for interacting with the GoodMem API.

    GoodMem is a memory layer for AI agents with support for semantic
    storage, retrieval, and summarization. This toolkit exposes GoodMem
    operations as CAMEL tools that can be used with any CAMEL agent.

    Attributes:
        base_url (str): The base URL of the GoodMem API server.
        api_key (str): The API key used for authentication.
    """

    @api_keys_required(
        [
            ("api_key", "GOODMEM_API_KEY"),
            ("base_url", "GOODMEM_BASE_URL"),
        ]
    )
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the GoodMemToolkit.

        Args:
            base_url (Optional[str]): The base URL of the GoodMem API
                server. If not provided, falls back to the
                ``GOODMEM_BASE_URL`` environment variable.
                (default: :obj:`None`)
            api_key (Optional[str]): The GoodMem API key for
                authentication (``X-API-Key``). If not provided, falls
                back to the ``GOODMEM_API_KEY`` environment variable.
                (default: :obj:`None`)
            verify_ssl (bool): Whether to verify SSL certificates. Set
                to ``False`` for self-signed certificates.
                (default: :obj:`True`)
            timeout (Optional[float]): The timeout value for the toolkit
                in seconds. (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.base_url = (
            base_url or os.environ.get("GOODMEM_BASE_URL", "")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("GOODMEM_API_KEY", "")
        self.verify_ssl = verify_ssl
        self._session = requests.Session()
        self._session.verify = self.verify_ssl

    def close(self) -> None:
        r"""Closes the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "GoodMemToolkit":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _headers(self, include_content_type: bool = True) -> Dict[str, str]:
        r"""Returns the common HTTP headers for GoodMem API requests.

        Args:
            include_content_type (bool): Whether to include the
                ``Content-Type`` header. Should be ``False`` for GET
                requests that carry no body. (default: :obj:`True`)

        Returns:
            Dict[str, str]: A dictionary of HTTP headers.
        """
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        if include_content_type:
            headers["Content-Type"] = "application/json"
        return headers

    # ------------------------------------------------------------------
    # List Embedders
    # ------------------------------------------------------------------

    def goodmem_list_embedders(self) -> List[Dict[str, Any]]:
        r"""Lists all available embedder models.

        Embedders convert text into vector representations for
        similarity search. Use this to find a valid ``embedder_id``
        when creating a space.

        Returns:
            List[Dict[str, Any]]: A list of embedder objects, each
                containing ``embedderId``, ``displayName``, and
                ``modelIdentifier``.
        """
        response = self._session.get(
            f"{self.base_url}/v1/embedders",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        body = response.json()
        embedders = (
            body if isinstance(body, list) else body.get("embedders", [])
        )
        return [
            {
                "embedderId": e.get("embedderId") or e.get("id"),
                "displayName": (
                    e.get("displayName")
                    or e.get("name")
                    or e.get("modelIdentifier")
                    or "Unnamed"
                ),
                "modelIdentifier": (
                    e.get("modelIdentifier") or e.get("model") or "unknown"
                ),
            }
            for e in embedders
        ]

    # ------------------------------------------------------------------
    # List Spaces
    # ------------------------------------------------------------------

    def goodmem_list_spaces(self) -> List[Dict[str, Any]]:
        r"""Lists all existing spaces.

        A space is a logical container for organizing related memories
        and is configured with one or more embedders.

        Returns:
            List[Dict[str, Any]]: A list of space objects, each
                containing ``spaceId``, ``name``, and
                ``spaceEmbedders``.
        """
        response = self._session.get(
            f"{self.base_url}/v1/spaces",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        body = response.json()
        spaces = body if isinstance(body, list) else body.get("spaces", [])
        return [
            {
                "spaceId": s.get("spaceId") or s.get("id"),
                "name": s.get("name") or "Unnamed",
                "spaceEmbedders": s.get("spaceEmbedders", []),
            }
            for s in spaces
        ]

    # ------------------------------------------------------------------
    # Get Space
    # ------------------------------------------------------------------

    def goodmem_get_space(self, space_id: str) -> Dict[str, Any]:
        r"""Fetches a single space by its ID.

        Use this to inspect a space's full configuration, including
        its embedders, chunking settings, and labels.

        Args:
            space_id (str): The UUID of the space to fetch.

        Returns:
            Dict[str, Any]: The full space object as returned by the
                GoodMem API.
        """
        response = self._session.get(
            f"{self.base_url}/v1/spaces/{space_id}",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Create Space
    # ------------------------------------------------------------------

    def goodmem_create_space(
        self,
        name: str,
        embedder_id: str,
        chunk_size: int = 256,
        chunk_overlap: int = 25,
        keep_strategy: str = "KEEP_END",
        length_measurement: str = "CHARACTER_COUNT",
    ) -> Dict[str, Any]:
        r"""Creates a new space or reuses an existing one.

        A space is a logical container for organizing related memories,
        configured with embedders that convert text to vector
        embeddings. If a space with the given name already exists, its
        ID is returned instead of creating a duplicate.

        Args:
            name (str): A unique name for the space.
            embedder_id (str): The ID of the embedder model to use.
                Use :meth:`goodmem_list_embedders` to find available IDs.
            chunk_size (int): Number of characters per chunk when
                splitting documents. (default: :obj:`256`)
            chunk_overlap (int): Number of overlapping characters
                between consecutive chunks. (default: :obj:`25`)
            keep_strategy (str): Where to attach the separator when
                splitting. One of ``KEEP_END``, ``KEEP_START``, or
                ``DISCARD``. (default: :obj:`"KEEP_END"`)
            length_measurement (str): How chunk size is measured. One
                of ``CHARACTER_COUNT`` or ``TOKEN_COUNT``.
                (default: :obj:`"CHARACTER_COUNT"`)

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``spaceId``, ``name``, ``embedderId``, ``message``,
                and ``reused``.
        """
        # Check if a space with the same name already exists.
        try:
            spaces = self.goodmem_list_spaces()
            for space in spaces:
                if space.get("name") == name:
                    actual_embedder_id = embedder_id
                    space_embedders = space.get("spaceEmbedders", [])
                    if space_embedders:
                        actual_embedder_id = space_embedders[0].get(
                            "embedderId", embedder_id
                        )
                    return {
                        "success": True,
                        "spaceId": space["spaceId"],
                        "name": space["name"],
                        "embedderId": actual_embedder_id,
                        "message": (
                            "Space already exists, reusing existing space"
                        ),
                        "reused": True,
                    }
        except requests.RequestException:
            # If listing fails, proceed to create.
            logger.debug("Failed to list spaces; proceeding to create.")

        request_body: Dict[str, Any] = {
            "name": name,
            "spaceEmbedders": [
                {"embedderId": embedder_id, "defaultRetrievalWeight": 1.0}
            ],
            "defaultChunkingConfig": {
                "recursive": {
                    "chunkSize": chunk_size,
                    "chunkOverlap": chunk_overlap,
                    "separators": ["\n\n", "\n", ". ", " ", ""],
                    "keepStrategy": keep_strategy,
                    "separatorIsRegex": False,
                    "lengthMeasurement": length_measurement,
                },
            },
        }

        response = self._session.post(
            f"{self.base_url}/v1/spaces",
            headers=self._headers(),
            json=request_body,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "success": True,
            "spaceId": body.get("spaceId"),
            "name": body.get("name"),
            "embedderId": embedder_id,
            "chunkingConfig": request_body["defaultChunkingConfig"],
            "message": "Space created successfully",
            "reused": False,
        }

    # ------------------------------------------------------------------
    # Update Space
    # ------------------------------------------------------------------

    def goodmem_update_space(
        self,
        space_id: str,
        name: Optional[str] = None,
        public_read: Optional[bool] = None,
        replace_labels_json: Optional[str] = None,
        merge_labels_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Updates a space's name, labels, or access settings.

        Only the fields you provide are changed; omitted fields keep
        their current values. ``replace_labels_json`` and
        ``merge_labels_json`` are mutually exclusive.

        Args:
            space_id (str): The UUID of the space to update.
            name (Optional[str]): New name for the space.
                (default: :obj:`None`)
            public_read (Optional[bool]): Whether to allow
                unauthenticated read access.
                (default: :obj:`None`)
            replace_labels_json (Optional[str]): A JSON string of
                labels that replace all existing labels, e.g.
                ``'{"env": "prod"}'``.
                (default: :obj:`None`)
            merge_labels_json (Optional[str]): A JSON string of
                labels that merge into existing labels, e.g.
                ``'{"team": "ml"}'``.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The updated space object as returned
                by the GoodMem API.
        """
        if replace_labels_json and merge_labels_json:
            return {
                "success": False,
                "error": (
                    "Cannot use both replace_labels_json and "
                    "merge_labels_json at the same time."
                ),
            }

        request_body: Dict[str, Any] = {}
        if name is not None:
            request_body["name"] = name
        if public_read is not None:
            request_body["publicRead"] = public_read
        if replace_labels_json:
            request_body["replaceLabels"] = json.loads(replace_labels_json)
        if merge_labels_json:
            request_body["mergeLabels"] = json.loads(merge_labels_json)

        response = self._session.put(
            f"{self.base_url}/v1/spaces/{space_id}",
            headers=self._headers(),
            json=request_body,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Delete Space
    # ------------------------------------------------------------------

    def goodmem_delete_space(self, space_id: str) -> Dict[str, Any]:
        r"""Permanently deletes a space and all associated data.

        Removes the space along with all its memories, chunks, and
        vector embeddings.

        Args:
            space_id (str): The UUID of the space to delete.

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``spaceId``, and ``message``.
        """
        response = self._session.delete(
            f"{self.base_url}/v1/spaces/{space_id}",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        return {
            "success": True,
            "spaceId": space_id,
            "message": "Space deleted successfully",
        }

    # ------------------------------------------------------------------
    # Create Memory
    # ------------------------------------------------------------------

    def goodmem_create_memory(
        self,
        space_id: str,
        text_content: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Stores a document as a new memory in a space.

        The memory is processed asynchronously -- chunked into
        searchable pieces and embedded into vectors. Provide either
        ``text_content`` for plain text or ``file_path`` for a file
        (PDF, DOCX, image, etc.). If both are provided, the file takes
        priority.

        Args:
            space_id (str): The ID of the space to store the memory in.
            text_content (Optional[str]): Plain text content to store.
                (default: :obj:`None`)
            file_path (Optional[str]): Path to a file to upload as
                memory. The content type is auto-detected from the
                file extension. (default: :obj:`None`)
            metadata_json (Optional[str]): A JSON string containing
                extra key-value metadata to attach to the memory,
                e.g. ``'{"source": "email"}'``.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``memoryId``, ``spaceId``, ``status``, ``contentType``,
                and ``message``.
        """
        request_body: Dict[str, Any] = {"spaceId": space_id}

        if file_path:
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
            mime_type = _get_mime_type(ext) or "application/octet-stream"

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            if mime_type.startswith("text/"):
                request_body["contentType"] = mime_type
                request_body["originalContent"] = file_bytes.decode("utf-8")
            else:
                request_body["contentType"] = mime_type
                request_body["originalContentB64"] = base64.b64encode(
                    file_bytes
                ).decode("ascii")
        elif text_content:
            request_body["contentType"] = "text/plain"
            request_body["originalContent"] = text_content
        else:
            return {
                "success": False,
                "error": (
                    "No content provided. Please provide text_content "
                    "or file_path."
                ),
            }

        if metadata_json:
            request_body["metadata"] = json.loads(metadata_json)

        response = self._session.post(
            f"{self.base_url}/v1/memories",
            headers=self._headers(),
            json=request_body,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "success": True,
            "memoryId": body.get("memoryId"),
            "spaceId": body.get("spaceId"),
            "status": body.get("processingStatus", "PENDING"),
            "contentType": request_body["contentType"],
            "message": "Memory created successfully",
        }

    # ------------------------------------------------------------------
    # Retrieve Memories
    # ------------------------------------------------------------------

    @manual_timeout
    def goodmem_retrieve_memories(
        self,
        query: str,
        space_ids: List[str],
        max_results: int = 5,
        include_memory_definition: bool = True,
        wait_for_indexing: bool = True,
        max_wait_seconds: float = 10,
        poll_interval: float = 2,
        reranker_id: Optional[str] = None,
        llm_id: Optional[str] = None,
        relevance_threshold: Optional[float] = None,
        llm_temperature: Optional[float] = None,
        chronological_resort: bool = False,
        metadata_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Performs similarity-based semantic retrieval across spaces.

        Returns matching chunks ranked by relevance, with optional full
        memory definitions.

        Args:
            query (str): A natural language query to find semantically
                similar memory chunks.
            space_ids (List[str]): One or more space IDs to search
                across.
            max_results (int): Maximum number of results to return.
                (default: :obj:`5`)
            include_memory_definition (bool): Whether to fetch the full
                memory metadata alongside matched chunks.
                (default: :obj:`True`)
            wait_for_indexing (bool): When ``True``, retry up to
                ``max_wait_seconds`` when no results are found.
                Enable this when memories were just added and may
                still be processing. (default: :obj:`True`)
            max_wait_seconds (float): Maximum time in seconds to poll
                for results when ``wait_for_indexing`` is ``True``.
                (default: :obj:`10`)
            poll_interval (float): Seconds to sleep between polling
                attempts when ``wait_for_indexing`` is ``True``.
                (default: :obj:`2`)
            reranker_id (Optional[str]): Optional reranker model ID to
                improve result ordering. (default: :obj:`None`)
            llm_id (Optional[str]): Optional LLM ID to generate
                contextual responses alongside retrieved chunks.
                (default: :obj:`None`)
            relevance_threshold (Optional[float]): Minimum score (0-1)
                for including results. Only used when ``reranker_id``
                or ``llm_id`` is set. (default: :obj:`None`)
            llm_temperature (Optional[float]): Creativity setting for
                LLM generation (0-2). Only used when ``llm_id`` is
                set. (default: :obj:`None`)
            chronological_resort (bool): Reorder results by creation
                time instead of relevance score.
                (default: :obj:`False`)
            metadata_filter (Optional[str]): A SQL-style JSONPath
                expression applied server-side to narrow results by
                metadata. Example: ``CAST(val('$.category') AS
                TEXT) = 'feat'`` returns only memories whose
                ``metadata.category`` equals ``feat``. When set, the
                same filter is applied to every space in
                ``space_ids``. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``resultSetId``, ``results``, ``memories``,
                ``totalResults``, ``query``, and optionally
                ``abstractReply``.
        """
        space_keys: List[Dict[str, Any]] = [
            {"spaceId": sid} for sid in space_ids if sid
        ]
        if not space_keys:
            return {
                "success": False,
                "error": "At least one space must be provided.",
            }
        if metadata_filter:
            for space_key in space_keys:
                space_key["filter"] = metadata_filter

        request_body: Dict[str, Any] = {
            "message": query,
            "spaceKeys": space_keys,
            "requestedSize": max_results,
            "fetchMemory": include_memory_definition,
        }

        # Add post-processor config if reranker or LLM is specified.
        if reranker_id or llm_id:
            config: Dict[str, Any] = {}
            if reranker_id:
                config["reranker_id"] = reranker_id
            if llm_id:
                config["llm_id"] = llm_id
            if relevance_threshold is not None:
                config["relevance_threshold"] = relevance_threshold
            if llm_temperature is not None:
                config["llm_temp"] = llm_temperature
            if max_results:
                config["max_results"] = max_results
            if chronological_resort:
                config["chronological_resort"] = True
            request_body["postProcessor"] = {
                "name": (
                    "com.goodmem.retrieval.postprocess"
                    ".ChatPostProcessorFactory"
                ),
                "config": config,
            }

        start_time = time.time()
        last_result: Optional[Dict[str, Any]] = None

        while True:
            retrieve_headers = {
                **self._headers(),
                "Accept": "application/x-ndjson",
            }

            response = self._session.post(
                f"{self.base_url}/v1/memories:retrieve",
                headers=retrieve_headers,
                json=request_body,
            )
            response.raise_for_status()

            results: List[Dict[str, Any]] = []
            memories: List[Any] = []
            result_set_id = ""
            abstract_reply: Any = None

            response_text = response.text
            lines = response_text.strip().split("\n")

            for line in lines:
                json_str = line.strip()
                if not json_str:
                    continue
                # Handle SSE format.
                if json_str.startswith("data:"):
                    json_str = json_str[5:].strip()
                if json_str.startswith("event:") or not json_str:
                    continue
                try:
                    item = json.loads(json_str)
                    if item.get("resultSetBoundary"):
                        result_set_id = item["resultSetBoundary"].get(
                            "resultSetId", ""
                        )
                    elif item.get("memoryDefinition"):
                        memories.append(item["memoryDefinition"])
                    elif item.get("abstractReply"):
                        abstract_reply = item["abstractReply"]
                    elif item.get("retrievedItem"):
                        chunk_data = item["retrievedItem"].get("chunk", {})
                        chunk_inner = chunk_data.get("chunk", {})
                        results.append(
                            {
                                "chunkId": chunk_inner.get("chunkId"),
                                "chunkText": chunk_inner.get("chunkText"),
                                "memoryId": chunk_inner.get("memoryId"),
                                "relevanceScore": chunk_data.get(
                                    "relevanceScore"
                                ),
                                "memoryIndex": chunk_data.get("memoryIndex"),
                            }
                        )
                except json.JSONDecodeError:
                    continue

            last_result = {
                "success": True,
                "resultSetId": result_set_id,
                "results": results,
                "memories": memories,
                "totalResults": len(results),
                "query": query,
            }
            if abstract_reply:
                last_result["abstractReply"] = abstract_reply

            if results or not wait_for_indexing:
                return last_result

            elapsed = time.time() - start_time
            if elapsed >= max_wait_seconds:
                last_result["message"] = (
                    f"No results found after waiting "
                    f"{max_wait_seconds}s for indexing. "
                    f"Memories may still be processing."
                )
                return last_result

            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # List Memories
    # ------------------------------------------------------------------

    def goodmem_list_memories(
        self,
        space_id: str,
        status_filter: Optional[str] = None,
        include_content: bool = False,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        r"""Lists all memories in a space.

        Returns metadata for every memory stored in the given space,
        with optional filtering by processing status and sorting.
        Set ``include_content=True`` to also receive each memory's
        original document content in a single call.

        Args:
            space_id (str): The UUID of the space to list memories
                from.
            status_filter (Optional[str]): Filter by processing
                status. One of ``PENDING``, ``PROCESSING``,
                ``COMPLETED``, or ``FAILED``.
                (default: :obj:`None`)
            include_content (bool): Whether each returned memory
                should include its original document content in
                addition to metadata. (default: :obj:`False`)
            sort_by (Optional[str]): Field to sort by. One of
                ``created_at`` or ``updated_at``.
                (default: :obj:`None`)
            sort_order (Optional[str]): Sort direction. One of
                ``ASCENDING`` or ``DESCENDING``.
                (default: :obj:`None`)

        Returns:
            List[Dict[str, Any]]: A list of memory objects.
        """
        params: Dict[str, str] = {}
        if include_content:
            params["includeContent"] = "true"
        if status_filter:
            params["statusFilter"] = status_filter
        if sort_by:
            params["sortBy"] = sort_by
        if sort_order:
            params["sortOrder"] = sort_order

        response = self._session.get(
            f"{self.base_url}/v1/spaces/{space_id}/memories",
            headers=self._headers(include_content_type=False),
            params=params,
        )
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, list) else body.get("memories", [])

    # ------------------------------------------------------------------
    # Get Memory
    # ------------------------------------------------------------------

    def goodmem_get_memory(
        self,
        memory_id: str,
        include_content: bool = True,
    ) -> Dict[str, Any]:
        r"""Fetches a specific memory record by its ID.

        Uses two separate endpoints: ``GET /v1/memories/{id}`` for
        metadata and ``GET /v1/memories/{id}/content`` for content.
        This separation allows efficient status polling without
        fetching potentially large content unnecessarily.

        Args:
            memory_id (str): The UUID of the memory to fetch.
            include_content (bool): Whether to also fetch the original
                document content via the ``/content`` endpoint.
                (default: :obj:`True`)

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``memory``, and optionally ``content`` (original
                document content) or ``contentError`` (set when
                the ``/content`` endpoint cannot be reached or
                returns an error).
        """
        response = self._session.get(
            f"{self.base_url}/v1/memories/{memory_id}",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        body = response.json()

        result: Dict[str, Any] = {
            "success": True,
            "memory": body,
        }

        if include_content:
            try:
                content_response = self._session.get(
                    f"{self.base_url}/v1/memories/{memory_id}/content",
                    headers=self._headers(include_content_type=False),
                )
                content_response.raise_for_status()
                content_type = content_response.headers.get("Content-Type", "")
                if "text" in content_type:
                    result["content"] = content_response.text
                else:
                    result["content"] = content_response.content
            except requests.RequestException as request_error:
                result["contentError"] = (
                    f"Failed to fetch content: {request_error}"
                )

        return result

    # ------------------------------------------------------------------
    # Delete Memory
    # ------------------------------------------------------------------

    def goodmem_delete_memory(self, memory_id: str) -> Dict[str, Any]:
        r"""Permanently deletes a memory and its associated data.

        Removes the memory record along with all its chunks and vector
        embeddings.

        Args:
            memory_id (str): The UUID of the memory to delete.

        Returns:
            Dict[str, Any]: A dictionary with keys ``success``,
                ``memoryId``, and ``message``.
        """
        response = self._session.delete(
            f"{self.base_url}/v1/memories/{memory_id}",
            headers=self._headers(include_content_type=False),
        )
        response.raise_for_status()
        return {
            "success": True,
            "memoryId": memory_id,
            "message": "Memory deleted successfully",
        }

    # ------------------------------------------------------------------
    # get_tools
    # ------------------------------------------------------------------

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for this toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.goodmem_list_embedders),
            FunctionTool(self.goodmem_list_spaces),
            FunctionTool(self.goodmem_get_space),
            FunctionTool(self.goodmem_create_space),
            FunctionTool(self.goodmem_update_space),
            FunctionTool(self.goodmem_delete_space),
            FunctionTool(self.goodmem_create_memory),
            FunctionTool(self.goodmem_list_memories),
            FunctionTool(self.goodmem_retrieve_memories),
            FunctionTool(self.goodmem_get_memory),
            FunctionTool(self.goodmem_delete_memory),
        ]
