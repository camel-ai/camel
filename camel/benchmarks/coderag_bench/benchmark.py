# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import inspect
import json
import logging
import os
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Union,
)

import datasets
from datasets import Dataset
from tqdm import tqdm
from unstructured.documents.elements import Element, Title

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.benchmarks.coderag_bench.code_generation_evaluation import (
    compute_code_eval,
)
from camel.embeddings import OpenAIEmbedding
from camel.retrievers.auto_retriever import AutoRetriever
from camel.retrievers.vector_retriever import VectorRetriever
from camel.types import StorageType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

EXAMPLE_PATCH_SWE_Bench = """
I need you to solve this issue by generating a single patch file that I can
apply directly to this repository using git apply. Please respond with a
single patch file in the following format.
<patch>
--- a/file.py
+++ b/file.py
@@ -1,27 +1,35 @@
 def euclidean(a, b):
-    while b:
-        a, b = b, a % b
-    return a
+    if b == 0:
+        return a
+    return euclidean(b, a % b)


 def bresenham(x0, y0, x1, y1):
     points = []
     dx = abs(x1 - x0)
     dy = abs(y1 - y0)
-    sx = 1 if x0 < x1 else -1
-    sy = 1 if y0 < y1 else -1
-    err = dx - dy
+    x, y = x0, y0
+    sx = -1 if x0 > x1 else 1
+    sy = -1 if y0 > y1 else 1

-    while True:
-        points.append((x0, y0))
-        if x0 == x1 and y0 == y1:
-            break
-        e2 = 2 * err
-        if e2 > -dy:
+    if dx > dy:
+        err = dx / 2.0
+        while x != x1:
+            points.append((x, y))
             err -= dy
-            x0 += sx
-        if e2 < dx:
-            err += dx
-            y0 += sy
+            if err < 0:
+                y += sy
+                err += dx
+            x += sx
+    else:
+        err = dy / 2.0
+        while y != y1:
+            points.append((x, y))
+            err -= dx
+            if err < 0:
+                x += sx
+                err += dy
+            y += sy

+    points.append((x, y))
     return points
</patch>
"""


class RetrieverFn(Protocol):
    r"""Protocol for a retrieval function used in benchmark evaluation.

    This function takes a user query and a list of `Element` documents, and
        returns
    a dictionary containing retrieved results.

    Required arguments:
        - query (str): The input query string.
        - contents (List[Element]): A list of unstructured elements to
            retrieve from.

    Optional keyword arguments that may be supported:
        - top_k (int): Number of results to retrieve. (default: :obj:`5`)
        - collection_name (str): Optional identifier for
            grouping indexed elements.
        - similarity_threshold (float): Minimum similarity score
            to retain results.
        - return_detailed_info (bool): If True, return full metadata
            instead of plain text.

    Returns:
        dict: A dictionary with keys like "Original Query" and
            "Retrieved Context".
    """

    def __call__(
        self,
        query: str,
        contents: Union[Element, List[Element]],
        top_k: int = 5,
        **kwargs,
    ) -> Dict: ...


def safe_call(func: Callable[..., Any], **kwargs) -> Any:
    r"""Call a function with only the parameters it declares.

    This avoids TypeError when the function doesn't accept some
    of the keyword arguments provided.

    Args:
        func (Callable): The function to call.
        **kwargs: Keyword arguments to be passed to the function.

    Returns:
        The return value of the function.
    """

    sig = inspect.signature(func)
    accepted_params = set(sig.parameters.keys())

    # If function supports **kwargs, pass everything
    if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
        return func(**kwargs)

    # Otherwise filter out unsupported keys
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in accepted_params}
    return func(**filtered_kwargs)


