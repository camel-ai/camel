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
"""Unit tests for GoodMemToolkit.

All HTTP calls are mocked so no live GoodMem server is required.

Run with:
    python -m pytest test/toolkits/test_goodmem_toolkit.py -v
"""
import base64
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from camel.toolkits.goodmem_toolkit import GoodMemToolkit, _get_mime_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://api.goodmem.test"
API_KEY = "test-api-key-12345"


def _make_response(
    json_data=None, text=None, content=None, headers=None,
    status_code=200, raise_for_status=None
):
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    if content is not None:
        resp.content = content
    if text is not None:
        resp.text = text
    else:
        resp.text = json.dumps(json_data) if json_data else ""
    resp.headers = headers or {}
    if raise_for_status:
        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def toolkit():
    """Create a GoodMemToolkit with mocked session."""
    tk = GoodMemToolkit(base_url=BASE_URL, api_key=API_KEY)
    tk._session = MagicMock(spec=requests.Session)
    return tk


# ---------------------------------------------------------------------------
# Initialization & Validation
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for constructor and environment variable validation."""

    def test_init_with_explicit_args(self, toolkit):
        assert toolkit.base_url == BASE_URL
        assert toolkit.api_key == API_KEY
        assert toolkit.verify_ssl is True

    def test_init_strips_trailing_slash(self):
        tk = GoodMemToolkit(
            base_url="https://api.test/", api_key=API_KEY
        )
        assert tk.base_url == "https://api.test"
        tk.close()

    def test_init_from_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "GOODMEM_API_KEY": "env-key",
                "GOODMEM_BASE_URL": "https://env.test",
            },
        ):
            tk = GoodMemToolkit()
            assert tk.api_key == "env-key"
            assert tk.base_url == "https://env.test"
            tk.close()

    def test_init_missing_api_key_raises(self):
        with patch.dict(
            os.environ,
            {"GOODMEM_BASE_URL": "https://test"},
            clear=False,
        ):
            env = os.environ.copy()
            env.pop("GOODMEM_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="GOODMEM_API_KEY"):
                    GoodMemToolkit(base_url="https://test")

    def test_init_missing_base_url_raises(self):
        with patch.dict(
            os.environ,
            {"GOODMEM_API_KEY": "some-key"},
            clear=False,
        ):
            env = os.environ.copy()
            env.pop("GOODMEM_BASE_URL", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="GOODMEM_BASE_URL"):
                    GoodMemToolkit(api_key="some-key")

    def test_verify_ssl_false(self):
        tk = GoodMemToolkit(
            base_url=BASE_URL, api_key=API_KEY, verify_ssl=False
        )
        assert tk._session.verify is False
        tk.close()


# ---------------------------------------------------------------------------
# Context manager & session lifecycle
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    """Tests for close(), __enter__, __exit__."""

    def test_close_calls_session_close(self, toolkit):
        toolkit.close()
        toolkit._session.close.assert_called_once()

    def test_context_manager(self):
        tk = GoodMemToolkit(base_url=BASE_URL, api_key=API_KEY)
        tk._session = MagicMock(spec=requests.Session)
        with tk as ctx:
            assert ctx is tk
        tk._session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


class TestHeaders:
    """Tests for _headers() generation."""

    def test_headers_with_content_type(self, toolkit):
        h = toolkit._headers(include_content_type=True)
        assert h["X-API-Key"] == API_KEY
        assert h["Content-Type"] == "application/json"
        assert h["Accept"] == "application/json"

    def test_headers_without_content_type(self, toolkit):
        h = toolkit._headers(include_content_type=False)
        assert "Content-Type" not in h
        assert h["X-API-Key"] == API_KEY
        assert h["Accept"] == "application/json"

    def test_headers_default_includes_content_type(self, toolkit):
        h = toolkit._headers()
        assert "Content-Type" in h


# ---------------------------------------------------------------------------
# MIME type helper
# ---------------------------------------------------------------------------


class TestMimeType:
    """Tests for _get_mime_type."""

    def test_known_extensions(self):
        assert _get_mime_type("pdf") == "application/pdf"
        assert _get_mime_type("PNG") == "image/png"
        assert _get_mime_type(".jpg") == "image/jpeg"
        assert _get_mime_type("txt") == "text/plain"
        assert _get_mime_type("md") == "text/markdown"

    def test_unknown_extension(self):
        assert _get_mime_type("xyz") is None
        assert _get_mime_type("") is None


# ---------------------------------------------------------------------------
# list_embedders
# ---------------------------------------------------------------------------


class TestListEmbedders:
    """Tests for list_embedders."""

    def test_list_embedders_dict_response(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={
                "embedders": [
                    {
                        "embedderId": "emb-1",
                        "displayName": "Test Embedder",
                        "modelIdentifier": "model-v1",
                    }
                ]
            }
        )
        result = toolkit.list_embedders()
        assert len(result) == 1
        assert result[0]["embedderId"] == "emb-1"
        assert result[0]["displayName"] == "Test Embedder"
        # Verify GET headers don't include Content-Type
        call_kwargs = toolkit._session.get.call_args
        headers = call_kwargs[1]["headers"]
        assert "Content-Type" not in headers

    def test_list_embedders_list_response(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data=[
                {"id": "emb-2", "name": "Fallback Name", "model": "m2"}
            ]
        )
        result = toolkit.list_embedders()
        assert result[0]["embedderId"] == "emb-2"
        assert result[0]["displayName"] == "Fallback Name"
        assert result[0]["modelIdentifier"] == "m2"

    def test_list_embedders_http_error_propagates(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            raise_for_status=requests.HTTPError("401 Unauthorized")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.list_embedders()


# ---------------------------------------------------------------------------
# list_spaces
# ---------------------------------------------------------------------------


class TestListSpaces:
    """Tests for list_spaces."""

    def test_list_spaces_dict_response(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={
                "spaces": [
                    {
                        "spaceId": "sp-1",
                        "name": "My Space",
                        "spaceEmbedders": [{"embedderId": "emb-1"}],
                    },
                    {
                        "spaceId": "sp-2",
                        "name": "Other Space",
                        "spaceEmbedders": [],
                    },
                ]
            }
        )
        result = toolkit.list_spaces()
        assert len(result) == 2
        assert result[0]["spaceId"] == "sp-1"
        assert result[0]["spaceEmbedders"] == [{"embedderId": "emb-1"}]
        assert result[1]["spaceEmbedders"] == []
        # Verify no Content-Type on GET
        headers = toolkit._session.get.call_args[1]["headers"]
        assert "Content-Type" not in headers

    def test_list_spaces_empty(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={"spaces": []}
        )
        result = toolkit.list_spaces()
        assert result == []

    def test_list_spaces_no_space_embedders_field(self, toolkit):
        """Server response without spaceEmbedders should default to []."""
        toolkit._session.get.return_value = _make_response(
            json_data={"spaces": [{"spaceId": "sp-1", "name": "My Space"}]}
        )
        result = toolkit.list_spaces()
        assert result[0]["spaceEmbedders"] == []


# ---------------------------------------------------------------------------
# create_space
# ---------------------------------------------------------------------------


class TestCreateSpace:
    """Tests for create_space."""

    def test_create_space_new(self, toolkit):
        # list_spaces returns empty -> no reuse
        toolkit._session.get.return_value = _make_response(
            json_data={"spaces": []}
        )
        toolkit._session.post.return_value = _make_response(
            json_data={"spaceId": "new-sp", "name": "test-space"}
        )
        result = toolkit.create_space(
            name="test-space", embedder_id="emb-1"
        )
        assert result["success"] is True
        assert result["spaceId"] == "new-sp"
        assert result["reused"] is False
        # Verify POST was called with Content-Type
        post_headers = toolkit._session.post.call_args[1]["headers"]
        assert post_headers["Content-Type"] == "application/json"

    def test_create_space_reuse_existing(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={
                "spaces": [
                    {"spaceId": "existing-sp", "name": "test-space"}
                ]
            }
        )
        result = toolkit.create_space(
            name="test-space", embedder_id="emb-1"
        )
        assert result["success"] is True
        assert result["spaceId"] == "existing-sp"
        assert result["reused"] is True
        # POST should NOT have been called
        toolkit._session.post.assert_not_called()

    def test_create_space_reuse_returns_actual_embedder(self, toolkit):
        """Reused space should return the embedder from the existing space,
        not the caller-supplied one."""
        toolkit._session.get.return_value = _make_response(
            json_data={
                "spaces": [
                    {
                        "spaceId": "existing-sp",
                        "name": "test-space",
                        "spaceEmbedders": [
                            {"embedderId": "actual-emb-from-server"}
                        ],
                    }
                ]
            }
        )
        result = toolkit.create_space(
            name="test-space", embedder_id="caller-emb"
        )
        assert result["success"] is True
        assert result["reused"] is True
        assert result["embedderId"] == "actual-emb-from-server"
        toolkit._session.post.assert_not_called()

    def test_create_space_list_fails_still_creates(self, toolkit):
        # list_spaces fails with RequestException -> proceed to create
        toolkit._session.get.return_value = _make_response(
            raise_for_status=requests.RequestException("connection error")
        )
        toolkit._session.post.return_value = _make_response(
            json_data={"spaceId": "new-sp", "name": "test-space"}
        )
        result = toolkit.create_space(
            name="test-space", embedder_id="emb-1"
        )
        assert result["success"] is True
        assert result["reused"] is False

    def test_create_space_post_error_propagates(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={"spaces": []}
        )
        toolkit._session.post.return_value = _make_response(
            raise_for_status=requests.HTTPError("500 Server Error")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.create_space(name="fail", embedder_id="emb-1")


# ---------------------------------------------------------------------------
# create_memory
# ---------------------------------------------------------------------------


class TestCreateMemory:
    """Tests for create_memory."""

    def test_create_memory_text(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            json_data={
                "memoryId": "mem-1",
                "spaceId": "sp-1",
                "processingStatus": "PENDING",
            }
        )
        result = toolkit.create_memory(
            space_id="sp-1", text_content="Hello world"
        )
        assert result["success"] is True
        assert result["memoryId"] == "mem-1"
        assert result["contentType"] == "text/plain"
        assert result["status"] == "PENDING"
        # Verify request body
        body = toolkit._session.post.call_args[1]["json"]
        assert body["originalContent"] == "Hello world"
        assert body["contentType"] == "text/plain"

    def test_create_memory_text_file(self, toolkit):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False
        ) as f:
            f.write("file content here")
            tmp_path = f.name

        try:
            toolkit._session.post.return_value = _make_response(
                json_data={
                    "memoryId": "mem-f",
                    "spaceId": "sp-1",
                    "processingStatus": "PENDING",
                }
            )
            result = toolkit.create_memory(
                space_id="sp-1", file_path=tmp_path
            )
            assert result["success"] is True
            assert result["contentType"] == "text/plain"
            body = toolkit._session.post.call_args[1]["json"]
            assert body["originalContent"] == "file content here"
            assert "originalContentB64" not in body
        finally:
            os.unlink(tmp_path)

    def test_create_memory_binary_file(self, toolkit):
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        ) as f:
            f.write(b"%PDF-fake-content")
            tmp_path = f.name

        try:
            toolkit._session.post.return_value = _make_response(
                json_data={
                    "memoryId": "mem-pdf",
                    "spaceId": "sp-1",
                    "processingStatus": "PENDING",
                }
            )
            result = toolkit.create_memory(
                space_id="sp-1", file_path=tmp_path
            )
            assert result["success"] is True
            assert result["contentType"] == "application/pdf"
            body = toolkit._session.post.call_args[1]["json"]
            assert "originalContentB64" in body
            assert "originalContent" not in body
            # Verify base64 round-trip
            decoded = base64.b64decode(body["originalContentB64"])
            assert decoded == b"%PDF-fake-content"
        finally:
            os.unlink(tmp_path)

    def test_create_memory_no_content_returns_error(self, toolkit):
        result = toolkit.create_memory(space_id="sp-1")
        assert result["success"] is False
        assert "No content provided" in result["error"]
        toolkit._session.post.assert_not_called()

    def test_create_memory_with_metadata(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            json_data={
                "memoryId": "mem-m",
                "spaceId": "sp-1",
                "processingStatus": "PENDING",
            }
        )
        result = toolkit.create_memory(
            space_id="sp-1",
            text_content="test",
            metadata={"key": "value"},
        )
        assert result["success"] is True
        body = toolkit._session.post.call_args[1]["json"]
        assert body["metadata"] == {"key": "value"}

    def test_create_memory_http_error_propagates(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            raise_for_status=requests.HTTPError("400 Bad Request")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.create_memory(
                space_id="sp-1", text_content="test"
            )

    def test_create_memory_file_takes_priority(self, toolkit):
        with tempfile.NamedTemporaryFile(
            suffix=".md", mode="w", delete=False
        ) as f:
            f.write("# Markdown content")
            tmp_path = f.name

        try:
            toolkit._session.post.return_value = _make_response(
                json_data={
                    "memoryId": "mem-md",
                    "spaceId": "sp-1",
                    "processingStatus": "PENDING",
                }
            )
            result = toolkit.create_memory(
                space_id="sp-1",
                text_content="ignored text",
                file_path=tmp_path,
            )
            assert result["contentType"] == "text/markdown"
            body = toolkit._session.post.call_args[1]["json"]
            assert body["originalContent"] == "# Markdown content"
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# retrieve_memories
# ---------------------------------------------------------------------------

# Sample NDJSON responses matching GoodMem API format
NDJSON_WITH_RESULTS = "\n".join(
    [
        json.dumps(
            {
                "resultSetBoundary": {
                    "resultSetId": "rs-1",
                    "boundary": "START",
                }
            }
        ),
        json.dumps(
            {
                "retrievedItem": {
                    "chunk": {
                        "chunk": {
                            "chunkId": "c-1",
                            "chunkText": "CAMEL is a framework",
                            "memoryId": "mem-1",
                        },
                        "relevanceScore": 0.95,
                        "memoryIndex": 0,
                    }
                }
            }
        ),
        json.dumps(
            {
                "memoryDefinition": {
                    "memoryId": "mem-1",
                    "spaceId": "sp-1",
                }
            }
        ),
        json.dumps(
            {
                "resultSetBoundary": {
                    "resultSetId": "rs-1",
                    "boundary": "END",
                }
            }
        ),
    ]
)

NDJSON_EMPTY = json.dumps(
    {
        "resultSetBoundary": {
            "resultSetId": "rs-empty",
            "boundary": "START",
        }
    }
)

NDJSON_WITH_ABSTRACT = "\n".join(
    [
        json.dumps(
            {"resultSetBoundary": {"resultSetId": "rs-2", "boundary": "START"}}
        ),
        json.dumps(
            {
                "retrievedItem": {
                    "chunk": {
                        "chunk": {
                            "chunkId": "c-2",
                            "chunkText": "Some text",
                            "memoryId": "mem-2",
                        },
                        "relevanceScore": 0.8,
                        "memoryIndex": 0,
                    }
                }
            }
        ),
        json.dumps(
            {"abstractReply": {"text": "This is a summary"}}
        ),
    ]
)

SSE_FORMAT = "\n".join(
    [
        "event: message",
        'data: {"resultSetBoundary": {"resultSetId": "rs-sse"}}',
        "",
        "event: message",
        'data: {"retrievedItem": {"chunk": {"chunk": '
        '{"chunkId": "c-sse", "chunkText": "SSE text", '
        '"memoryId": "mem-sse"}, "relevanceScore": 0.9, '
        '"memoryIndex": 0}}}',
    ]
)


class TestRetrieveMemories:
    """Tests for retrieve_memories."""

    def test_retrieve_with_results(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=NDJSON_WITH_RESULTS
        )
        result = toolkit.retrieve_memories(
            query="What is CAMEL?",
            space_ids=["sp-1"],
            wait_for_indexing=False,
        )
        assert result["success"] is True
        assert result["totalResults"] == 1
        assert result["results"][0]["chunkId"] == "c-1"
        assert result["results"][0]["chunkText"] == "CAMEL is a framework"
        assert result["results"][0]["relevanceScore"] == 0.95
        assert result["resultSetId"] == "rs-1"
        assert len(result["memories"]) == 1

    def test_retrieve_empty_space_ids(self, toolkit):
        result = toolkit.retrieve_memories(
            query="test", space_ids=[], wait_for_indexing=False
        )
        assert result["success"] is False
        assert "At least one space" in result["error"]

    def test_retrieve_filters_empty_space_ids(self, toolkit):
        result = toolkit.retrieve_memories(
            query="test", space_ids=["", ""], wait_for_indexing=False
        )
        assert result["success"] is False

    def test_retrieve_with_abstract_reply(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=NDJSON_WITH_ABSTRACT
        )
        result = toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            wait_for_indexing=False,
        )
        assert result["success"] is True
        assert "abstractReply" in result
        assert result["abstractReply"]["text"] == "This is a summary"

    def test_retrieve_sse_format(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=SSE_FORMAT
        )
        result = toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            wait_for_indexing=False,
        )
        assert result["success"] is True
        assert result["totalResults"] == 1
        assert result["results"][0]["chunkId"] == "c-sse"

    def test_retrieve_wait_for_indexing_timeout(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=NDJSON_EMPTY
        )
        result = toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            wait_for_indexing=True,
            max_wait_seconds=0.1,
            poll_interval=0.05,
        )
        assert result["success"] is True
        assert result["totalResults"] == 0
        assert "No results found" in result.get("message", "")

    def test_retrieve_with_post_processor(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=NDJSON_WITH_RESULTS
        )
        toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            reranker_id="reranker-1",
            llm_id="llm-1",
            relevance_threshold=0.5,
            llm_temperature=0.3,
            chronological_resort=True,
            wait_for_indexing=False,
        )
        body = toolkit._session.post.call_args[1]["json"]
        assert "postProcessor" in body
        pp = body["postProcessor"]
        assert "ChatPostProcessorFactory" in pp["name"]
        cfg = pp["config"]
        assert cfg["reranker_id"] == "reranker-1"
        assert cfg["llm_id"] == "llm-1"
        assert cfg["relevance_threshold"] == 0.5
        assert cfg["llm_temp"] == 0.3
        assert cfg["chronological_resort"] is True

    def test_retrieve_http_error_propagates(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            raise_for_status=requests.HTTPError("500")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.retrieve_memories(
                query="test",
                space_ids=["sp-1"],
                wait_for_indexing=False,
            )

    def test_retrieve_ndjson_accept_header(self, toolkit):
        toolkit._session.post.return_value = _make_response(
            text=NDJSON_WITH_RESULTS
        )
        toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            wait_for_indexing=False,
        )
        headers = toolkit._session.post.call_args[1]["headers"]
        assert headers["Accept"] == "application/x-ndjson"

    def test_retrieve_configurable_wait_params(self, toolkit):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_response(text=NDJSON_EMPTY)

        toolkit._session.post.side_effect = side_effect
        result = toolkit.retrieve_memories(
            query="test",
            space_ids=["sp-1"],
            wait_for_indexing=True,
            max_wait_seconds=0.15,
            poll_interval=0.05,
        )
        assert result["totalResults"] == 0
        # Should have polled multiple times
        assert call_count >= 2


# ---------------------------------------------------------------------------
# get_memory
# ---------------------------------------------------------------------------


class TestGetMemory:
    """Tests for get_memory."""

    def test_get_memory_with_text_content(self, toolkit):
        meta_resp = _make_response(
            json_data={
                "memoryId": "mem-1",
                "processingStatus": "COMPLETED",
                "contentType": "text/plain",
            }
        )
        content_resp = _make_response(
            text="Hello world",
            headers={"Content-Type": "text/plain"},
        )
        toolkit._session.get.side_effect = [meta_resp, content_resp]
        result = toolkit.get_memory(memory_id="mem-1", include_content=True)
        assert result["success"] is True
        assert result["memory"]["memoryId"] == "mem-1"
        assert result["content"] == "Hello world"
        # Two GET calls: metadata then content endpoint
        assert toolkit._session.get.call_count == 2
        urls = [c[0][0] for c in toolkit._session.get.call_args_list]
        assert urls[0].endswith("/v1/memories/mem-1")
        assert urls[1].endswith("/v1/memories/mem-1/content")
        # No params or Content-Type on the metadata call
        first_kwargs = toolkit._session.get.call_args_list[0][1]
        assert "Content-Type" not in first_kwargs["headers"]
        assert not first_kwargs.get("params")

    def test_get_memory_binary_content(self, toolkit):
        raw_bytes = b"%PDF-fake-content"
        meta_resp = _make_response(
            json_data={
                "memoryId": "mem-pdf",
                "processingStatus": "COMPLETED",
                "contentType": "application/pdf",
            }
        )
        content_resp = _make_response(
            content=raw_bytes,
            headers={"Content-Type": "application/pdf"},
        )
        toolkit._session.get.side_effect = [meta_resp, content_resp]
        result = toolkit.get_memory(memory_id="mem-pdf", include_content=True)
        assert result["success"] is True
        assert result["content"] == raw_bytes

    def test_get_memory_without_content(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            json_data={"memoryId": "mem-1"}
        )
        result = toolkit.get_memory(
            memory_id="mem-1", include_content=False
        )
        assert result["success"] is True
        assert "content" not in result
        # Only one GET for metadata, /content endpoint not called
        assert toolkit._session.get.call_count == 1

    def test_get_memory_content_fetch_error_sets_content_error(self, toolkit):
        """When /content endpoint fails, contentError is set instead of raising."""
        meta_resp = _make_response(
            json_data={
                "memoryId": "mem-1",
                "processingStatus": "PROCESSING",
            }
        )
        content_resp = _make_response(
            raise_for_status=requests.RequestException("content not available")
        )
        toolkit._session.get.side_effect = [meta_resp, content_resp]
        result = toolkit.get_memory(memory_id="mem-1", include_content=True)
        assert result["success"] is True
        assert "content" not in result
        assert "contentError" in result
        assert "Failed to fetch content" in result["contentError"]

    def test_get_memory_content_http_error_sets_content_error(self, toolkit):
        """HTTP error from /content endpoint sets contentError, not exception."""
        meta_resp = _make_response(
            json_data={
                "memoryId": "mem-1",
                "processingStatus": "COMPLETED",
            }
        )
        content_resp = _make_response(
            raise_for_status=requests.HTTPError("404 Not Found")
        )
        toolkit._session.get.side_effect = [meta_resp, content_resp]
        result = toolkit.get_memory(memory_id="mem-1", include_content=True)
        assert result["success"] is True
        assert "content" not in result
        assert "contentError" in result

    def test_get_memory_metadata_error_propagates(self, toolkit):
        toolkit._session.get.return_value = _make_response(
            raise_for_status=requests.HTTPError("404")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.get_memory(memory_id="nonexistent")


# ---------------------------------------------------------------------------
# delete_memory
# ---------------------------------------------------------------------------


class TestDeleteMemory:
    """Tests for delete_memory."""

    def test_delete_memory_success(self, toolkit):
        toolkit._session.delete.return_value = _make_response(
            json_data={}
        )
        result = toolkit.delete_memory(memory_id="mem-1")
        assert result["success"] is True
        assert result["memoryId"] == "mem-1"
        # Verify DELETE doesn't include Content-Type
        headers = toolkit._session.delete.call_args[1]["headers"]
        assert "Content-Type" not in headers

    def test_delete_memory_error_propagates(self, toolkit):
        toolkit._session.delete.return_value = _make_response(
            raise_for_status=requests.HTTPError("404")
        )
        with pytest.raises(requests.HTTPError):
            toolkit.delete_memory(memory_id="nonexistent")


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------


class TestGetTools:
    """Tests for get_tools."""

    def test_get_tools_returns_seven_tools(self, toolkit):
        tools = toolkit.get_tools()
        assert len(tools) == 7

    def test_get_tools_correct_names(self, toolkit):
        tools = toolkit.get_tools()
        names = [t.get_function_name() for t in tools]
        expected = [
            "list_embedders",
            "list_spaces",
            "create_space",
            "create_memory",
            "retrieve_memories",
            "get_memory",
            "delete_memory",
        ]
        assert names == expected
