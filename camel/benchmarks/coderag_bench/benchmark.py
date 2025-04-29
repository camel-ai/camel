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

import json
import logging
import os
import re
from typing import List, Literal, Optional, Union

import datasets
import jsonlines
from datasets import Dataset
from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.retrievers.auto_retriever import AutoRetriever



from beir.retrieval.evaluation import EvaluateRetrieval
from unstructured.documents.elements import Element, Title

from camel.benchmarks.coderag_bench.code_generation_evaluation import (
    compute_code_eval,
)
from camel.embeddings import OpenAIEmbedding

# === BEGIN: Temporary monkey patch for AutoRetriever metadata propagation ===
# This patch enables `.metadata.extra_info` in unstructured.Element to be forwarded
# to VectorRetriever.process(extra_info=...) when used with AutoRetriever.
# Without this, structured document metadata (e.g., doc_id) will be silently discarded.
# A formal enhancement PR will follow for upstream merge.
from camel.retrievers.vector_retriever import VectorRetriever
from camel.types import StorageType
logger = logging.getLogger(__name__)

class CoderagBenchAutoRetriever(AutoRetriever):
    r"""
    A customized AutoRetriever for CodeRAG-Bench that supports vector retrieval
    over a list of `unstructured.Element` documents with preserved metadata.

    Unlike generic retrievers that chunk long documents, this retriever assumes
    each `Element` is already a semantically complete unit (e.g., one code function),
    and uses `should_chunk=False` for ingestion.

    It supports standard retrieval interface `run_vector_retriever` consistent with
    other CAMEL-AI retrievers, and returns either plain text or detailed metadata
    depending on `return_detailed_info`.

    Args:
        storage_type (Optional[StorageType]): The type of vector store to use.
        embedding_model (Optional[OpenAIEmbedding]): Embedding model for indexing and querying.
        vector_storage_local_path (Optional[str]): Path for local storage (if applicable).
        url_and_api_key (Optional[tuple]): Remote storage URL and API key (if applicable).
        overwrite (bool): Whether to re-index documents and overwrite existing collection.
    """

    def __init__(
        self,
        storage_type: Optional[StorageType] = None,
        embedding_model: Optional[OpenAIEmbedding] = None,
        vector_storage_local_path: Optional[str] = None,
        url_and_api_key: Optional[tuple] = None,
        overwrite: bool = False,
    ):
        r"""
        Initializes the retriever with optional vector store config and embedding model.

        Args:
            storage_type (Optional[StorageType]): Type of storage to use.
            embedding_model (Optional[OpenAIEmbedding]): Embedding model to use.
            vector_storage_local_path (Optional[str]): Local vector DB path.
            url_and_api_key (Optional[tuple]): Remote DB config if needed.
            overwrite (bool): Whether to re-index if collection already exists.
        """
        super().__init__(
            storage_type=storage_type,
            embedding_model=embedding_model,
            vector_storage_local_path=vector_storage_local_path,
            url_and_api_key=url_and_api_key,
        )
        self.overwrite = overwrite

    def run_vector_retriever(
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
        r"""
        Runs document-level retrieval on a list of unstructured Elements.

        Supports optional manual specification of collection_name. If not provided,
        a collection name will be automatically generated based on the first Element.

        Args:
            query (str): The user query string.
            contents (Union[Element, List[Element]]): One or more `Element` documents to ingest/query.
            top_k (int): Number of top results to return.
            similarity_threshold (float): Minimum similarity score to retain results.
            return_detailed_info (bool): If True, returns full metadata; else, returns plain text only.
            max_characters (int): Maximum allowed characters per document for embedding.
            collection_name (Optional[str]): Custom name for the vector storage collection. If None, auto-generate.
            **kwargs: Extra keyword arguments for compatibility.

        Returns:
            dict: {
                "Original Query": query,
                "Retrieved Context": [list of texts] or [list of detailed results]
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
                f"Overwriting collection '{collection_name}' with {len(elements)} documents..."
            )
            vector_storage_instance.clear()
            vector_count = 0

        if vector_count == 0:
            logger.debug(
                f"Ingesting {len(elements)} documents into vector store '{collection_name}'"
            )
            for elem in elements:
                vr.process(
                    content=elem,
                    max_characters=max_characters,
                    should_chunk=False,
                    extra_info=getattr(elem.metadata, "extra_info", {}),
                )
            logger.debug(
                f"Vector store now contains {vector_storage_instance.status().vector_count} documents"
            )
        else:
            logger.debug(
                f"Vector store '{collection_name}' already contains {vector_count} vectors. Skipping ingestion."
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
    r"""
    Convert document samples into code generation pairs for IR evaluation.

    This function is directly adapted from the CodeRAG-Bench repository:
        GitHub: https://github.com/code-rag-bench/code-rag-bench/blob/main/retrieval/create/humaneval.py

    It constructs a flat list of query-document pairs and relevance judgments from a
    code generation dataset. Each sample contains a "prompt" and its corresponding
    "canonical_solution". The prompt is used as the query, and the concatenation of
    prompt + solution is treated as the relevant code document.

    Note:
        This function is preserved **unmodified** to ensure compatibility with the original
        CodeRAG-Bench logic. To convert the output into BEIR-compatible dictionary format,
        use the wrapper function `wrap_as_beir_loader`.

    Args:
        data (dict): Dataset split dictionary, e.g., {"test": [...]}.
        split (str): Dataset split to process (default: "test").

    Returns:
        Tuple[List[dict], List[dict], List[dict]]:
            - queries: List of dicts with "_id" and "text".
            - docs: List of dicts with "_id", "text", and "title".
            - qrels: List of dicts linking queries to relevant documents.
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
    r"""
    Wraps the output of `document2code()` into BEIR-compatible dictionary format.

    This function converts flat lists of queries, documents, and qrels into dictionaries
    keyed by ID, as expected by BEIR's evaluation tools.

    It is intended to be used directly after `document2code()` to prepare the dataset
    for retrieval benchmarking.

    Args:
        queries_list (List[dict]): List of queries with "_id" and "text" fields.
        corpus_list (List[dict]): List of documents with "_id", "text", and metadata.
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
    r"""
    Extracts Python code blocks from a text string formatted with Markdown-style triple backticks.

    This function scans the input text and extracts code segments that start with a given prefix
    (e.g., "```python") and end with a closing triple backtick ("```"). It is useful for extracting
    model-generated code from responses that follow Markdown formatting conventions.

    Args:
        text (str): The input string potentially containing code blocks.
        prefix (str): The Markdown code block prefix to search for (default: "```python").
        return_all (bool): If True, returns all extracted code blocks concatenated with double newlines.
                           If False, returns only the first matched block.

    Returns:
        str: The extracted code block(s) as a string. If no block is found, returns an empty string.

    Note:
        This implementation is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/utils.py

    Example:
        >>> text = "Here is the function:\n```python\ndef add(a, b):\n    return a + b\n```"
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
    Extracts the function name and the prefix (preceding lines) from a code prompt.

    This is useful for evaluation purposes where the generated function needs to be
    compared or executed with a known entry point name. The logic assumes a simple structure
    where either the last Python function is the target, or in non-Python languages, the
    function appears at the end enclosed in curly braces.

    Args:
        question (str): The full code prompt or question containing the function definition.
        lang (str): The programming language (e.g., "python", "java").

    Returns:
        Tuple[str, str]: A tuple of (function_name, function_prefix), where function_prefix
                         is the code before the function definition.

    Notes:
        This function is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/utils.py
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
    r"""
    Indents each non-empty line in a code block by a specified number of spaces.

    This is typically used to ensure that generated code fits correctly within
    a function body, control structure, or other nested context.

    Args:
        code (str): The input code block as a string.
        indent (int): The number of spaces to add at the beginning of each non-empty line. Defaults to 4.

    Returns:
        str: The indented code block as a single string.
    """
    return "\n".join(
        " " * indent + line if line.strip() else ""
        for line in code.splitlines()
    )


def extract_generation_code(output: str, question: str) -> str:
    r"""
    Extracts the generated Python code block from a model's output and reconstructs
    it with the original function header from the prompt.

    This ensures that the generated code can be executed properly by attaching
    it to the original function signature and any necessary imports.

    The extraction follows the pattern of locating the first ```python ... ``` block
    in the output, combined with parsing the function definition line from the prompt.

    Note:
        This implementation is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/utils.py

    Args:
        output (str): The raw model output containing a code snippet.
        question (str): The original prompt, containing the intended function signature.

    Returns:
        str: The reconstructed full function code, or the raw output if extraction fails.
    """
    try:
        # Extract the content within ```python ... ``` block
        code_block = re.findall(
            r"```python\n(.*?)```", output, re.DOTALL | re.IGNORECASE
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
    r"""
    Produces the prefix of the decoded string that ends at the first occurrence
    of any stop token.

    This function searches for the earliest appearance of any provided stop token
    in the decoded string and truncates the string at that point.

    Warning:
        The `decoded_string` must not include the prompt itself, as the prompt may
        contain stop tokens that should be ignored.

    Note:
        This implementation is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/tasks/humaneval.py

    Args:
        decoded_string (str): The generated text output to be processed.
        stop_tokens (list[str]): A list of stop tokens to search for in the decoded text.

    Returns:
        str: The truncated decoded string ending before the first occurrence of a stop token.
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
    r"""
    Retrieves the top-ranked documents for a given task based on retrieval scores.

    This function sorts the documents associated with a specific task ID by their
    similarity scores in descending order, and returns the corresponding code snippets
    from the corpus.

    If the task ID is not present in the results, an empty list is returned.

    Note:
        This implementation is adapted from:
        https://github.com/code-rag-bench/code-rag-bench/blob/main/retrieval/eval_beir_sbert_canonical.py

    Args:
        results (dict): A mapping from task IDs to document-score dictionaries.
        corpus (dict): A mapping from document IDs to their content (e.g., code snippets).
        task_id (str): The identifier for the task whose top documents are to be retrieved.
        topk (int): The number of top documents to return. Defaults to 10.

    Returns:
        list[str]: A list of top code snippets or documents corresponding to the task ID.
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


class CodeRagBenchmark(BaseBenchmark):
    r"""
    CodeRag-Bench Benchmark for evaluating retrieval-augmented generation (RAG) performance
    across multiple programming datasets.

    This benchmark supports:
    - Canonical retrieval evaluation
    - Code generation based on retrieved contexts
    - End-to-end retrieval and generation evaluation
    - Pass@k code evaluation with optional execution

    Currently, only the "humaneval" task and canonical retrieval are supported.

    Attributes:
        task (str): The name of the target evaluation dataset.
        run_mode (str): Execution mode ("retrieve", "generate", or "retrieve_generate").
        retrieval_type (str): Type of retrieval ("canonical" or "open").
        subset_size (Optional[int]): Optional subset size for quicker benchmarking.
        dataset (Optional[Dataset]): Loaded dataset.
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
        r"""
        Initializes the CodeRagBenchmark instance with configuration options.

        Args:
            data_dir (str): Path to the data directory.
            save_to (str): Path to save the results and outputs.
            task (str): Evaluation task name.
            run_mode (str): Mode to run ("retrieve"(only), "generate"(only), "retrieve_generate").
            retrieval_type (str): Retrieval method ("canonical" or "open").
            subset_size (Optional[int]): If set, limits evaluation to a subset of the data.
        """
        super().__init__("coderag_bench", data_dir, save_to)
        self.task = task
        self.retrieval_type = retrieval_type
        self.run_mode = run_mode
        self.dataset: Optional[Dataset] = None
        self.subset_size = subset_size

        # Todo: Support other 6 tasks, e.g., mbpp, ds100,...
        if self.task != "humaneval":
            raise NotImplementedError(
                "Only canonical retrieval is supported for now."
            )

    def download(self):
        r"""
        Downloads and preprocesses the CodeRag-Bench dataset if necessary.

        Currently, only supports downloading and preparing the "humaneval" dataset.

        Returns:
            None
        """
        if self.task == "humaneval":
            logger.info(
                f"Downloading and processing dataset for task: {self.task}"
            )
            dataset = datasets.load_dataset("openai_humaneval")
            self.dataset = dataset

        else:
            raise NotImplementedError(
                f"Download() not implemented for task: {self.task}"
            )
            pass

    def load(self, force_download: bool = False):
        r"""
        Loads the dataset into memory. Downloads if not already available or if forced.

        Args:
            force_download (bool, optional): Whether to force re-downloading the dataset.

        Returns:
            None
        """
        if force_download or self.dataset is None:
            logger.info(
                "%s dataset",
                "Force downloading" if force_download else "Loading",
            )
            self.download()

    def run(
        self,
        agent: ChatAgent,
        auto_retriever: Optional[
            CoderagBenchAutoRetriever
        ] = None,
        retrieval_top_k=10,
        n_generation_samples: int = 1,
        allow_code_execution=False,
        generation_eval_k=[1, 5, 10],
    ):
        r"""
        Runs the CodeRAG-Bench benchmark, including retrieval, code generation, and evaluation.

        Depending on the specified run mode ("retrieve", "generate", or "retrieve_generate"), this method:
        - Retrieves top-k documents for each query.
        - Generates code based on the retrieved contexts.
        - Optionally executes generated code to compute pass@k metrics.

        Benchmark outputs, including retrieval results, generations, and evaluation metrics, are saved to disk.

        Args:
            agent (ChatAgent): Chat agent used for code generation.
            auto_retriever (Optional[CoderagBenchAutoRetriever]): Retriever used for document retrieval. Required if retrieval is enabled.
            retrieval_top_k (int, optional): Number of top documents to retrieve for each query. Defaults to 10.
            n_generation_samples (int, optional): Number of code generations to sample per query. Defaults to 1.
            allow_code_execution (bool, optional): Whether to execute generated code for pass@k evaluation. **Warning:** Executing untrusted code may be unsafe. Always run in a sandboxed environment. Defaults to False.
            generation_eval_k (List[int], optional): List of k values for pass@k computation (e.g., [1, 5, 10]). Defaults to [1, 5, 10].

        Returns:
            Dict[str, Any]: A dictionary containing retrieval and/or generation evaluation metrics.
        """

        output_metrics = {}

        if self.dataset is None:
            self.load()

        if self.subset_size is not None:
            logger.info(
                f"Using only first {self.subset_size} samples for testing."
            )
            self.dataset["test"] = self.dataset["test"].select(
                range(self.subset_size)
            )

        if self.run_mode in ["retrieve", "retrieve_generate"]:
            queries_list, docs_list, qrels_list = document2code(self.dataset)
            """
            corpus: Corpus used for retrieval.
            queries: Queries used for retrieval evaluation.
            qrels: Relevance labels for retrieval evaluation.
            """
            queries, corpus, qrels = wrap_as_beir_loader(
                queries_list, docs_list, qrels_list
            )

            # Todo: Support Open retrieval
            if self.retrieval_type != "canonical":
                raise NotImplementedError(
                    "Only canonical retrieval is supported for now."
                )

            if auto_retriever is None:
                raise ValueError(
                    "auto_retriever must be provided in retrieve or retrieve_generate mode"
                )

            # === Canonical Retrieval Logic ===
            logger.info("Starting canonical retrieval...")

            # Convert the corpus into a list of Element objects (one per document),
            # and assign a consistent file_directory to group them into a single vector collection.
            elements = []
            collection_name = f"{self.task}_collection"
            for doc_id, doc in corpus.items():
                element = Title(text=doc["text"])
                element.metadata.file_directory = collection_name
                element.metadata.extra_info = {"doc_id": doc_id}
                elements.append(element)

            for idx, elem in enumerate(elements):
                logger.debug("Element #%d", idx)
                logger.debug(
                    "Text preview: %s", elem.text[:80].replace('\n', ' ')
                )
                logger.debug(
                    "file_directory: %s", elem.metadata.file_directory
                )
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

            with jsonlines.open(output_path, mode='w') as writer:
                for example in tqdm(self.dataset["test"]):
                    query_text = example["prompt"]
                    query_id = (
                        example["task_id"] + "_doc"
                    )  # make sure the format is the same as qrel, for evaluation purposes

                    # Use any one element to trigger collection matching.
                    # All elements share the same file_directory, so this is safe.
                    result = auto_retriever.run_vector_retriever(
                        query=query_text,
                        contents=elements,
                        collection_name=collection_name,
                        top_k=retrieval_top_k,
                        similarity_threshold=0.0,
                        return_detailed_info=True,
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

                        scores[doc_id] = float(
                            item.get("similarity score", 0.0)
                        )
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

                    # Merge retrieved docs into the original sample and stream write
                    example_with_docs = dict(example)
                    example_with_docs["docs"] = doc_entries
                    writer.write(example_with_docs)

            self.dataset["test"] = datasets.load_dataset(
                "json", data_files=output_path, split="train"
            )
            # Evaluate using BEIR
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
            output_metrics['retrieval'] = metrics

            with open(metrics_path, "w") as f:
                json.dump(metrics, f, indent=2)

            logger.info("Retrieval results saved to %s", output_path)
            logger.info("Retrieval metrics saved to %s", metrics_path)
            logger.info("Canonical retrieval completed.")

        # === Generation Logic ===
        if self.run_mode in ["generate", "retrieve_generate"]:
            logger.info("[INFO] Starting generation...")

            generation_dir = os.path.join(
                self.save_to, "generation", self.task
            )
            os.makedirs(generation_dir, exist_ok=True)

            gen_path = os.path.join(generation_dir, "generations.json")
            ref_path = os.path.join(generation_dir, "references.json")

            all_generations = []  # List[List[str]]: list of candidates per task
            all_references = []  # List[str]: one reference string per task

            for idx, data_i in enumerate(
                tqdm(self.dataset["test"])
            ):  # data_i is equivalent to doc in <https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/tasks/humaneval.py>
                prompt = data_i["prompt"]

                docs = data_i.get("docs", [])
                context = "\n\n".join(
                    doc["text"] for doc in docs[:10]
                )  # Top-10 Todo: allow customization of top-k retrieval!

                # Construct the final prompt for the agent
                final_prompt = (
                    context
                    + '\n\nPlease complete the following function based on the example above:\n'
                    + '```python\n'
                    + prompt
                )

                candidates = []
                # Run generation using the agent
                for _ in range(n_generation_samples):
                    response = agent.step(final_prompt)
                    generation = response.msg.content

                    # === Postprocessing based on CodeRAG-Bench ===
                    stop_words = [
                        "\nclass",
                        "<file_sep>",
                        "if __name__",
                        "\nprint(",
                        "\ndef",
                    ]
                    generation = stop_at_stop_token(generation, stop_words)
                    generation = prompt + generation
                    logger.debug("%s", "=" * 40)
                    logger.debug("%s", generation)
                    logger.debug("%s", "=" * 40)

                    generation = extract_generation_code(generation, prompt)

                    logger.debug("%s", "=" * 40)
                    logger.debug("%s", generation)
                    logger.debug("%s", "=" * 40)
                    candidates.append(generation)
                all_generations.append(candidates)

                # Build reference
                test_func = data_i["test"]
                entry_point = f"check({data_i['entry_point']})"
                reference = "\n" + test_func + "\n" + entry_point
                all_references.append(reference)

            with open(gen_path, "w") as f_gen:
                json.dump(all_generations, f_gen, indent=2)
                logger.info(f"Saved generations to {gen_path}")

            with open(ref_path, "w") as f_ref:
                json.dump(all_references, f_ref, indent=2)
                logger.info(f"Saved references to {ref_path}")

            # === Code Evaluation ===
            if not allow_code_execution:
                logger.warning(
                    "[SKIP] Code execution is disabled. Set `allow_code_execution=True` to run evaluation."
                )
            else:
                logger.warning(
                    "Running code to evaluate the benchmark. It can be dangerous, as the generated code may contain unknown or harmful operations. To ensure safety, please execute all code in a secure sandboxed environment."
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
                output_metrics['generation'] = pass_at_k

                # Save raw results for analysis
                raw_results_path = os.path.join(eval_dir, "raw_results.jsonl")
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
                        f"Raw evaluation results saved to {raw_results_path}"
                    )

                logger.info("Generations saved to %s", gen_path)
        return output_metrics