class CodeRAGBenchAutoRetriever(AutoRetriever):
    r"""Customized AutoRetriever for CodeRAG-Bench.

    Supports vector retrieval over a list of `Element` documents
    with preserved metadata. Assumes each `Element` is already a
    semantically complete unit (e.g., one code function), and sets
    `should_chunk=False` during ingestion.

    Compatible with `run_vector_retriever` interface used by other
    CAMEL-AI retrievers. Returns plain text or metadata depending
    on `return_detailed_info`.

    Args:
        storage_type (Optional[StorageType]): Type of vector store.
            (default: :obj:`None`)
        embedding_model (Optional[OpenAIEmbedding]): Embedding model
            for indexing and querying. (default: :obj:`None`)
        vector_storage_local_path (Optional[str]): Local storage path.
            (default: :obj:`None`)
        url_and_api_key (Optional[tuple]): Remote URL and API key.
            (default: :obj:`None`)
        overwrite (bool): Whether to re-index and overwrite existing
            collection. (default: :obj:`False`)
    """

    def __init__(
        self,
        storage_type: Optional[StorageType] = None,
        embedding_model: Optional[OpenAIEmbedding] = None,
        vector_storage_local_path: Optional[str] = None,
        url_and_api_key: Optional[tuple] = None,
        overwrite: bool = False,
    ):
        r"""Initializes the retriever with optional vector store config and
        embedding model.

        Args:
            storage_type (Optional[StorageType]): Type of storage to use.
                (default: :obj:`None`)
            embedding_model (Optional[OpenAIEmbedding]): Embedding model
                to use for indexing and querying. (default: :obj:`None`)
            vector_storage_local_path (Optional[str]): Path to local
                vector DB, if applicable. (default: :obj:`None`)
            url_and_api_key (Optional[tuple]): Remote DB config, if any.
                (default: :obj:`None`)
            overwrite (bool): Whether to re-index and overwrite existing
                collection. (default: :obj:`False`)
        """
        super().__init__(
            storage_type=storage_type,
            embedding_model=embedding_model,
            vector_storage_local_path=vector_storage_local_path,
            url_and_api_key=url_and_api_key,
        )
        self.overwrite = overwrite

    def run_vector_retriever(  # type: ignore[override]
        self,
        query: str,
        contents: Union[Element, List[Element]],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        return_detailed_info: bool = False,
        max_characters: int = 500,
        collection_name: Optional[str] = None,
        **kwargs,
    ) -> dict:
        r"""Runs document-level retrieval on unstructured Elements.

        Supports optional collection name override. If not provided,
        a name will be auto-generated from the first Element.

        Args:
            query (str): The input query string.
            contents (Union[Element, List[Element]]): One or more
                `Element` documents to ingest and retrieve over.
            top_k (int): Number of top results to return.
                (default: :obj:`5`)
            similarity_threshold (float): Minimum similarity score to
                retain results. (default: :obj:`0.7`)
            return_detailed_info (bool): If True, returns full metadata;
                otherwise, returns plain text. (default: :obj:`False`)
            max_characters (int): Max characters per document for
                embedding. (default: :obj:`500`)
            collection_name (Optional[str]): Custom name for the vector
                collection. If None, a name is auto-generated.
                (default: :obj:`None`)
            **kwargs: Extra keyword arguments for compatibility.

        Returns:
            dict: {
                "Original Query": query,
                "Retrieved Context": list of plain texts or detailed
                metadata entries
            }
        """
        if isinstance(contents, Element):
            elements = [contents]
        elif isinstance(contents, list) and all(
            isinstance(e, Element) for e in contents
        ):
            elements = contents
        else:
            raise ValueError(
                "contents must be an Element or a list of Elements"
            )

        if not elements:
            raise ValueError("No elements provided for retrieval.")

        # Generate or use the provided collection name
        collection_name = collection_name or self._collection_name_generator(
            elements[0]
        )

        vector_storage_instance = self._initialize_vector_storage(
            collection_name
        )

        vr = VectorRetriever(
            storage=vector_storage_instance,
            embedding_model=self.embedding_model,
        )

        vector_count = vector_storage_instance.status().vector_count

        if self.overwrite and vector_count > 0:
            logger.debug(
                f"Overwriting collection '{collection_name}' with "
                f"{len(elements)} documents..."
            )
            vector_storage_instance.clear()
            vector_count = 0

        if vector_count == 0:
            logger.debug(
                f"Ingesting {len(elements)} documents into vector store "
                f"'{collection_name}'"
            )
            for elem in elements:
                vr.process(
                    content=elem,
                    max_characters=max_characters,
                    should_chunk=False,
                    extra_info=getattr(elem.metadata, "extra_info", {}),
                )
            logger.debug(
                f"Vector store now contains "
                f"{vector_storage_instance.status().vector_count} documents"
            )
        else:
            logger.debug(
                f"Vector store '{collection_name}' "
                f"already contains {vector_count} vectors. Skipping ingestion."
            )

        retrieved_info = vr.query(
            query, top_k=top_k, similarity_threshold=similarity_threshold
        )

        # Sort results by similarity score in descending order
        with_score = [
            info for info in retrieved_info if "similarity score" in info
        ]
        without_score = [
            info for info in retrieved_info if "similarity score" not in info
        ]
        with_score_sorted = sorted(
            with_score, key=lambda x: x["similarity score"], reverse=True
        )
        sorted_info = with_score_sorted + without_score
        sorted_info = sorted_info[:top_k]

        if return_detailed_info:
            return {"Original Query": query, "Retrieved Context": sorted_info}
        else:
            return {
                "Original Query": query,
                "Retrieved Context": [item["text"] for item in sorted_info],
            }


