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

import json
import re
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from camel.embeddings import BaseEmbedding
from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit, manual_timeout
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required

logger = get_logger(__name__)


def _extract_tool_text(tool: FunctionTool) -> str:
    r"""Extracts the tool name, description and complete parameter schema."""
    function = tool.get_openai_tool_schema()["function"]
    parameters = json.dumps(function["parameters"], ensure_ascii=False)
    return (
        f"{function['name']}: {function.get('description', '')} "
        f"Parameters: {parameters}"
    )


class BaseToolSearchBackend(ABC):
    r"""Interface for building and searching a tool index."""

    _in_use: bool = False

    @abstractmethod
    def build_index(self, tools: List[FunctionTool]) -> None:
        r"""Builds or updates the search index for the given tools.

        Args:
            tools (List[FunctionTool]): The list of tools to index.
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[FunctionTool, float]]:
        r"""Searches for matching tools given a query.

        Args:
            query (str): The search query text.
            top_k (int, optional): Maximum number of tools to return.
                (default: :obj:`5`)
            threshold (float, optional): Only return tools with scores strictly
                greater than this value. (default: :obj:`0.0`)

        Returns:
            List[Tuple[FunctionTool, float]]: List of (tool, score) pairs,
                sorted descending by relevance score.
        """
        pass


class BM25ToolSearchBackend(BaseToolSearchBackend):
    r"""BM25 lexical search backend for tool retrieval.

    Scores tool names, descriptions and parameter schemas with BM25Okapi.
    Install the optional dependency with ``pip install "camel-ai[rag]"``.
    No API key or model download is required; scoring scans the corpus.
    """

    @dependencies_required('rank_bm25')
    def __init__(self) -> None:
        r"""Initializes BM25ToolSearchBackend."""
        from rank_bm25 import BM25Okapi

        self._bm25_cls = BM25Okapi
        self._index: Tuple[List[FunctionTool], Optional[BM25Okapi]] = (
            [],
            None,
        )

    def _tokenize(self, text: str) -> List[str]:
        r"""Subword tokenizer for code identifiers and natural language
        queries.

        Splits camelCase, acronym sequences, underscores, and punctuation
        while preserving original tokens for exact identifier matches.
        Unicode words are preserved without language-specific segmentation.

        Args:
            text (str): Input text string.

        Returns:
            List[str]: List of lowercase word and subword tokens.
        """
        tokens = []
        for word in re.findall(r"\w+", text):
            if not word.strip("_"):
                continue
            original = word.lower()
            tokens.append(original)
            split = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', word)
            split = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', split)
            tokens.extend(
                part.lower()
                for part in re.findall(r"[^\W\d_]+|\d+", split)
                if part.lower() != original
            )
        return tokens

    def build_index(self, tools: List[FunctionTool]) -> None:
        r"""Builds the BM25 index from a list of tools.

        Args:
            tools (List[FunctionTool]): The list of tools to index.
        """
        tools = list(tools)
        if not tools:
            self._index = ([], None)
            return

        corpus_tokens = [
            self._tokenize(_extract_tool_text(tool)) for tool in tools
        ]
        bm25 = self._bm25_cls(corpus_tokens)
        # BM25Okapi's epsilon floor can still be non-positive in tiny corpora.
        # Keep matching terms retrievable, including one- and two-tool banks.
        for word, idf_val in bm25.idf.items():
            if idf_val <= 0:
                bm25.idf[word] = 0.01
        self._index = (tools, bm25)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[FunctionTool, float]]:
        r"""Executes BM25 search and returns matching tools.

        Args:
            query (str): The search query text.
            top_k (int, optional): Maximum number of tools to return.
                (default: :obj:`5`)
            threshold (float, optional): Only return tools with scores strictly
                greater than this value. (default: :obj:`0.0`)

        Returns:
            List[Tuple[FunctionTool, float]]: List of (tool, score) tuples,
                sorted descending by score.

        Raises:
            ValueError: If `top_k` is less than or equal to 0.
        """
        if top_k <= 0:
            raise ValueError(f"top_k must be a positive integer, got {top_k}.")
        tools, bm25 = self._index
        if bm25 is None:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)
        scored_tools = [
            (tool, float(score))
            for tool, score in zip(tools, scores)
            if float(score) > threshold
        ]

        scored_tools.sort(key=lambda x: x[1], reverse=True)
        return scored_tools[:top_k]


class EmbeddingToolSearchBackend(BaseToolSearchBackend):
    r"""Embedding-based semantic search backend for tool retrieval.

    Computes cosine similarity between user queries and tools using an
    instance of `BaseEmbedding`. Every query calls ``embedding.embed``;
    registering tools re-embeds the entire collection. Batch registrations
    to avoid repeated embedding costs.
    """

    @dependencies_required('numpy')
    def __init__(self, embedding: BaseEmbedding) -> None:
        r"""Initializes EmbeddingToolSearchBackend.

        Args:
            embedding (BaseEmbedding): The embedding model instance used to
                embed tools and queries.

        Raises:
            ValueError: If `embedding` is None.
        """
        if embedding is None:
            raise ValueError("embedding model cannot be None.")
        self.embedding = embedding
        self._index: Tuple[List[FunctionTool], Optional[Any]] = ([], None)

    def build_index(self, tools: List[FunctionTool]) -> None:
        r"""Builds tool vector representations using the embedding model.

        Args:
            tools (List[FunctionTool]): Tools to embed and index.
        """
        import numpy as np

        tools = list(tools)
        if not tools:
            self._index = ([], None)
            return

        texts = [_extract_tool_text(tool) for tool in tools]
        # TODO: Add reusable persistent caching in the embedding layer, keyed
        # by text hash and provider/model configuration (including dimensions).
        raw_embeddings = self.embedding.embed_list(texts)
        emb_matrix = np.array(raw_embeddings, dtype=np.float32)
        if emb_matrix.ndim != 2 or emb_matrix.shape[0] != len(tools):
            raise ValueError("Expected one embedding vector per tool.")

        # Unit vectors make the search dot product equal cosine similarity.
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._index = (tools, emb_matrix / norms)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[FunctionTool, float]]:
        r"""Searches for semantically similar tools using cosine similarity.

        Args:
            query (str): The search query text.
            top_k (int, optional): Maximum number of tools to return.
                (default: :obj:`5`)
            threshold (float, optional): Only return tools with cosine
                similarity strictly greater than this value.
                (default: :obj:`0.0`)

        Returns:
            List[Tuple[FunctionTool, float]]: List of (tool, score) tuples,
                sorted descending by similarity score.

        Raises:
            ValueError: If `top_k` is less than or equal to 0.
        """
        import numpy as np

        if top_k <= 0:
            raise ValueError(f"top_k must be a positive integer, got {top_k}.")
        tools, tool_embeddings = self._index
        if tool_embeddings is None:
            return []

        if not query.strip():
            return []

        query_emb = np.array(self.embedding.embed(query), dtype=np.float32)
        query_norm = float(np.linalg.norm(query_emb)) or 1.0
        query_emb = query_emb / query_norm

        scores = np.dot(tool_embeddings, query_emb)
        scored_tools = [
            (tool, float(score))
            for tool, score in zip(tools, scores)
            if float(score) > threshold
        ]
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        return scored_tools[:top_k]


class ToolSearchToolkit(BaseToolkit):
    r"""Selects a relevant subset of tools before agent initialization.

    Reduces the number of tool schemas sent to the model. Provider schema
    constraints still apply to the selected tools. The default BM25 backend
    requires ``pip install "camel-ai[rag]"``.

    Indexing and filtering run synchronously. Configure network timeouts on
    the embedding client; its exceptions propagate to the caller.

    Args:
        tools (Optional[Union[Any, Sequence[Any]]], optional): Tools or
            toolkits to register upon initialization. (default: :obj:`None`)
        backend (Union[str, BaseToolSearchBackend], optional): Search backend
            to use ('bm25', 'embedding', or a custom BaseToolSearchBackend
            instance owned exclusively by this toolkit).
            (default: :obj:`"bm25"`)
        embedding (Optional[BaseEmbedding], optional): Embedding model
            instance required when backend is 'embedding'.
            (default: :obj:`None`)
        top_k (int, optional): Default maximum number of tools to
            return when searching. (default: :obj:`5`)
        threshold (float, optional): Default score threshold for
            filtering search results. (default: :obj:`0.0`)
    """

    def __init__(
        self,
        tools: Optional[
            Union[
                BaseToolkit,
                FunctionTool,
                Callable,
                Sequence[Union[BaseToolkit, FunctionTool, Callable]],
            ]
        ] = None,
        backend: Union[str, BaseToolSearchBackend] = "bm25",
        embedding: Optional[BaseEmbedding] = None,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> None:
        super().__init__(timeout=None)
        if top_k <= 0:
            raise ValueError(f"top_k must be a positive integer, got {top_k}.")
        self.top_k = top_k
        self.threshold = threshold

        if isinstance(backend, BaseToolSearchBackend):
            self.backend = backend
            if embedding is not None:
                logger.warning(
                    "An explicit BaseToolSearchBackend instance was provided; "
                    "the 'embedding' parameter will be ignored."
                )
        elif isinstance(backend, str):
            backend_key = backend.strip().lower()
            if backend_key == "bm25":
                self.backend = BM25ToolSearchBackend()
            elif backend_key == "embedding":
                if embedding is None:
                    raise ValueError(
                        "An instance of BaseEmbedding must be provided when "
                        "using the 'embedding' backend."
                    )
                self.backend = EmbeddingToolSearchBackend(embedding=embedding)
            else:
                raise ValueError(
                    f"Unsupported backend '{backend}'. Supported backends are "
                    "'bm25', 'embedding', or a BaseToolSearchBackend instance."
                )
        else:
            raise TypeError(
                f"Unsupported backend type '{type(backend)}'. Expected str or "
                "BaseToolSearchBackend."
            )

        if self.backend._in_use:
            raise ValueError("This backend already belongs to a toolkit.")
        self.tools: List[FunctionTool] = []
        if tools is not None:
            self.register_tools(tools)
        if not self.tools:
            self.backend.build_index([])
        self.backend._in_use = True

    @manual_timeout
    def register_tools(
        self,
        tools: Union[
            BaseToolkit,
            FunctionTool,
            Callable,
            Sequence[Union[BaseToolkit, FunctionTool, Callable]],
        ],
    ) -> None:
        r"""Registers and resolves tools into the toolkit, updating the index.

        Supports unpacking tools from `BaseToolkit` instances, `FunctionTool`
        objects, or standard Python callables. Tools with duplicate function
        names will be overridden.

        Each non-empty call rebuilds the full index synchronously, including
        re-embedding all tools for the embedding backend. Prefer registering
        tools in batches. Validation or index-build failures preserve the
        previous registration. Callers must serialize registration calls.

        Args:
            tools (Union[Any, Sequence[Any]]): The tools to register.

        Raises:
            TypeError: If an unsupported tool type is provided.
        """
        if isinstance(tools, (BaseToolkit, FunctionTool)) or callable(tools):
            tools = [tools]
        resolved = []
        for item in tools:
            if isinstance(item, BaseToolkit):
                resolved.extend(item.get_tools())
            elif isinstance(item, FunctionTool):
                resolved.append(item)
            elif callable(item):
                resolved.append(FunctionTool(item))
            else:
                raise TypeError(f"Unsupported tool type: {type(item)}")

        if not resolved:
            return
        candidate = {tool.get_function_name(): tool for tool in self.tools}
        candidate.update({tool.get_function_name(): tool for tool in resolved})

        candidate_tools = list(candidate.values())
        self.backend.build_index(candidate_tools)
        self.tools = candidate_tools

    @manual_timeout
    def filter_tools(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[FunctionTool]:
        r"""Filters tools based on relevance to the provided query.

        Args:
            query (str): The task or tools needed. A blank query returns the
                first top_k registered tools without scoring or threshold
                filtering. A non-blank query always goes through the backend.
            top_k (Optional[int], optional): Maximum number of tools to return.
                If None, uses the constructor's `top_k`.
                (default: :obj:`None`)
            threshold (Optional[float], optional): Only return tools with
                scores strictly greater than this value. If None, uses the
                constructor's `threshold`.
                (default: :obj:`None`)

        Returns:
            List[FunctionTool]: Relevant FunctionTool objects.

        Raises:
            ValueError: If `top_k` is less than or equal to 0.
        """
        k = top_k if top_k is not None else self.top_k
        thresh = threshold if threshold is not None else self.threshold

        if k <= 0:
            raise ValueError(f"top_k must be a positive integer, got {k}.")

        if not query.strip():
            return self.tools[:k]

        results = self.backend.search(query, k, thresh)
        return [tool for tool, _ in results]

    @manual_timeout
    def get_tools(self) -> List[FunctionTool]:
        r"""Return no runtime meta-tools.

        Pass the result of ``filter_tools()`` to an agent for static selection.
        """
        return []
