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

import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from camel.embeddings import BaseEmbedding

logger = get_logger(__name__)

# A toolkit instance, a single tool, or a plain callable.
ToolSource = Union[BaseToolkit, FunctionTool, Callable]

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class ToolkitManager:
    r"""Aggregates tools from multiple toolkits and searches for the ones most
    relevant to a query.

    A capable agent may have access to many toolkits, which together expose
    hundreds of tools. Passing all of them to a language model bloats the
    context window and degrades tool-selection accuracy. ``ToolkitManager``
    indexes the name, description, and parameters of every registered tool and
    retrieves only the most relevant ones for a query -- the "tool RAG"
    pattern.

    Two usage patterns are supported:

    1. **Static pre-filtering** -- call :meth:`search_tools` to obtain the
       top-k relevant tools and pass them straight to a ``ChatAgent``::

           manager = ToolkitManager([SearchToolkit(), MathToolkit()])
           tools = manager.search_tools("add two numbers")
           agent = ChatAgent(tools=tools)

    2. **Agentic discovery** -- expose the meta-tools returned by
       :meth:`get_search_tools` so the agent can search the registry and
       invoke a discovered tool on demand, without ever seeing the full tool
       list::

           agent = ChatAgent(tools=manager.get_search_tools())

    Args:
        toolkits (Optional[Sequence[ToolSource]]): Initial toolkits, tools, or
            plain callables to register. (default: :obj:`None`)
        search_backend (Literal["bm25", "embedding"]): The ranking backend.
            ``"bm25"`` is keyword based and requires no API key.
            ``"embedding"`` ranks by semantic similarity and requires an
            embedding model. (default: :obj:`"bm25"`)
        embedding_model (Optional[BaseEmbedding]): The embedding model used
            when ``search_backend="embedding"``. Falls back to
            :obj:`OpenAIEmbedding` when not provided. (default: :obj:`None`)
        default_top_k (int): The default number of tools returned by
            :meth:`search_tools`. (default: :obj:`5`)
    """

    def __init__(
        self,
        toolkits: Optional[Sequence[ToolSource]] = None,
        *,
        search_backend: Literal["bm25", "embedding"] = "bm25",
        embedding_model: Optional["BaseEmbedding"] = None,
        default_top_k: int = 5,
    ) -> None:
        if search_backend not in ("bm25", "embedding"):
            raise ValueError(
                f"Unknown search_backend '{search_backend}'. "
                f"Expected 'bm25' or 'embedding'."
            )
        if default_top_k <= 0:
            raise ValueError("default_top_k must be a positive integer.")

        self.search_backend = search_backend
        self.default_top_k = default_top_k
        self._embedding_model = embedding_model

        # Registered tools keyed by name (insertion order preserved).
        self._tools: Dict[str, FunctionTool] = {}

        # Lazily built search index. ``_dirty`` is set whenever the set of
        # registered tools changes so the index is rebuilt on next query.
        self._dirty: bool = True
        self._indexed_names: List[str] = []
        self._bm25: Any = None
        self._tool_embeddings: Any = None  # numpy.ndarray of unit vectors

        if toolkits:
            self.add(toolkits)

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def add(
        self, source: Union[ToolSource, Sequence[ToolSource]]
    ) -> "ToolkitManager":
        r"""Registers one or more toolkits, tools, or callables.

        Args:
            source (Union[ToolSource, Sequence[ToolSource]]): A single
                toolkit/tool/callable, or a sequence of them. Each
                :obj:`BaseToolkit` is expanded into its individual tools.

        Returns:
            ToolkitManager: ``self``, to allow chaining.
        """
        # Normalize a single item into a one-element list. ``FunctionTool`` is
        # callable, so it is checked before the generic ``callable`` case.
        if isinstance(source, (BaseToolkit, FunctionTool)) or callable(source):
            items: Sequence[ToolSource] = [source]  # type: ignore[list-item]
        else:
            items = source

        for item in items:
            if isinstance(item, BaseToolkit):
                for tool in item.get_tools():
                    self._register(tool)
            elif isinstance(item, FunctionTool):
                self._register(item)
            elif callable(item):
                self._register(FunctionTool(item))
            else:
                raise TypeError(
                    f"Cannot register object of type {type(item)!r}. "
                    f"Expected a BaseToolkit, FunctionTool, or callable."
                )
        return self

    def _register(self, tool: FunctionTool) -> None:
        r"""Registers a single tool, de-duplicating by function name."""
        name = tool.get_function_name()
        if name in self._tools:
            logger.warning(
                f"Tool '{name}' is already registered; overwriting the "
                f"previous entry."
            )
        self._tools[name] = tool
        self._dirty = True

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    def get_all_tools(self) -> List[FunctionTool]:
        r"""Returns every registered tool.

        Returns:
            List[FunctionTool]: All registered tools, in registration order.
        """
        return list(self._tools.values())

    @property
    def tool_names(self) -> List[str]:
        r"""The names of all registered tools."""
        return list(self._tools.keys())

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    @overload
    def search_tools(
        self,
        query: str,
        top_k: Optional[int] = ...,
        *,
        with_scores: Literal[False] = ...,
    ) -> List[FunctionTool]: ...

    @overload
    def search_tools(
        self,
        query: str,
        top_k: Optional[int] = ...,
        *,
        with_scores: Literal[True],
    ) -> List[Tuple[FunctionTool, float]]: ...

    def search_tools(
        self,
        query: str,
        top_k: Optional[int] = None,
        *,
        with_scores: bool = False,
    ) -> Union[List[FunctionTool], List[Tuple[FunctionTool, float]]]:
        r"""Returns the tools most relevant to ``query``, best match first.

        Args:
            query (str): A natural language description of the desired
                capability (e.g. "download a paper from arxiv").
            top_k (Optional[int]): The maximum number of tools to return.
                Falls back to ``default_top_k`` when ``None``.
                (default: :obj:`None`)
            with_scores (bool): When ``True``, return ``(tool, score)`` tuples
                instead of bare tools. (default: :obj:`False`)

        Returns:
            Union[List[FunctionTool], List[Tuple[FunctionTool, float]]]: The
                ranked tools, optionally paired with their relevance scores.

        Raises:
            ValueError: If ``query`` is empty or ``top_k`` is not positive.
        """
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string.")
        top_k = self.default_top_k if top_k is None else top_k
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        if not self._tools:
            return []

        ranked = self._rank(query)[:top_k]
        if with_scores:
            return [(self._tools[name], score) for name, score in ranked]
        return [self._tools[name] for name, _ in ranked]

    def _rank(self, query: str) -> List[Tuple[str, float]]:
        r"""Ranks all tool names against ``query`` (descending score).

        Ties are broken by tool name so results are deterministic.
        """
        self._ensure_index()
        if self.search_backend == "bm25":
            scores = self._bm25_scores(query)
        else:
            scores = self._embedding_scores(query)
        paired = list(zip(self._indexed_names, scores))
        paired.sort(key=lambda item: (-item[1], item[0]))
        return paired

    def _ensure_index(self) -> None:
        r"""(Re)builds the search index if the tool set changed."""
        if not self._dirty:
            return
        self._indexed_names = list(self._tools.keys())
        if self.search_backend == "bm25":
            self._build_bm25_index()
        else:
            self._build_embedding_index()
        self._dirty = False

    # ------------------------------------------------------------------ #
    # BM25 backend
    # ------------------------------------------------------------------ #
    @dependencies_required('rank_bm25')
    def _build_bm25_index(self) -> None:
        from rank_bm25 import BM25Okapi

        corpus = [
            self._tokenize(self._tool_document(self._tools[name]))
            for name in self._indexed_names
        ]
        # ``BM25Okapi`` cannot be built from an empty corpus.
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def _bm25_scores(self, query: str) -> List[float]:
        if self._bm25 is None:
            return [0.0] * len(self._indexed_names)
        return [float(s) for s in self._bm25.get_scores(self._tokenize(query))]

    # ------------------------------------------------------------------ #
    # Embedding backend
    # ------------------------------------------------------------------ #
    def _get_embedding_model(self) -> "BaseEmbedding":
        if self._embedding_model is None:
            from camel.embeddings import OpenAIEmbedding

            self._embedding_model = OpenAIEmbedding()
        return self._embedding_model

    def _build_embedding_index(self) -> None:
        import numpy as np

        if not self._indexed_names:
            self._tool_embeddings = None
            return
        documents = [
            self._tool_document(self._tools[name])
            for name in self._indexed_names
        ]
        vectors = np.asarray(
            self._get_embedding_model().embed_list(documents), dtype=float
        )
        self._tool_embeddings = self._normalize_rows(vectors)

    def _embedding_scores(self, query: str) -> List[float]:
        import numpy as np

        if self._tool_embeddings is None:
            return [0.0] * len(self._indexed_names)
        query_vector = np.asarray(
            self._get_embedding_model().embed(query), dtype=float
        )
        query_vector = self._normalize_rows(query_vector[np.newaxis, :])[0]
        # Cosine similarity reduces to a dot product of unit vectors.
        return [float(s) for s in self._tool_embeddings @ query_vector]

    @staticmethod
    def _normalize_rows(matrix: Any) -> Any:
        import numpy as np

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    # ------------------------------------------------------------------ #
    # Agentic meta-tools
    # ------------------------------------------------------------------ #
    def get_search_tools(self) -> List[FunctionTool]:
        r"""Returns meta-tools that let an agent search and call tools at
        runtime.

        Exposing these two tools -- ``search_tools`` and ``execute_tool`` --
        instead of the full tool list keeps the agent's context small while
        still granting access to every registered tool on demand.

        Returns:
            List[FunctionTool]: The ``search_tools`` and ``execute_tool``
                meta-tools, bound to this manager.
        """
        manager = self

        def search_tools(query: str, top_k: int = 5) -> str:
            r"""Search the tool registry for tools relevant to a query.

            Call this to discover which tools are available before invoking
            ``execute_tool``.

            Args:
                query (str): A natural language description of what you want
                    to do, e.g. "download a paper from arxiv".
                top_k (int): The maximum number of tools to return.
                    (default: :obj:`5`)

            Returns:
                str: The matching tool names with their descriptions and
                    parameters, or a message stating that nothing matched.
            """
            try:
                results = manager.search_tools(
                    query, top_k=top_k, with_scores=True
                )
            except ValueError as error:
                return f"Error: {error}"
            if not results:
                return "No matching tools were found."
            return "\n\n".join(
                manager._describe_tool(tool) for tool, _ in results
            )

        def execute_tool(
            tool_name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> str:
            r"""Execute a registered tool by name.

            Use ``search_tools`` first to find the exact tool name and its
            parameters.

            Args:
                tool_name (str): The exact name of the tool to execute, as
                    returned by ``search_tools``.
                arguments (Optional[Dict[str, Any]]): A mapping of parameter
                    names to values passed to the tool. (default: :obj:`None`)

            Returns:
                str: The tool's result, or an error message if the tool is
                    unknown or raised an exception.
            """
            return manager._execute_named_tool(tool_name, arguments)

        return [FunctionTool(search_tools), FunctionTool(execute_tool)]

    def _execute_named_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> str:
        r"""Dispatches a call to a registered tool by name (error-safe)."""
        tool = self._tools.get(tool_name)
        if tool is None:
            hint = ""
            try:
                suggestions = self.search_tools(tool_name, top_k=3)
            except ValueError:
                suggestions = []
            names = ", ".join(tool.get_function_name() for tool in suggestions)
            if names:
                hint = f" Did you mean: {names}?"
            return (
                f"Error: no tool named '{tool_name}'.{hint} "
                f"Use search_tools to discover available tools."
            )
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return (
                "Error: 'arguments' must be a mapping of parameter names to "
                "values."
            )
        try:
            return str(tool(**arguments))
        except Exception as error:
            return f"Error executing '{tool_name}': {error}"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _tool_document(self, tool: FunctionTool) -> str:
        r"""Builds the searchable text for a tool from its name, description,
        and parameter names/descriptions."""
        name = tool.get_function_name()
        description = tool.get_function_description() or ""
        parts = [name, description]
        try:
            properties = (
                tool.get_openai_tool_schema()["function"]
                .get("parameters", {})
                .get("properties", {})
            )
            for param_name, param_info in properties.items():
                parts.append(param_name)
                param_desc = param_info.get("description")
                if param_desc:
                    parts.append(param_desc)
        except Exception:
            # A malformed schema should not break indexing.
            pass
        return " ".join(part for part in parts if part)

    def _describe_tool(self, tool: FunctionTool) -> str:
        r"""Renders a human/LLM-readable description of a tool and its
        parameters."""
        name = tool.get_function_name()
        description = tool.get_function_description() or ""
        try:
            parameters = tool.get_openai_tool_schema()["function"].get(
                "parameters", {}
            )
        except Exception:
            parameters = {}
        properties = parameters.get("properties", {})
        required = set(parameters.get("required", []))

        if not properties:
            params_text = " none"
        else:
            lines = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                requirement = (
                    "required" if param_name in required else "optional"
                )
                param_desc = param_info.get("description", "")
                lines.append(
                    f"    - {param_name} ({param_type}, {requirement}): "
                    f"{param_desc}".rstrip()
                )
            params_text = "\n" + "\n".join(lines)
        return f"{name}: {description}\n  parameters:{params_text}"

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        r"""Lowercases and splits text into alphanumeric tokens, also breaking
        ``camelCase`` boundaries so e.g. ``downloadPapers`` matches
        ``download``."""
        spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
        return [match.lower() for match in _TOKEN_RE.findall(spaced)]

    # ------------------------------------------------------------------ #
    # Dunder helpers
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_name: object) -> bool:
        return tool_name in self._tools

    def __repr__(self) -> str:
        return (
            f"ToolkitManager(num_tools={len(self._tools)}, "
            f"search_backend='{self.search_backend}')"
        )