def document2code(data, split="test"):
    r"""Converts document samples into IR code generation pairs.

    Adapted from CodeRAG-Bench:
        https://github.com/code-rag-bench/code-rag-bench/blob/
        main/retrieval/create/humaneval.py

    Constructs a flat list of query-document pairs and relevance
    judgments from a code generation dataset. Each sample includes a
    "prompt" and its corresponding "canonical_solution". The prompt is
    used as the query, and prompt + solution is treated as the target
    code document.

    Note:
        This function is preserved unmodified for compatibility with
        original CodeRAG-Bench logic. To convert the result into
        BEIR-style format, use `wrap_as_beir_loader`.

    Args:
        data (dict): Dataset split dictionary, e.g., {"test": [...]}.
        split (str): Dataset split to process.
            (default: :obj:`"test"`)

    Returns:
        Tuple[List[dict], List[dict], List[dict]]:
            - queries: List of dicts with "_id" and "text".
            - docs: List of dicts with "_id", "text", and "title".
            - qrels: List of dicts linking queries to relevant docs.
    """

    data = data[split]
    queries, docs, qrels = [], [], []

    for item in tqdm(data):
        doc = item["prompt"]
        code = item["prompt"] + '\n' + item["canonical_solution"]
        doc_id = "{task_id}_doc".format_map(item)
        code_id = "{task_id}_code".format_map(item)

        queries.append({"_id": doc_id, "text": doc, "metadata": {}})
        docs.append(
            {
                "_id": code_id,
                "title": item["entry_point"],
                "text": code,
                "metadata": {},
            }
        )
        qrels.append({"query-id": doc_id, "corpus-id": code_id, "score": 1})

    return queries, docs, qrels


def wrap_as_beir_loader(queries_list, corpus_list, qrels_list):
    r"""Wraps the output of `document2code()` into BEIR-compatible
        dictionary format.

    This function converts flat lists of queries, documents, and qrels into
        dictionaries keyed by ID, as expected by BEIR's evaluation tools.

    It is intended to be used directly after `document2code()` to
        prepare the dataset
    for retrieval benchmarking.

    Args:
        queries_list (List[dict]): List of queries with "_id" and "text"
            fields.
        corpus_list (List[dict]): List of documents with "_id", "text",
            and metadata.
        qrels_list (List[dict]): List of relevance annotations with "query-id",
                                 "corpus-id", and optional "score".

    Returns:
        Tuple[Dict[str, dict], Dict[str, dict], Dict[str, Dict[str, int]]]:
            - queries: Dict mapping query ID to query text.
            - corpus: Dict mapping document ID to document content.
            - qrels: Nested dict mapping query ID to a dict of {doc ID: score}.
    """

    queries = {q["_id"]: q for q in queries_list}
    corpus = {d["_id"]: d for d in corpus_list}
    qrels = {}

    for entry in qrels_list:
        qid = entry["query-id"]
        did = entry["corpus-id"]
        score = entry.get("score", 1)
        if qid not in qrels:
            qrels[qid] = {}
        qrels[qid][did] = score

    return queries, corpus, qrels


def extract_code_pieces(
    text: str, prefix: str = "```python", return_all: bool = False
) -> str:
    r"""Extracts Python code blocks from Markdown-style strings.

    Scans input text and extracts code blocks that start with the
    given prefix (e.g., "```python") and end with a triple backtick
    ("```"). Useful for parsing model-generated code formatted using
    Markdown.

    Args:
        text (str): Input string possibly containing code blocks.
        prefix (str): Markdown code prefix to search for.
            (default: :obj:`"```python"`)
        return_all (bool): If True, returns all code blocks joined by
            double newlines. If False, returns only the first match.
            (default: :obj:`False`)

    Returns:
        str: Extracted code block(s). If none found, returns empty
            string.

    Note:
        Adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/
        generation/eval/utils.py

    Example:
        >>> text = "Here is the function:\n```python\ndef add(a, b):\n"
        >>>        "    return a + b\n```"
        >>> extract_code_pieces(text)
        'def add(a, b):\n    return a + b'
    """

    code_pieces = []
    while prefix in text:
        st_idx = text.index(prefix) + 10
        # end_idx = text.index("```", st_idx)
        if "```" in text[st_idx:]:
            end_idx = text.index("```", st_idx)
        else:
            end_idx = len(text)
        code_pieces.append(text[st_idx:end_idx].strip())
        text = text[end_idx + 3 :].strip()
    if return_all:
        return '\n\n'.join(code_pieces)
    return code_pieces[0]


def get_function_name(question: str, lang: str):
    r"""
    Extracts the function name and the prefix (preceding
    lines) from a code prompt.

    This is useful for evaluation purposes where the
    generated function needs to be compared or executed
    with a known entry point name. The logic assumes a
    simple structure where either the last Python
    function is the target, or in non-Python languages,
    the function appears at the end enclosed in curly
    braces.

    Args:
        question (str): The full code prompt or question
            containing the function definition.
        lang (str): The programming language (e.g.,
            "python", "java").

    Returns:
        Tuple[str, str]: A tuple of (function_name,
            function_prefix), where function_prefix is the
            code before the function definition.

    Notes:
        This function is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/
        main/generation/eval/utils.py
    """
    func_lines = [x for x in question.strip().split('\n') if x.strip()]

    if lang.lower() == 'python':
        func_idx = [
            i
            for i in range(len(func_lines))
            if func_lines[i].startswith("def ")
        ][-1]
        func_name = func_lines[func_idx].split('(')[0].strip()
        func_prefix = "\n".join(func_lines[:func_idx])
        return func_name, func_prefix

    func_name = func_lines[-1].split('{')[0].strip()
    func_prefix = "\n".join(func_lines[:-1])
    return func_name, func_prefix


