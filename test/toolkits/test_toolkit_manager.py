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
from typing import Any, ClassVar, List

import pytest

from camel.embeddings import BaseEmbedding
from camel.toolkits import FunctionTool, MathToolkit, ToolkitManager

# ``rank_bm25`` backs the default search backend.
pytest.importorskip("rank_bm25")


def fetch_weather(city: str) -> str:
    r"""Get the current weather forecast for a city.

    Args:
        city (str): The name of the city.

    Returns:
        str: A weather description.
    """
    return f"Sunny in {city}."


def send_email(recipient: str, body: str) -> str:
    r"""Send an email message to a recipient.

    Args:
        recipient (str): The email address of the recipient.
        body (str): The body of the email message.

    Returns:
        str: A confirmation string.
    """
    return f"Sent to {recipient}: {body}"


class _BagOfWordsEmbedding(BaseEmbedding):
    r"""Deterministic, offline embedding for tests.

    Each text is embedded as token-count vector over a fixed vocabulary, so
    semantic similarity reduces to keyword overlap without any network call.
    """

    VOCAB: ClassVar[List[str]] = [
        "weather",
        "forecast",
        "city",
        "email",
        "message",
        "send",
        "recipient",
        "add",
        "sum",
        "number",
    ]

    def embed_list(self, objs: List[str], **kwargs: Any) -> List[List[float]]:
        vectors = []
        for obj in objs:
            tokens = obj.lower().replace(".", " ").replace(",", " ").split()
            vectors.append([float(tokens.count(word)) for word in self.VOCAB])
        return vectors

    def get_output_dim(self) -> int:
        return len(self.VOCAB)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_register_expands_toolkit_and_dedups():
    manager = ToolkitManager([MathToolkit()])
    assert len(manager) == 5
    assert "math_divide" in manager
    assert set(manager.tool_names) == {
        "math_add",
        "math_subtract",
        "math_multiply",
        "math_divide",
        "math_round",
    }

    # Registering the same toolkit again must not create duplicates.
    manager.add(MathToolkit())
    assert len(manager) == 5


def test_register_function_tool_and_callable():
    manager = ToolkitManager()
    assert len(manager) == 0

    returned = manager.add(fetch_weather)  # plain callable
    assert returned is manager  # chainable
    manager.add(FunctionTool(send_email))  # FunctionTool instance

    assert len(manager) == 2
    assert "fetch_weather" in manager
    assert "send_email" in manager
    assert all(isinstance(t, FunctionTool) for t in manager.get_all_tools())


