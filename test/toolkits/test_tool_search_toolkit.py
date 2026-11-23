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
import re
from threading import Event, Thread, get_ident
from typing import Literal, Optional
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from camel.embeddings import BaseEmbedding
from camel.toolkits import (
    BaseToolkit,
    BaseToolSearchBackend,
    BM25ToolSearchBackend,
    EmbeddingToolSearchBackend,
    FunctionTool,
    ToolSearchToolkit,
)


class MockEmbedding(BaseEmbedding[str]):
    r"""Deterministic mock embedding model for testing."""

    def __init__(self, dim: int = 4) -> None:
        self.dim = dim

    def embed_list(self, objs: list[str], **kwargs) -> list[list[float]]:
        results = []
        for obj in objs:
            text = set(re.findall(r"[a-z]+", str(obj).lower()))
            vec = [0.0] * self.dim
            if any(
                k in text
                for k in ("weather", "rain", "temperature", "forecast")
            ):
                vec[0] = 1.0
            if any(k in text for k in ("math", "calculate", "sum", "add")):
                vec[1] = 1.0
            if any(k in text for k in ("email", "mail", "send")):
                vec[2] = 1.0
            if any(k in text for k in ("search", "find", "query")):
                vec[3] = 1.0
            if sum(vec) == 0:
                vec = [0.1] * self.dim
            results.append(vec)
        return results

    def get_output_dim(self) -> int:
        return self.dim


class DummySampleToolkit(BaseToolkit):
    r"""Sample toolkit for testing tool unwrapping and registration."""

    def get_weather(self, city: str) -> str:
        r"""Fetches the current weather for a specified city.

        Args:
            city (str): Name of the city.

        Returns:
            str: Weather report.
        """
        return f"Sunny in {city}"

    def get_tools(self) -> list[FunctionTool]:
        return [FunctionTool(self.get_weather)]


def calculate_sum(a: int, b: int) -> int:
    r"""Calculates the sum of two integers.

    Args:
        a (int): First integer.
        b (int): Second integer.

    Returns:
        int: Sum of a and b.
    """
    return a + b


def send_notification_email(recipient: str, body: str) -> str:
    r"""Sends an email notification to the given recipient.

    Args:
        recipient (str): Email address of the recipient.
        body (str): Email content body.

    Returns:
        str: Status message.
    """
    return f"Sent email to {recipient}"


def function_without_docstring(data: str) -> str:
    return data