def indent_code_block(code: str, indent: int = 4) -> str:
    r"""Indents each non-empty line in a code block.

    Typically used to ensure that generated code fits correctly
    within a function body, control structure, or nested context.

    Args:
        code (str): Input code block as a single string.
        indent (int): Number of spaces to add at the beginning of
            each non-empty line. (default: :obj:`4`)

    Returns:
        str: Indented code block as a single string.
    """
    return "\n".join(
        " " * indent + line if line.strip() else ""
        for line in code.splitlines()
    )


def extract_generation_code(output: str, question: str) -> str:
    r"""Reconstructs function code from model output and prompt.

    Extracts the first Python code block from model output and
    reattaches the original function header from the prompt to
    ensure proper execution (e.g., for pass@k evaluation).

    Combines Markdown-style block parsing with prompt-based header
    recovery to ensure correctness of generated code.

    Note:
        Adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/
        generation/eval/utils.py

    Args:
        output (str): Model output containing a code snippet.
        question (str): Prompt containing the expected function
            signature.

    Returns:
        str: Reconstructed full function code. Returns raw output if
            extraction fails.
    """

    try:
        # Extract the content within ```python ... ``` block
        code_block = re.findall(
            r"```(?:python)?\s*\n(.*?)```", output, re.DOTALL | re.IGNORECASE
        )[0]

        # Get the original function header from the prompt
        func_lines = [
            line for line in question.strip().split('\n') if line.strip()
        ]
        def_idx = [
            i
            for i, line in enumerate(func_lines)
            if line.strip().startswith("def ")
        ][-1]
        func_header = func_lines[def_idx]
        imports = "\n".join(
            func_lines[:def_idx]
        )  # All lines above the def line

        # Combine everything together with proper indentation
        full_code = f"{imports}\n\n{func_header}\n" + indent_code_block(
            code_block
        )
        return full_code

    except Exception as ex:
        print(f"Failed to extract code block: {ex}")
        return output.strip()  # Fallback to raw output


def stop_at_stop_token(decoded_string, stop_tokens):
    r"""Produces the prefix of the decoded string that ends
    at the first occurrence of any stop token.

    This function searches for the earliest appearance of
    any provided stop token in the decoded string and
    truncates the string at that point.

    Warning:
        The `decoded_string` must not include the prompt
        itself, as the prompt may contain stop tokens that
        should be ignored.

    Note:
        This implementation is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/
        blob/main/generation/eval/tasks/humaneval.py

    Args:
        decoded_string (str): The generated text output to
            be processed.
        stop_tokens (list[str]): A list of stop tokens to
            search for in the decoded text.

    Returns:
        str: The truncated decoded string ending before the
            first occurrence of a stop token.
    """
    min_stop_index = len(decoded_string)
    for stop_token in stop_tokens:
        stop_index = decoded_string.find(stop_token)
        if stop_index != -1 and stop_index < min_stop_index:
            min_stop_index = stop_index
    return decoded_string[:min_stop_index]


def get_top_docs(
    results: dict, corpus: dict, task_id: str, topk: int = 10
) -> list[str]:
    r"""Retrieves top-ranked documents by similarity score.

    Sorts documents for a given task ID by similarity score in
    descending order and returns the corresponding code snippets
    from the corpus.

    If the task ID is not found in the results, returns an empty
    list.

    Note:
        Adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/
        retrieval/eval_beir_sbert_canonical.py

    Args:
        results (dict): Mapping from task IDs to document-score
            dictionaries.
        corpus (dict): Mapping from document IDs to code content.
        task_id (str): Task ID to retrieve top documents for.
        topk (int): Number of top documents to return.
            (default: :obj:`10`)

    Returns:
        list[str]: Top code snippets or documents for the task ID.
    """
    if task_id not in results:
        return []
    doc_scores = results[task_id]
    doc_scores_sorted = sorted(
        doc_scores.items(), key=lambda item: item[1], reverse=True
    )
    doc_scores_sorted = doc_scores_sorted[:topk]
    doc_code_snippets = [
        corpus[code_id] for code_id, score in doc_scores_sorted
    ]
    return doc_code_snippets