def test_register_rejects_unsupported_type():
    manager = ToolkitManager()
    with pytest.raises(TypeError):
        manager.add(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Initialization validation
# ---------------------------------------------------------------------------
def test_init_validation():
    with pytest.raises(ValueError):
        ToolkitManager(search_backend="invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ToolkitManager(default_top_k=0)


# ---------------------------------------------------------------------------
# BM25 search
# ---------------------------------------------------------------------------
def test_search_ranks_relevant_tool_first():
    manager = ToolkitManager([MathToolkit()])
    results = manager.search_tools("divide one number by another", top_k=3)
    assert len(results) == 3
    assert results[0].get_function_name() == "math_divide"


def test_search_respects_top_k_and_with_scores():
    manager = ToolkitManager([MathToolkit()])

    top1 = manager.search_tools("multiply", top_k=1)
    assert len(top1) == 1
    assert top1[0].get_function_name() == "math_multiply"

    scored = manager.search_tools("subtract", top_k=2, with_scores=True)
    assert len(scored) == 2
    assert all(
        isinstance(tool, FunctionTool) and isinstance(score, float)
        for tool, score in scored
    )
    # Scores must be sorted descending.
    assert scored[0][1] >= scored[1][1]


def test_search_top_k_larger_than_registry_returns_all():
    manager = ToolkitManager([MathToolkit()])
    results = manager.search_tools("add", top_k=100)
    assert len(results) == len(manager) == 5


def test_search_uses_default_top_k():
    manager = ToolkitManager([MathToolkit()], default_top_k=2)
    assert len(manager.search_tools("add")) == 2


def test_search_index_refreshes_after_add():
    manager = ToolkitManager([MathToolkit()])
    manager.search_tools("add")  # builds the index
    manager.add(fetch_weather)  # marks the index dirty
    names = [t.get_function_name() for t in manager.search_tools("weather")]
    assert "fetch_weather" in names


def test_search_validation():
    manager = ToolkitManager([MathToolkit()])
    with pytest.raises(ValueError):
        manager.search_tools("")
    with pytest.raises(ValueError):
        manager.search_tools("   ")
    with pytest.raises(ValueError):
        manager.search_tools("add", top_k=0)


def test_search_on_empty_manager_returns_empty():
    manager = ToolkitManager()
    assert manager.search_tools("anything") == []


# ---------------------------------------------------------------------------
# Embedding backend
# ---------------------------------------------------------------------------
def test_embedding_backend_ranks_by_similarity():
    manager = ToolkitManager(
        [fetch_weather, send_email],
        search_backend="embedding",
        embedding_model=_BagOfWordsEmbedding(),
    )
    results = manager.search_tools("send an email message", top_k=2)
    assert results[0].get_function_name() == "send_email"

    results = manager.search_tools("weather forecast for a city", top_k=2)
    assert results[0].get_function_name() == "fetch_weather"


def test_embedding_backend_handles_unmatched_query():
    # A query with no overlapping vocabulary yields all-zero similarity but
    # must not raise (zero vectors are normalized safely).
    manager = ToolkitManager(
        [fetch_weather, send_email],
        search_backend="embedding",
        embedding_model=_BagOfWordsEmbedding(),
    )
    results = manager.search_tools("zzz", top_k=2)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Agentic meta-tools
# ---------------------------------------------------------------------------
def test_get_search_tools_names():
    manager = ToolkitManager([MathToolkit()])
    meta = manager.get_search_tools()
    assert [t.get_function_name() for t in meta] == [
        "search_tools",
        "execute_tool",
    ]


def test_meta_search_tools_returns_descriptions():
    manager = ToolkitManager([MathToolkit()])
    search_tools, _ = manager.get_search_tools()
    output = search_tools("add two numbers", 2)
    assert "math_add" in output
    assert "parameters:" in output


def test_meta_search_tools_handles_bad_query():
    manager = ToolkitManager([MathToolkit()])
    search_tools, _ = manager.get_search_tools()
    # The meta-tool must not raise for the model; it returns an error string.
    assert search_tools("", 2).startswith("Error:")


def test_meta_execute_tool_runs_tool():
    manager = ToolkitManager([MathToolkit()])
    _, execute_tool = manager.get_search_tools()
    assert execute_tool("math_add", {"a": 2, "b": 40}) == "42"


def test_meta_execute_tool_unknown_name_suggests_alternatives():
    manager = ToolkitManager([MathToolkit()])
    _, execute_tool = manager.get_search_tools()
    result = execute_tool("add", {"a": 1, "b": 2})
    assert "no tool named 'add'" in result
    assert "Did you mean" in result
    assert "math_add" in result


def test_meta_execute_tool_rejects_non_mapping_arguments():
    manager = ToolkitManager([MathToolkit()])
    _, execute_tool = manager.get_search_tools()
    result = execute_tool("math_add", ["a", "b"])  # type: ignore[arg-type]
    assert "must be a mapping" in result


def test_meta_execute_tool_reports_execution_error():
    manager = ToolkitManager([MathToolkit()])
    _, execute_tool = manager.get_search_tools()
    result = execute_tool("math_divide", {"a": 1, "b": 0})
    assert result.startswith("Error executing 'math_divide'")