def test_base_tool_search_backend_abstract():
    r"""Test that BaseToolSearchBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseToolSearchBackend()  # type: ignore[abstract]


def test_tool_registration_and_deduplication():
    r"""Test tool registration from BaseToolkit, FunctionTool,
    Callable and deduplication."""
    toolkit = ToolSearchToolkit(backend="bm25")

    # 1. Register a BaseToolkit
    sample_tk = DummySampleToolkit()
    toolkit.register_tools(sample_tk)
    assert len(toolkit.tools) == 1
    assert toolkit.tools[0].get_function_name() == "get_weather"

    # 2. Register a FunctionTool and a Callable
    func_tool = FunctionTool(calculate_sum)
    toolkit.register_tools([func_tool, send_notification_email])
    assert len(toolkit.tools) == 3
    tool_names = {t.get_function_name() for t in toolkit.tools}
    assert tool_names == {
        "get_weather",
        "calculate_sum",
        "send_notification_email",
    }

    # 3. Deduplication: register another FunctionTool with the same name
    duplicate_tool = FunctionTool(calculate_sum)
    toolkit.register_tools(duplicate_tool)
    assert len(toolkit.tools) == 3  # Count should not increase

    # 4. Invalid tool type raises TypeError
    with pytest.raises(TypeError):
        toolkit.register_tools("invalid_tool_string")  # type: ignore[arg-type]


def test_bm25_backend_ranking_and_tokenization():
    r"""Test BM25 search ranking, camelCase/snake_case tokenization,
    and threshold."""
    backend = BM25ToolSearchBackend()
    tools = [
        FunctionTool(calculate_sum),
        FunctionTool(send_notification_email),
        FunctionTool(DummySampleToolkit().get_weather),
    ]
    backend.build_index(tools)

    # Query matching weather
    weather_results = backend.search("What is the weather in Tokyo?", top_k=2)
    assert len(weather_results) >= 1
    top_tool, score = weather_results[0]
    assert top_tool.get_function_name() == "get_weather"
    assert score > 0.0

    # Query matching addition/math
    math_results = backend.search("calculate sum of two numbers", top_k=1)
    assert len(math_results) == 1
    top_tool, score = math_results[0]
    assert top_tool.get_function_name() == "calculate_sum"
    assert score > 0.0

    # Query with high threshold that filters out low matches
    filtered_results = backend.search("weather", top_k=5, threshold=100.0)
    assert len(filtered_results) == 0

    # Non-matching query returns empty list when threshold=0.0
    irrelevant_results = backend.search(
        "completely unrelated query xyz123", top_k=5
    )
    assert len(irrelevant_results) == 0


def test_embedding_backend():
    r"""Test EmbeddingToolSearchBackend semantic matching using
    mock embeddings."""
    mock_emb = MockEmbedding(dim=4)
    backend = EmbeddingToolSearchBackend(embedding=mock_emb)

    tools = [
        FunctionTool(calculate_sum),
        FunctionTool(send_notification_email),
        FunctionTool(DummySampleToolkit().get_weather),
    ]
    backend.build_index(tools)

    # Query matching rain/forecast (semantic proximity to weather)
    results = backend.search("forecast rain tomorrow", top_k=1)
    assert len(results) == 1
    top_tool, sim = results[0]
    assert top_tool.get_function_name() == "get_weather"
    assert sim > 0.9

    # Query matching send mail
    results = backend.search("send mail alert", top_k=1)
    assert len(results) == 1
    top_tool, sim = results[0]
    assert top_tool.get_function_name() == "send_notification_email"
    assert sim > 0.9


def test_edge_cases_and_error_handling():
    r"""Test boundary conditions, empty inputs, and invalid arguments."""
    # 1. Error when top_k <= 0
    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        ToolSearchToolkit(top_k=0)

    # 2. Error when search top_k <= 0
    toolkit = ToolSearchToolkit(
        tools=[calculate_sum],
        backend="bm25",
    )
    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        toolkit.filter_tools("math", top_k=-1)

    # 3. Empty tools registry returns empty list
    empty_toolkit = ToolSearchToolkit()
    assert empty_toolkit.filter_tools("weather") == []

    # 4. Empty or whitespace query returns top-k tools from registry
    fallback_tools = toolkit.filter_tools("   ", top_k=1)
    assert len(fallback_tools) == 1
    assert fallback_tools[0].get_function_name() == "calculate_sum"

    # 5. Function without docstring does not fail during indexing
    no_doc_toolkit = ToolSearchToolkit(
        tools=[function_without_docstring],
        backend="bm25",
    )
    res = no_doc_toolkit.filter_tools("function_without_docstring", top_k=1)
    assert len(res) == 1
    assert res[0].get_function_name() == "function_without_docstring"

    # 6. Unsupported backend string raises ValueError
    with pytest.raises(ValueError, match="Unsupported backend"):
        ToolSearchToolkit(backend="invalid_backend")

    # 7. Embedding backend without embedding model raises ValueError
    with pytest.raises(ValueError, match="BaseEmbedding must be provided"):
        ToolSearchToolkit(backend="embedding", embedding=None)


def test_filter_tools_end_to_end():
    r"""Test end-to-end filter_tools with BM25 and custom backend."""
    all_tools = [
        DummySampleToolkit(),
        calculate_sum,
        send_notification_email,
    ]
    # Initialize with all tools
    search_toolkit = ToolSearchToolkit(
        tools=all_tools,
        backend="bm25",
        top_k=2,
    )

    filtered = search_toolkit.filter_tools(
        "send an email notification", top_k=1
    )
    assert len(filtered) == 1
    assert isinstance(filtered[0], FunctionTool)
    assert filtered[0].get_function_name() == "send_notification_email"

    # Static selection exposes no runtime meta-tools.
    assert search_toolkit.get_tools() == []
    assert ToolSearchToolkit([search_toolkit]).tools == []


def test_custom_backend_and_embedding_toolkit():
    r"""Test ToolSearchToolkit with an explicit backend instance
    and embedding backend."""
    mock_emb = MockEmbedding(dim=4)

    # 1. Test embedding backend integration
    search_toolkit_emb = ToolSearchToolkit(
        tools=[calculate_sum, send_notification_email],
        backend="embedding",
        embedding=mock_emb,
    )
    res = search_toolkit_emb.filter_tools("please send mail", top_k=1)
    assert len(res) == 1
    assert res[0].get_function_name() == "send_notification_email"

    # 2. Test explicit custom backend instance
    custom_backend = BM25ToolSearchBackend()
    search_toolkit_custom = ToolSearchToolkit(
        tools=[calculate_sum],
        backend=custom_backend,
    )
    assert search_toolkit_custom.backend is custom_backend

    # 3. Test additional tool registration
    search_toolkit_custom.register_tools([send_notification_email])
    assert len(search_toolkit_custom.tools) == 2
    res2 = search_toolkit_custom.filter_tools("email", top_k=1)
    assert len(res2) == 1
    assert res2[0].get_function_name() == "send_notification_email"


def test_registration_failure_preserves_registry_and_index(monkeypatch):
    embedding = MockEmbedding()
    original = FunctionTool(calculate_sum)
    toolkit = ToolSearchToolkit(
        original, backend="embedding", embedding=embedding
    )
    replacement = FunctionTool(DummySampleToolkit().get_weather)
    replacement.set_function_name(original.get_function_name())

    with monkeypatch.context() as patch:
        patch.setattr(
            embedding, "embed_list", Mock(side_effect=RuntimeError("offline"))
        )
        with pytest.raises(RuntimeError, match="offline"):
            toolkit.register_tools(replacement)
    assert toolkit.tools == [original]
    assert toolkit.filter_tools("math") == [original]

    with pytest.raises(TypeError):
        toolkit.register_tools([send_notification_email, 123])
    assert toolkit.tools == [original]
    # A later registration must not pick up tools from the rejected batch.
    toolkit.register_tools(DummySampleToolkit())
    assert {t.get_function_name() for t in toolkit.tools} == {
        "calculate_sum",
        "get_weather",
    }


def test_backend_build_failure_preserves_index(monkeypatch):
    backend = BM25ToolSearchBackend()
    original = FunctionTool(calculate_sum)
    backend.build_index([original])
    monkeypatch.setattr(
        backend, "_bm25_cls", Mock(side_effect=RuntimeError("index failed"))
    )
    with pytest.raises(RuntimeError, match="index failed"):
        backend.build_index([FunctionTool(send_notification_email)])
    assert backend.search("calculate")[0][0] is original


def test_backend_cannot_be_shared():
    backend = BM25ToolSearchBackend()
    first = ToolSearchToolkit(calculate_sum, backend=backend)
    with pytest.raises(ValueError, match="already.*toolkit"):
        ToolSearchToolkit(send_notification_email, backend=backend)
    assert first.filter_tools("email") == []
    assert first.filter_tools("calculate") == first.tools


@pytest.mark.parametrize("tools", [None, []])
def test_empty_registry_clears_prebuilt_backend(tools):
    backend = BM25ToolSearchBackend()
    backend.build_index([FunctionTool(calculate_sum)])
    toolkit = ToolSearchToolkit(tools, backend=backend)
    assert toolkit.tools == []
    assert toolkit.filter_tools("calculate") == []


@pytest.mark.parametrize("query", ["查询天气", "!!!", "🦄"])
@pytest.mark.parametrize("threshold", [0.0, 999.0])
def test_nonmatching_query_never_falls_back(query, threshold):
    toolkit = ToolSearchToolkit(calculate_sum)
    assert toolkit.filter_tools(query, threshold=threshold) == []


@pytest.mark.parametrize(
    "name, queries",
    [
        ("parseJSONString", ["parsejsonstring", "PARSEJSONSTRING", "json"]),
        ("getWeatherV2", ["getweatherv2", "weather", "v2", "2"]),
        ("get_weather", ["GET_WEATHER", "weather"]),
        ("查询天气", ["查询天气"]),
        ("US", ["US", "us"]),
        ("IT", ["IT", "it"]),
    ],
)
def test_identifier_recall(name, queries):
    tool = FunctionTool(function_without_docstring)
    tool.set_function_name(name)
    toolkit = ToolSearchToolkit([tool, calculate_sum])
    for query in queries:
        assert toolkit.filter_tools(query, top_k=1) == [tool]


class SearchOptions(BaseModel):
    target: Literal["pulsar", "supernova"]


def select_mode(
    mode: Optional[Literal["quasar", "nebula"]], nodes: list[SearchOptions]
) -> None:
    r"""Select an astronomical mode.

    Args:
        mode: Mode selector.
        nodes: Requested targets.
    """


def test_nested_schema_indexing_in_both_backends():
    tool = FunctionTool(select_mode)
    schema = tool.get_openai_tool_schema()["function"]["parameters"]
    assert "$defs" in schema
    assert "anyOf" in schema["properties"]["mode"]
    toolkit = ToolSearchToolkit([tool, calculate_sum])
    for query in ("quasar", "nebula", "pulsar", "supernova", "target"):
        assert toolkit.filter_tools(query, top_k=1) == [tool]

    embedding = MockEmbedding()
    embedding.embed_list = Mock(wraps=embedding.embed_list)
    EmbeddingToolSearchBackend(embedding).build_index([tool])
    text = embedding.embed_list.call_args.args[0][0]
    for term in ("quasar", "pulsar", "target", "Mode selector"):
        assert term in text


def test_schema_property_names_and_literal_values_remain_searchable():
    tool = FunctionTool(
        function_without_docstring,
        openai_tool_schema={
            "type": "function",
            "function": {
                "name": "select_option",
                "description": "Select an option.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "description": "Output category.",
                            "const": "quasar",
                        },
                        "description": {
                            "type": "string",
                            "description": "A nebula label.",
                        },
                    },
                },
            },
        },
    )
    toolkit = ToolSearchToolkit(tool)
    for query in ("type", "description", "quasar", "nebula"):
        assert toolkit.filter_tools(query) == [tool]


def test_single_letter_function_name_can_be_searched():
    def a():
        pass

    toolkit = ToolSearchToolkit(a)
    assert toolkit.filter_tools("a") == toolkit.tools
    assert toolkit.filter_tools("unknown") == []
    assert len(toolkit.filter_tools("")) == 1


def test_zero_embeddings_are_finite():
    embedding = MockEmbedding()
    embedding.embed_list = Mock(return_value=[[0.0] * 4])
    backend = EmbeddingToolSearchBackend(embedding)
    tool = FunctionTool(calculate_sum)
    backend.build_index([tool])
    assert backend.search("unknown") == []
    assert backend.search("unknown", threshold=-1) == [(tool, 0.0)]


def test_incomplete_embeddings_preserve_index(monkeypatch):
    embedding = MockEmbedding()
    backend = EmbeddingToolSearchBackend(embedding)
    original = FunctionTool(calculate_sum)
    backend.build_index([original])
    with monkeypatch.context() as patch:
        patch.setattr(embedding, "embed_list", Mock(return_value=[[1.0] * 4]))
        with pytest.raises(ValueError, match="one embedding vector per tool"):
            backend.build_index(
                [original, FunctionTool(send_notification_email)]
            )
    assert backend.search("math", top_k=1)[0][0] is original


def test_small_bm25_corpus_keeps_matching_terms():
    tools = [
        FunctionTool(calculate_sum),
        FunctionTool(send_notification_email),
    ]
    for corpus in (tools[:1], tools):
        backend = BM25ToolSearchBackend()
        backend.build_index(corpus)
        assert backend.search("calculate")[0][0] is tools[0]
        assert backend.search("calculate")[0][1] > 0


def test_search_uses_index_snapshot_during_registration(monkeypatch):
    embedding = MockEmbedding()
    original = FunctionTool(calculate_sum)
    toolkit = ToolSearchToolkit(
        original, backend="embedding", embedding=embedding
    )
    release = Event()
    started = Event()
    results = []

    def slow_embed(query):
        started.set()
        assert release.wait(5)
        return [0.0, 1.0, 0.0, 0.0]

    replacement = FunctionTool(DummySampleToolkit().get_weather)
    replacement.set_function_name(original.get_function_name())
    with monkeypatch.context() as patch:
        patch.setattr(embedding, "embed", slow_embed)
        thread = Thread(
            target=lambda: results.extend(toolkit.filter_tools("math"))
        )
        thread.start()
        try:
            assert started.wait(5)
            toolkit.register_tools(replacement)
        finally:
            release.set()
            thread.join(5)
            assert not thread.is_alive()
    assert results == [original]
    assert toolkit.filter_tools("weather", top_k=1) == [replacement]
    assert toolkit.tools == [replacement]


def test_embedding_calls_stay_synchronous_and_propagate_timeout(monkeypatch):
    embedding = MockEmbedding()
    caller = get_ident()
    embed_list = embedding.embed_list

    def check_thread(objs):
        assert get_ident() == caller
        return embed_list(objs)

    monkeypatch.setattr(embedding, "embed_list", check_thread)
    toolkit = ToolSearchToolkit(
        calculate_sum, backend="embedding", embedding=embedding
    )
    assert toolkit.register_tools(send_notification_email) is None
    assert len(toolkit.tools) == 2
    assert toolkit.filter_tools("math", top_k=1) == toolkit.tools[:1]

    timeout = TimeoutError("Embedding request timed out")
    monkeypatch.setattr(embedding, "embed_list", Mock(side_effect=timeout))
    with pytest.raises(TimeoutError) as error:
        toolkit.filter_tools("math")
    assert error.value is timeout
    original_tools = toolkit.tools.copy()
    with pytest.raises(TimeoutError):
        toolkit.register_tools(DummySampleToolkit())
    assert toolkit.tools == original_tools


@pytest.mark.parametrize("backend_name", ["bm25", "embedding"])
def test_search_threshold_boundaries(backend_name):
    tools = [
        FunctionTool(calculate_sum),
        FunctionTool(send_notification_email),
    ]
    backend = (
        BM25ToolSearchBackend()
        if backend_name == "bm25"
        else EmbeddingToolSearchBackend(MockEmbedding())
    )
    backend.build_index(tools)
    matches = backend.search("calculate")
    assert [tool for tool, _ in matches] == tools[:1]
    score = matches[0][1]
    assert backend.search("calculate", threshold=score) == []
    assert backend.search("calculate", threshold=score / 2) == matches
    assert [
        tool for tool, _ in backend.search("calculate", threshold=-1)
    ] == tools


def test_constructor_search_defaults_can_be_overridden():
    toolkit = ToolSearchToolkit(
        [calculate_sum, send_notification_email], top_k=1, threshold=100
    )
    assert toolkit.filter_tools("calculate") == []
    assert toolkit.filter_tools("calculate", threshold=0) == toolkit.tools[:1]
    assert toolkit.filter_tools(" ") == toolkit.tools[:1]
    assert toolkit.filter_tools(" ", top_k=2) == toolkit.tools


def test_cosine_similarity_is_independent_of_vector_length(monkeypatch):
    embedding = MockEmbedding()
    monkeypatch.setattr(
        embedding, "embed_list", Mock(return_value=[[3.0, 4.0], [30.0, 40.0]])
    )
    tools = [
        FunctionTool(calculate_sum),
        FunctionTool(send_notification_email),
    ]
    backend = EmbeddingToolSearchBackend(embedding)
    backend.build_index(tools)
    monkeypatch.setattr(embedding, "embed", Mock(return_value=[6.0, 8.0]))
    matches = backend.search("query")
    assert [tool for tool, _ in matches] == tools
    assert [score for _, score in matches] == pytest.approx([1.0, 1.0])