class CodeRAGBenchmark(BaseBenchmark):
    r"""Benchmark for evaluating CodeRAG-Bench performance.

    Evaluates retrieval-augmented generation (RAG) on multiple
    programming datasets.

    Supports:
    - Canonical retrieval evaluation
    - Code generation from retrieved context
    - End-to-end retrieval + generation evaluation
    - Pass@k code evaluation (with optional execution)

    Currently, only the "humaneval" task and canonical retrieval
    are supported.

    Attributes:
        task (str): Target evaluation dataset name.
        run_mode (str): Execution mode ("retrieve", "generate", or
            "retrieve_generate").
        retrieval_type (str): Retrieval type ("canonical" or "open").
        subset_size (Optional[int]): Optional limit on number of
            examples for faster benchmarking.
        dataset (Optional[Dataset]): Loaded HuggingFace dataset.
    """

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        task: Literal[
            "humaneval",
            "mbpp",
            "live_code_bench",
            "ds1000",
            "odex",
            "repoeval_repo",
            "swebench_repo",
        ] = "humaneval",
        run_mode: Literal[
            "retrieve", "generate", "retrieve_generate"
        ] = "retrieve_generate",
        retrieval_type: Literal['canonical', 'open'] = "canonical",
        subset_size: Optional[int] = None,
    ) -> None:
        r"""Initializes the CodeRAGBenchmark configuration.

        Args:
            data_dir (str): Path to the data directory.
            save_to (str): Path to save results and outputs.
            task (str): Evaluation task name.
                (default: :obj:`"humaneval"`)
            run_mode (str): Execution mode: "retrieve",
                "generate", or "retrieve_generate".
                (default: :obj:`"retrieve_generate"`)
            retrieval_type (str): Retrieval type: "canonical" or
                "open". (default: :obj:`"canonical"`)
            subset_size (Optional[int]): Optional subset size for
                limiting evaluation. (default: :obj:`None`)
        """
        super().__init__("coderag_bench", data_dir, save_to)
        self.task = task
        self.retrieval_type = retrieval_type
        self.run_mode = run_mode
        self.dataset: Optional[Dataset] = None
        self.subset_size = subset_size

        # Todo: Support other 6 tasks, e.g., mbpp, ds100,...
        if self.task not in ["humaneval", "swe-bench_lite"]:
            raise NotImplementedError(
                "Only canonical retrieval is supported for now."
            )

    def download(self):
        r"""Downloads and preprocesses CodeRAG-Bench dataset.

        Currently only supports downloading and preparing the
        "humaneval" dataset.

        Returns:
            None
        """
        if self.task in ["humaneval", "swe-bench_lite"]:
            logger.info(
                f"Downloading and processing dataset for task: {self.task}"
            )
            dataset_name_map = {
                "humaneval": "openai_humaneval",
                "swe-bench_lite": "princeton-nlp/SWE-bench_Lite",
            }
            dataset = datasets.load_dataset(
                dataset_name_map[self.task], cache_dir=self.data_dir
            )
            self.dataset = dataset

        else:
            raise NotImplementedError(
                f"Download() not implemented for task: {self.task}"
            )
            pass

    def load(self, force_download: bool = False):
        r"""Loads the dataset into memory.

        Downloads the dataset if not already available or if
        `force_download` is set to True.

        Args:
            force_download (bool, optional): Whether to force
                re-downloading the dataset. (default: :obj:`False`)

        Returns:
            None
        """
        if force_download or self.dataset is None:
            logger.info(
                "%s dataset",
                "Force downloading" if force_download else "Loading",
            )
            self.download()

    def run_retrieval(self, retrieve_fn, retrieval_top_k):
        r"""Run top-k document retrieval and compute retrieval
        metrics.

        Args:
            retrieve_fn (Callable): A callable retrieval
                function that takes `query`, `contents`,
                `top_k`, and optionally other keyword
                arguments.
            retrieval_top_k (int): Number of top documents
                to retrieve per query.

        Returns:
            dict: A dictionary containing retrieval
                evaluation metrics.
        """

        queries_list, docs_list, qrels_list = document2code(self.dataset)

        # Format corpus, queries, and qrels in BEIR style
        # corpus: Corpus used for retrieval.
        # queries: Queries used for retrieval evaluation.
        # qrels: Relevance labels for retrieval evaluation.
        queries, corpus, qrels = wrap_as_beir_loader(
            queries_list, docs_list, qrels_list
        )

        # Todo: Support Open retrieval
        if self.retrieval_type != "canonical":
            raise NotImplementedError(
                "Only canonical retrieval is supported for now."
            )

        if retrieve_fn is None or not callable(retrieve_fn):
            raise ValueError(
                "A callable `retrieve_fn` must be provided in "
                "`retrieve` or `retrieve_generate` mode."
            )

        # === Canonical Retrieval Logic ===
        logger.info("Starting canonical retrieval...")

        # Convert the corpus into a list of Element objects
        #   (one per document),
        # and assign a consistent file_directory to group them into
        #   a single vector collection.
        elements = []
        collection_name = f"{self.task}_collection"
        for doc_id, doc in corpus.items():
            element = Title(text=doc["text"])
            element.metadata.file_directory = collection_name
            element.metadata.extra_info = {"doc_id": doc_id}
            elements.append(element)

        # Logging debug information
        for idx, elem in enumerate(elements):
            logger.debug("Element #%d", idx)
            logger.debug("Text preview: %s", elem.text[:80].replace('\n', ' '))
            logger.debug("file_directory: %s", elem.metadata.file_directory)
            logger.debug("other: %s", getattr(elem.metadata, "other", {}))
            logger.debug("-" * 50)

        retrieval_results = {}

        # Prepare output directory
        output_dir = os.path.join(self.save_to, "retrieval")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"{self.task}_retrieved_docs.jsonl"
        )
        metrics_path = os.path.join(
            output_dir, f"{self.task}_retrieval_metrics.json"
        )
        import jsonlines

        with jsonlines.open(output_path, mode='w') as writer:
            for example in tqdm(self.dataset["test"]):
                query_text = example["prompt"]
                query_id = (
                    example["task_id"] + "_doc"
                )  # make sure the format is the same as qrel,
                #   for evaluation purposes

                # Prepare optional keyword arguments for retrieval.
                # All elements share the same `file_directory`, so
                # collection_name can be shared safely.
                kwargs = {
                    "collection_name": collection_name,
                    "similarity_threshold": 0.0,
                    "return_detailed_info": True,
                }

                # Only pass arguments that are accepted by retrieve_fn.
                # This makes the interface flexible for lightweight
                # user-defined functions.
                sig = inspect.signature(retrieve_fn)
                accepted_kwargs = {
                    k: v for k, v in kwargs.items() if k in sig.parameters
                }

                # Call the retriever function with required and filtered
                # optional arguments.
                result = retrieve_fn(
                    query=query_text,
                    contents=elements,
                    top_k=retrieval_top_k,
                    **accepted_kwargs,
                )

                # print for debugging
                logger.debug("Query: %s", query_text[:60])
                logger.debug(
                    "Retrieved Context: %s", result['Retrieved Context']
                )

                doc_entries = []
                scores = {}

                for item in result["Retrieved Context"]:
                    doc_text = item["text"]
                    doc_id = item.get("extra_info", {}).get("doc_id")
                    if doc_id is None:
                        continue  # fallback or missing metadata

                    scores[doc_id] = float(item.get("similarity score", 0.0))
                    doc_entries.append(
                        {
                            "doc_id": doc_id,
                            "text": doc_text,
                            "title": corpus[doc_id].get("title", ""),
                            "similarity": float(
                                item.get("similarity score", 0.0)
                            ),
                        }
                    )

                # Save scores for retrieval evaluation
                retrieval_results[query_id] = scores

                # Merge retrieved docs into the original sample
                #   and stream write
                example_with_docs = dict(example)
                example_with_docs["docs"] = doc_entries
                writer.write(example_with_docs)

        self.dataset["test"] = datasets.load_dataset(
            "json", data_files=output_path, split="train"
        )
        # Evaluate using BEIR

        from beir.retrieval.evaluation import (  # type: ignore[import-untyped]
            EvaluateRetrieval,
        )

        retriever = EvaluateRetrieval(score_function="dot")
        k_values = [1, 5, 10]
        logger.debug("qrels keys: %s", list(qrels.keys())[:5])
        logger.debug(
            "retrieval_results keys: %s",
            list(retrieval_results.keys())[:5],
        )

        for qid in qrels:
            relevant_doc_ids = set(qrels[qid].keys())
            retrieved_doc_ids = set(retrieval_results.get(qid, {}).keys())

            if not relevant_doc_ids & retrieved_doc_ids:
                logger.debug(f"[NO MATCH] for query {qid}")
            else:
                logger.debug(f"[MATCH] {qid} retrieved")
            logger.debug(f"  gold:      {relevant_doc_ids}")
            logger.debug(f"  retrieved: {retrieved_doc_ids}")

        ndcg, _map, recall, precision = retriever.evaluate(
            qrels, retrieval_results, k_values, ignore_identical_ids=False
        )
        mrr = retriever.evaluate_custom(
            qrels, retrieval_results, k_values, metric="mrr"
        )

        metrics = {
            "ndcg": ndcg,
            "mrr": mrr,
            "recall": recall,
            "precision": precision,
        }

        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info("Retrieval results saved to %s", output_path)
        logger.info("Retrieval metrics saved to %s", metrics_path)
        logger.info("Canonical retrieval completed.")
        return metrics

    def run_generation(
        self,
        agent,
        n_generation_samples,
        allow_code_execution,
        generation_eval_k,
        split="test",
    ):
        r"""Runs code generation and evaluation for the task.

        This uses retrieved documents to construct prompts
        and optionally runs pass@k evaluation using code
        execution if enabled.

        Args:
            agent (ChatAgent): Chat agent for code generation.
            n_generation_samples (int): Number of completions
                to generate per prompt. (default: :obj:`1`)

            allow_code_execution (bool): Whether to run code for
                pass@k evaluation. Use with caution.
                (default: :obj:`False`)
            generation_eval_k (List[int]): k values used in pass@k
                computation. (default: :obj:`List[int]` with [1, 5, 10])
            split (str): Split for the dataset. (default: :obj:`"test"`)

        Returns:
            Optional[Dict[str, float]]: Dictionary of pass@k
                results if executed; otherwise None.
        """
        generation_dir = os.path.join(self.save_to, "generation", self.task)
        os.makedirs(generation_dir, exist_ok=True)

        gen_path = os.path.join(generation_dir, "generations.json")
        ref_path = os.path.join(generation_dir, "references.json")

        # List[List[str]]: list of candidates per task
        all_generations = []

        # List[str]: one reference string per task
        all_references = []

        for _, doc_i in enumerate(
            tqdm(self.dataset[split])
        ):  # doc_i is equivalent to doc in <https://github.com/
            # code-rag-bench/code-rag-bench/blob/main/generation/
            # eval/tasks/humaneval.py>

            prompt = data_i["prompt"]

            docs = data_i.get("docs", [])
            context = "\n\n".join(doc["text"] for doc in docs)

            # Construct the final prompt for the agent
            final_prompt = (
                context + '\n\nPlease complete the following function based '
                'on the example above, DO NOT REPEAT'
                'PREVIOUS DEFINITIONS :\n' + '```python\n' + prompt
            )


            # ===Generate Prompts======
            if self.task == "humaneval":
                prompt = doc_i["prompt"]
            elif self.task == "swe-bench-lite":
                # Note: This is the current implementation in CodeRAG-Bench
                # Todo: maybe consider allowing users to customize prompts
                # Todo: Maybe consider how to make use of `hints_text`
                prompt = (
                    "You will be provided with a partial code base and "
                    "an issue statement explaining a problem to "
                    "resolve.\n"
                )

                prompt += (
                    "<issue>\n" + doc_i["problem_statement"] + "\n</issue>\n"
                )

            # RAG only: Get retrieved contexts,
            # which is stored in the "docs" field
            docs = doc_i.get("docs", [])
            # Deal with retrieved contexts
            if self.task == "humaneval":
                context = "\n\n".join(doc["text"] for doc in docs)
            elif self.task == "swe-bench-lite":
                # Todo: deal with retrieved contexts for RAG
                pass

            # Construct the final prompt for the agent,
            # Combining original context and  final context

            if self.task == "humaneval":
                final_prompt = (
                    context
                    + '\n\nPlease complete the following function based '
                    'on the example above, DO NOT REPEAT'
                    'PREVIOUS DEFINITIONS :\n' + '```python\n' + prompt
                )
            elif self.task == "swe-bench-lite":
                # Note: This is the current implementation in CodeRAG-Bench
                # Todo: maybe consider allowing users to customize prompts
                final_prompt = prompt + EXAMPLE_PATCH_SWE_Bench

            # A list of generated candidate codes
            candidates = []
            # Run generation using the agent
            for _ in range(n_generation_samples):
                response = agent.step(final_prompt)
                generation = response.msg.content
                logger.debug("GENERATION: %s", generation)
                # === Postprocessing based on CodeRAG-Bench ===
                if self.task == "humaneval":
                    stop_words = [
                        "\nclass",
                        "<file_sep>",
                        "if __name__",
                        "\nprint(",
                        "\ndef",
                    ]
                elif self.task == "swe-bench-lite":
                    stop_words = ["\n<issue>"]

                generation = stop_at_stop_token(generation, stop_words)
                if self.task == "humaneval":
                    generation = prompt + generation
                    logger.debug("%s", "=" * 40)
                    logger.debug("%s", generation)
                    logger.debug("%s", "=" * 40)

                    generation = extract_generation_code(generation, prompt)

                    logger.debug("%s", "=" * 40)
                    logger.debug("%s", generation)
                    logger.debug("%s", "=" * 40)
                elif self.task == "swe-bench-lite":
                    if "```python\n" in generation:
                        generation = extract_code_pieces(
                            generation, prefix="```python"
                        )
                    elif "```\n" in generation:
                        generation = extract_code_pieces(
                            generation, prefix="```"
                        )
                    # Todo: it seems there are specific format requirements
                    # for SWE-bench. The current code is not dealing with
                    # that, and we are simply saving the generated patch as
                    # a list. We should further adjust the format. Maybe we
                    # should disallow multiple candidate generation for
                    # SWE-bench (CodeRAG-Bench is allowing multiple-generation
                    # candidates for simpler subtasks, but I have not yet
                    # checked how it deals with SWE-Bench)

                candidates.append(generation)
            all_generations.append(candidates)

            # Build reference solution
            if self.task == "humaneval":
                test_func = doc_i["test"]
                entry_point = f"check({doc_i['entry_point']})"
                reference = "\n" + test_func + "\n" + entry_point
                all_references.append(reference)
            elif self.task == "swe-bench-lite":
                all_references = []
                logger.info(
                    "Warning: Reference solution is not applicable"
                    "for swe-bench-lite"
                )

        # Save Generation Results
        with open(gen_path, "w") as f_gen:
            json.dump(all_generations, f_gen, indent=2)
            logger.info(f"Saved generations to {gen_path}")

        # Save Generation Results
        if self.task == "humaneval":
            with open(ref_path, "w") as f_ref:
                json.dump(all_references, f_ref, indent=2)
                logger.info(f"Saved references to {ref_path}")

        # === Code Evaluation ===
        # Todo: Think about if/how we want to do evaluation for SWE-Bench here.
        # Todo: No code is implemented about SWE-Bench below this line for now.

        if not allow_code_execution:
            logger.warning(
                "[SKIP] Code execution is disabled. "
                "Set `allow_code_execution=True` to run evaluation."
            )
        else:
            logger.warning(
                "Running code to evaluate the benchmark. "
                "It can be dangerous, as the generated code may "
                "contain unknown or harmful operations. "
                "To ensure safety, please execute all code in a "
                "secure sandboxed environment."
            )
            os.environ["HF_ALLOW_CODE_EVAL"] = (
                "1"  # Allow code execution (sandboxed)
            )

            logger.info("Starting code evaluation...")

            pass_at_k, raw_results = compute_code_eval(
                references=all_references,
                predictions=all_generations,
                k=generation_eval_k,
                num_workers=4,
                timeout=3.0,
            )

            # Print pass@k results
            logger.info("[EVAL] pass@k:")
            for k, v in pass_at_k.items():
                logger.info(f"  {k}: {v:.4f}")

            # Save metrics
            eval_dir = os.path.join(generation_dir, "eval")
            os.makedirs(eval_dir, exist_ok=True)

            eval_path = os.path.join(eval_dir, "pass_at_k.json")
            with open(eval_path, "w") as f_eval:
                json.dump(pass_at_k, f_eval, indent=2)
                logger.info(f"pass@k metrics saved to {eval_path}")

            # Save raw results for analysis
            raw_results_path = os.path.join(eval_dir, "raw_results.jsonl")

            import jsonlines

            with jsonlines.open(raw_results_path, mode="w") as writer:
                for task_id, results in raw_results.items():
                    for completion_id, result in results:
                        writer.write(
                            {
                                "task_id": task_id,
                                "completion_id": completion_id,
                                **result,
                                "generation": all_generations[task_id][
                                    completion_id
                                ],
                                "reference": all_references[task_id],
                            }
                        )
                logger.info(
                    f"Raw evaluation results saved to " f"{raw_results_path}"
                )

            logger.info("Generations saved to %s", gen_path)

            return pass_at_k

    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        retrieve_fn: Optional[RetrieverFn] = None,
        retrieval_top_k: int = 10,
        n_generation_samples: int = 1,
        allow_code_execution: bool = False,
        generation_eval_k: Optional[List[int]] = None,
    ):
        r"""Runs the CodeRAG-Bench benchmark: retrieval and eval.

        Depending on the run mode ("retrieve", "generate", or
        "retrieve_generate"), this method:
        - Retrieves top-k documents for each query.
        - Generates code from retrieved contexts.
        - Optionally executes code to compute pass@k.

        Outputs (retrievals, generations, metrics) are saved to disk.

        Args:
            agent (ChatAgent): Chat agent for code generation.
            retrieve_fn (Optional[RetrieverFn]): A callable that accepts
                query and contents, and may support kwargs like
                `collection_name`, `top_k`, and `return_detailed_info`.
                Required if retrieval is enabled.
                (default: :obj:`None`)
            retrieval_top_k (int, optional): Number of top docs to
                retrieve. (default: :obj:`10`)
            n_generation_samples (int, optional): Number of samples per
                query. (default: :obj:`1`)
            allow_code_execution (bool, optional): Whether to execute
                generated code. Use caution—run in a sandboxed env.
                (default: :obj:`False`)
            generation_eval_k (List[int], optional): k values for pass@k.
                (default: :obj:`List[int]` with value [1, 5, 10])

        Returns:
            Dict[str, Any]: Evaluation metrics.
        """
        if generation_eval_k is None:
            generation_eval_k = [1, 5, 10]

        output_metrics = {}

        if self.dataset is None:
            self.load()

        if self.subset_size is not None:
            logger.info(
                f"Using only first {self.subset_size} samples for testing."
            )
            assert self.dataset is not None
            self.dataset["test"] = self.dataset["test"].select(
                range(self.subset_size)
            )

        # === Retrieval Logic ===
        if self.run_mode in ["retrieve", "retrieve_generate"]:
            logger.info("[INFO] Starting retrieval...")
            output_metrics['retrieval'] = self.run_retrieval(
                retrieve_fn=retrieve_fn, retrieval_top_k=retrieval_top_k
            )

        # === Generation Logic ===
        if self.run_mode in ["generate", "retrieve_generate"]:
            logger.info("[INFO] Starting generation...")
            output_metrics['generation'] = self.run_generation(
                agent=agent,
                n_generation_samples=n_generation_samples,
                allow_code_execution=allow_code_execution,
                generation_eval_k=generation_eval_k,
            )

        return output_metrics
