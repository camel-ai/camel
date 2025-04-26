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
import random
import re
import string
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Protocol, Union
import datasets
import jsonlines

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.messages import BaseMessage
from camel.retrievers.auto_retriever import AutoRetriever
from datasets import Dataset
logger = logging.getLogger(__name__)

from beir.datasets.data_loader import GenericDataLoader
from beir.retrieval.evaluation import EvaluateRetrieval

from camel.benchmarks.coderag_bench.code_generation_evaluation import compute_code_eval
import re
from unstructured.documents.elements import Title, Element

# === BEGIN: Temporary monkey patch for AutoRetriever metadata propagation ===
# This patch enables `.metadata.extra_info` in unstructured.Element to be forwarded
# to VectorRetriever.process(extra_info=...) when used with AutoRetriever.
# Without this, structured document metadata (e.g., doc_id) will be silently discarded.
# A formal enhancement PR will follow for upstream merge.

from camel.retrievers.auto_retriever import AutoRetriever
from camel.retrievers.vector_retriever import VectorRetriever

def patched_run_vector_retriever(
    self,
    query,
    contents,
    top_k=5,
    similarity_threshold=0.7,
    return_detailed_info=False,
    max_characters=500,
):
    # Ensure contents is a list of Element
    if not isinstance(contents, list):
        contents = [contents]

    if len(contents) == 0:
        raise ValueError("No content provided to run_vector_retriever.")

    # Use the first element to determine the collection name
    collection_name = self._collection_name_generator(contents[0])
    vector_storage_instance = self._initialize_vector_storage(collection_name)

    vr = VectorRetriever(
        storage=vector_storage_instance,
        embedding_model=self.embedding_model,
    )

    # Only embed if storage is empty
    if vector_storage_instance.status().vector_count == 0:
        print(f"[DEBUG] Ingesting {len(contents)} documents into vector store '{collection_name}'")

        for elem in contents:
            vr.process(
                content=elem,
                max_characters=max_characters,
                should_chunk=False,  # preserve document granularity
                extra_info=getattr(elem.metadata, "extra_info", {}),
            )

        # Sanity check: make sure the count matches
        vector_count = vector_storage_instance.status().vector_count
        if vector_count != len(contents):
            raise RuntimeError(
                f"Mismatch in document count: embedded {len(contents)} documents "
                f"but vector store contains {vector_count}"
            )
        print(f"[DEBUG]  Vector store now contains {vector_count} documents")

    # Run vector query
    retrieved_info = vr.query(query, top_k, similarity_threshold)

    text_only = [item["text"] for item in retrieved_info]
    return {
        "Original Query": query,
        "Retrieved Context": retrieved_info if return_detailed_info else text_only,
    }

# Inject monkey patch
AutoRetriever.run_vector_retriever = patched_run_vector_retriever
# === END: Monkey patch ===
from camel.types import StorageType
from camel.embeddings import OpenAIEmbedding
from typing import Optional, List
class CoderagBenchAutoRetriever(AutoRetriever):
    """
    A customized AutoRetriever for CodeRAG-Bench to support retrieval from
    a list of unstructured.Elements with preserved metadata.

    This class enables document-level ingestion and retrieval without chunking,
    making it suitable for cases where:
      - each Element is already a fully-formed document (e.g., one code function),
      - `.metadata.extra_info` contains structured identifiers (e.g., doc_id),
      - all Elements belong to the same retrieval corpus and should be stored
        in a shared vector collection.

    Chunking is explicitly disabled here because in CodeRAG-Bench,
    each sample (typically a function-level code generation task) is already
    preprocessed as a single coherent unit. Re-chunking such inputs would
    break their semantic structure and degrade retrieval quality.

    This implementation is currently specific to CodeRAG-Bench but may be
    generalized and moved to `camel.retrievers` in the future.

    Args:
        overwrite (bool): Whether to forcibly re-embed and overwrite existing vector index.
    """

    def __init__(
        self,
        storage_type: Optional[StorageType] = None,
        embedding_model: Optional[OpenAIEmbedding] = None,
        vector_storage_local_path: Optional[str] = None,
        url_and_api_key: Optional[tuple] = None,
        overwrite: bool = False,
    ):
        super().__init__(
            storage_type=storage_type,
            embedding_model=embedding_model,
            vector_storage_local_path=vector_storage_local_path,
            url_and_api_key=url_and_api_key,
        )
        self.overwrite = overwrite

    def run_element_list_retriever(
        self,
        query: str,
        elements: List["Element"],
        collection_name: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        return_detailed_info: bool = False,
        max_characters: int = 500,
    ) -> dict:
        if not elements:
            raise ValueError("No elements provided for retrieval.")

        collection_name = collection_name or self._collection_name_generator(elements[0])
        vector_storage_instance = self._initialize_vector_storage(collection_name)

        vr = VectorRetriever(
            storage=vector_storage_instance,
            embedding_model=self.embedding_model,
        )

        vector_count = vector_storage_instance.status().vector_count

        if self.overwrite and vector_count > 0:
            print(f"[DEBUG] Overwriting collection '{collection_name}' with {len(elements)} documents...")
            vector_storage_instance.clear()
            vector_count = 0

        if vector_count == 0:
            print(f"[DEBUG] Ingesting {len(elements)} documents into vector store '{collection_name}'")
            for elem in elements:
                vr.process(
                    content=elem,
                    max_characters=max_characters,
                    should_chunk=False,
                    extra_info=getattr(elem.metadata, "extra_info", {}),
                )
            print(f"[DEBUG] Vector store now contains {vector_storage_instance.status().vector_count} documents")
        else:
            print(f"[DEBUG] Vector store '{collection_name}' already contains {vector_count} vectors. Skipping ingestion.")

        retrieved_info = vr.query(query, top_k=top_k, similarity_threshold=similarity_threshold)

        return {
            "Original Query": query,
            "Retrieved Context": retrieved_info if return_detailed_info else [r["text"] for r in retrieved_info],
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
            {"_id": code_id, "title": item["entry_point"], "text": code,
             "metadata": {}})
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


def extract_code_pieces(text: str, prefix: str = "```python",
                        return_all: bool = False) -> str:
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
        text = text[end_idx + 3:].strip()
    if return_all: return '\n\n'.join(code_pieces)
    return code_pieces[0]


def get_function_name(question: str, lang: str):
    """
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
        func_idx = [i for i in range(len(func_lines)) if
                    func_lines[i].startswith("def ")][-1]
        func_name = func_lines[func_idx].split('(')[0].strip()
        func_prefix = "\n".join(func_lines[:func_idx])
        return func_name, func_prefix

    func_name = func_lines[-1].split('{')[0].strip()
    func_prefix = "\n".join(func_lines[:-1])
    return func_name, func_prefix


def indent_code_block(code: str, indent: int = 4) -> str:
    """
    Indent each line of the code block with a given number of spaces.
    This ensures the generated code fits correctly inside the function body.
    """
    return "\n".join(" " * indent + line if line.strip() else "" for line in code.splitlines())


def extract_generation_code(output: str, question: str) -> str:
    """
    Extract the generated Python code block from model output and attach it
    back to the original function header (from the prompt).
    """
    try:
        # Extract the content within ```python ... ``` block
        code_block = re.findall(r"```python\n(.*?)```", output, re.DOTALL | re.IGNORECASE)[0]

        # Get the original function header from the prompt
        func_lines = [line for line in question.strip().split('\n') if line.strip()]
        def_idx = [i for i, line in enumerate(func_lines) if line.strip().startswith("def ")][-1]
        func_header = func_lines[def_idx]
        imports = "\n".join(func_lines[:def_idx])  # All lines above the def line

        # Combine everything together with proper indentation
        full_code = f"{imports}\n\n{func_header}\n" + indent_code_block(code_block)
        return full_code

    except Exception as ex:
        print(f"Failed to extract code block: {ex}")
        return output.strip()  # Fallback to raw output


def stop_at_stop_token(decoded_string, stop_tokens):
    """
    Produces the prefix of decoded_string that ends at the first occurrence of
    a stop_token.
    WARNING: the decoded_string *must not* include the prompt, which may have stop tokens
    itself.
    """
    min_stop_index = len(decoded_string)
    for stop_token in stop_tokens:
        stop_index = decoded_string.find(stop_token)
        if stop_index != -1 and stop_index < min_stop_index:
            min_stop_index = stop_index
    return decoded_string[:min_stop_index]


def get_top_docs(results: dict, corpus: dict, task_id: str, topk: int = 10) -> list[str]:
    if task_id not in results: return []
    doc_scores = results[task_id]
    doc_scores_sorted = sorted(doc_scores.items(), key=lambda item: item[1], reverse=True)
    doc_scores_sorted = doc_scores_sorted[:topk]
    doc_code_snippets = [corpus[code_id] for code_id, score in doc_scores_sorted]
    return doc_code_snippets

class CodeRagBenchmark(BaseBenchmark):
    r"""CodeRag-Bench Benchmark for evaluating RAG performance."""


    def __init__(
        self,
        data_dir: str,
        save_to: str,

        task: Literal[
            "humaneval","mbpp","live_code_bench","ds1000", "odex","repoeval_repo","swebench_repo"
        ] = "humaneval",
        run_mode: Literal["retrieve", "generate", "retrieve_generate"] = "retrieve_generate",
        retrieval_type: Literal['canonical','open'] = "canonical",
        n_samples: int = 1,
        allow_code_execution = False,
        generation_eval_k = [1,5,10],
        subset_size: Optional[int] = None,
    ) -> None:
        r"""Initialize the benchmark.

            Args:
                name (str): Name of the benchmark.
                data_dir (str): Path to the data directory.
                save_to (str): Path to save the results.
                processes (int): Number of processes to use for parallel
                    processing. :(default: :obj:`1`)

            """
        super().__init__("coderag_bench", data_dir, save_to)
        self.task = task
        self.retrieval_type = retrieval_type
        self.run_mode = run_mode
        self.dataset: Optional[Dataset] = None
        self.corpus: Optional[dict] = None
        self.queries: Optional[dict] = None
        self.qrels: Optional[dict] = None
        self.n_samples = n_samples
        self.allow_code_execution = allow_code_execution
        self.generation_eval_k = generation_eval_k
        self.subset_size = subset_size

        # Todo: Support other 6 tasks, e.g., mbpp, ds100,...
        if self.task != "humaneval":
            raise NotImplementedError(
                "Only canonical retrieval is supported for now.")

    def download(self):
        r"""Download and preprocess the CodeRag-Bench data.

        Returns:

        """
        if self.task == "humaneval":
            logger.info(f"[INFO] Downloading and processing dataset for task: {self.task}")
            dataset = datasets.load_dataset("openai_humaneval")
            self.dataset = dataset

        else:
            logger.info(f"[INFO] download() not implemented for task: {self.task}")
            pass


    def load(self, force_download: bool = False):
        r"""Load the CodeRAG-Bench dataset.

        Args:
            force_download (bool, optional): Whether to force download the
                data.
        """
        if force_download or self.dataset is None:
            logger.info(
                "%s dataset",
                "Force downloading" if force_download else "Loading",
            )
            self.download()
        # if self.run_mode in ["retrieve", "retrieve_generate"]:
        #     path = os.path.join(self.data_dir, "datasets")
        #
        #     self.corpus, self.queries, self.qrels = GenericDataLoader(
        #         data_folder=os.path.join(path, self.task)).load(split="test")


    def run(  # type: ignore[override, return]
            self,
            agent: ChatAgent,
            auto_retriever: Optional[CoderagBenchAutoRetriever] = None, # TODO: Currently only supports canonical retriever. Add support for other retrieval types.
    ):
        r"""Load the CodeRAG-Bench dataset.
            save benchmark result to files
            return evaluation result"""

        if self.corpus is None or self.queries is None or self.qrels is None or self.dataset is None:
            self.load()

        if self.subset_size is not None:
            logger.info(
                f"[INFO] Using only first {self.subset_size} samples for testing.")
            self.dataset["test"] = self.dataset["test"].select(
                range(self.subset_size))

        if self.run_mode in ["retrieve", "retrieve_generate"]:
            # path = os.path.join(self.datadir, "datasets")
            # os.makedirs(path, exist_ok=True)
            # os.makedirs(os.path.join(path, "humaneval"), exist_ok=True)
            # os.makedirs(os.path.join(path, "humaneval", "qrels"),
            #             exist_ok=True)
            queries_list, docs_list, qrels_list = document2code(self.dataset)
            self.queries, self.corpus, self.qrels = wrap_as_beir_loader(
                queries_list, docs_list, qrels_list)
            # save_file_jsonl(queries, os.path.join(path, "queries.jsonl"))
            # save_file_jsonl(docs, os.path.join(path, "corpus.jsonl"))
            # qrels_path = os.path.join(path, "qrels", "test.tsv")
            # save_tsv_dict(qrels, qrels_path,
            #               ["query-id", "corpus-id", "score"])
            #
            # # create canonical file path if not existent yet
            # os.makedirs(os.path.join(path, "canonical"), exist_ok=True)
            # # Todo: Maybe later allow users to specify canonical file name
            # canonical_file = os.path.join(path, "canonical",
            #                               "humaneval_solutions.json")
            # if not os.path.exists(canonical_file):
            #     canonical_solutions = []
            #     for doc in docs:
            #         canonical_solutions.append([{
            #             "text": doc["text"], "title": doc["title"]
            #         }])
            #     canonical_dataset = dataset["test"].add_column("docs",
            #                                                    canonical_solutions)
            #     canonical_dataset.to_json(canonical_file)

            # path = os.path.join(self.datadir, "datasets")
            # self.corpus, self.queries, self.qrels = GenericDataLoader(
            #     data_folder=os.path.join(path, self.task)).load(split="test")

            # Todo: Support Canonical retrieval
            if self.retrieval_type != "canonical":
                raise NotImplementedError(
                    "Only canonical retrieval is supported for now.")


            if auto_retriever is None:
                raise ValueError(
                    "auto_retriever must be provided in retrieve or retrieve_generate mode")



            # === Canonical Retrieval Logic ===
            logger.info("[INFO] Starting canonical retrieval...")

            # Convert the corpus into a list of Element objects (one per document),
            # and assign a consistent file_directory to group them into a single vector collection.
            elements = []
            #doc_id_map = {}
            collection_name = f"{self.task}_collection"

            for doc_id, doc in self.corpus.items():
                element = Title(text=doc["text"])
                element.metadata.file_directory = collection_name
                element.metadata.extra_info = {
                    "doc_id": doc_id}
                elements.append(element)
                #doc_id_map[doc["text"]] = doc_id

            for idx, elem in enumerate(elements):
                print(f"[DEBUG] Element #{idx}")
                print("Text preview:", elem.text[:80].replace('\n', ' '))
                print("file_directory:", elem.metadata.file_directory)
                print("other:", getattr(elem.metadata, "other", {}))
                print("-" * 50)
            # Force all documents to be stored in a single vector collection.
            # This prevents AutoRetriever from generating a separate collection for each document.
            # auto_retriever._collection_name_generator = lambda _: f"{self.task}_collection"

            print("[DEBUG] First element metadata:", elements[0].metadata.to_dict())
            # Build the vector index once using the entire document set.
            # Later queries will reuse this collection.
            # auto_retriever.run_vector_retriever(
            #     query="dummy",
            #     contents=elements,
            #     top_k=10,
            # )

            # vector_storage = auto_retriever._initialize_vector_storage(
            #     collection_name)
            # print("[DEBUG] Vector count:",
            #       vector_storage.status().vector_count)

            retrieval_results = {}

            # Prepare output directory
            output_dir = os.path.join(self.save_to, "retrieval")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir,
                                       f"{self.task}_retrieved_docs.jsonl")
            metrics_path = os.path.join(output_dir,
                                        f"{self.task}_retrieval_metrics.json")

            with jsonlines.open(output_path, mode='w') as writer:
                for example in tqdm(self.dataset["test"]):

                    query_text = example["prompt"]
                    query_id = example[
                                   "task_id"] + "_doc"  # make sure the format is the same as qrel, for evaluation purposes

                    # Use any one element to trigger collection matching.
                    # All elements share the same file_directory, so this is safe.
                    #dummy_element = elements[0]
                    result = auto_retriever.run_element_list_retriever(
                        query=query_text,
                        elements=elements,
                        collection_name=collection_name,
                        top_k=10,
                        similarity_threshold=0.0,
                        return_detailed_info=True,
                    )

                    # print for debugging
                    print(f"\n[DEBUG] Query: {query_text[:60]}")
                    print(f"[DEBUG] Retrieved Context: {result['Retrieved Context']}")

                    doc_entries = []
                    scores = {}



                    for item in result["Retrieved Context"]:

                        doc_text = item["text"]
                        doc_id = item.get("extra_info", {}).get("doc_id")
                        if doc_id is None:
                            continue  # fallback or missing metadata

                        scores[doc_id] = float(item.get("similarity score", 0.0))
                        doc_entries.append({
                            "doc_id": doc_id,
                            "text": doc_text,
                            "title": self.corpus[doc_id].get("title", ""),
                            "similarity": float(item.get("similarity score", 0.0))
                        })

                    # Save scores for retrieval evaluation
                    retrieval_results[query_id] = scores

                    # Merge retrieved docs into the original sample and stream write
                    example_with_docs = dict(example)
                    example_with_docs["docs"] = doc_entries
                    writer.write(example_with_docs)

            self.dataset["test"] = datasets.load_dataset("json", data_files=output_path,
                                                split="train")
            # Evaluate using BEIR

            retriever = EvaluateRetrieval(score_function="dot")
            k_values = [1, 5, 10]
            print("qrels keys:", list(self.qrels.keys())[:5])
            print("retrieval_results keys:",
                  list(retrieval_results.keys())[:5])

            for qid in self.qrels:
                relevant_doc_ids = set(self.qrels[qid].keys())
                retrieved_doc_ids = set(retrieval_results.get(qid, {}).keys())

                if not relevant_doc_ids & retrieved_doc_ids:
                    print(f"[NO MATCH] for query {qid}")
                else:
                    print(f"[MATCH] {qid} retrieved")
                print(f"  gold:      {relevant_doc_ids}")
                print(f"  retrieved: {retrieved_doc_ids}")

            ndcg, _map, recall, precision = retriever.evaluate(
                self.qrels, retrieval_results, k_values,ignore_identical_ids=False)
            mrr = retriever.evaluate_custom(self.qrels,
                                            retrieval_results,
                                            k_values, metric="mrr")



            metrics = {
                "ndcg": ndcg,
                "mrr": mrr,
                "recall": recall,
                "precision": precision,
            }

            with open(metrics_path, "w") as f:
                json.dump(metrics, f, indent=2)

            logger.info("[INFO] Retrieval results saved to %s",
                        output_path)
            logger.info("[INFO] Retrieval metrics saved to %s",
                        metrics_path)
            logger.info("[INFO] Canonical retrieval completed.")

        # ============================================
        # generation part
        if self.run_mode in ["generate", "retrieve_generate"]:
            logger.info("[INFO] Starting generation...")
            # TODO: Implement generation + save + evaluation

            generation_dir = os.path.join(self.save_to, "generation",
                                          self.task)
            os.makedirs(generation_dir, exist_ok=True)

            # Todo: Allow path customization!!
            gen_path = os.path.join(generation_dir, "generations.json")
            ref_path = os.path.join(generation_dir, "references.json")
            # # Open retrieval results stream if needed
            # if self.run_mode == "retrieve_generate":
            #     retrieved_path = os.path.join(self.save_to, "retrieval",
            #                                   f"{self.task}_retrieved_docs.jsonl")
            #     retrieval_reader = jsonlines.open(retrieved_path, mode='r')
            # else:
            #     retrieval_reader = None

            all_generations = []  # List[List[str]]: list of candidates per task
            all_references = []  # List[str]: one reference string per task

            for idx, data_i in enumerate(tqdm(self.dataset["test"])): # data_i is equivalent to doc in <https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/tasks/humaneval.py>
                prompt = data_i["prompt"]

                docs = data_i.get("docs", [])
                context = "\n\n".join(
                    doc["text"] for doc in docs[:10])  # Top-10 Todo: allow customization of top-k retrieval!

                # Construct the final prompt for the agent
                final_prompt = (
                        context +
                        '\n\nPlease complete the following function based on the example above:\n' +
                        '```python\n' +
                        prompt
                )

                candidates = []
                # Run generation using the agent
                for _ in range(self.n_samples): #Todo: initilize n_samples in init file
                    response = agent.step(final_prompt)
                    generation = response.msg.content

                    # === Postprocessing based on CodeRAG-Bench ===
                    stop_words = ["\nclass", "<file_sep>", "if __name__",
                                  "\nprint(", "\ndef"]
                    generation = stop_at_stop_token(generation,
                                                          stop_words)
                    generation = prompt + generation
                    print("1=" * 40)
                    print(generation)
                    print("1=" * 40)
                    generation = extract_generation_code(generation,
                                                         prompt)

                    print("=" * 40)
                    print(generation)
                    print("=" * 40)
                    candidates.append(generation)
                all_generations.append(candidates)

                # Build reference
                test_func = data_i["test"]
                entry_point = f"check({data_i['entry_point']})"
                reference = "\n" + test_func + "\n" + entry_point
                all_references.append(reference)

            # Save to JSON files
            with open(gen_path, "w") as f_gen:
                json.dump(all_generations, f_gen, indent=2)
                logger.info(f"[INFO] Saved generations to {gen_path}")

            with open(ref_path, "w") as f_ref:
                json.dump(all_references, f_ref, indent=2)
                logger.info(f"[INFO] Saved references to {ref_path}")

            # === Code Evaluation ===
            if not self.allow_code_execution:
                logger.warning(
                    "[SKIP] Code execution is disabled. Set `allow_code_execution=True` to run evaluation."
                )
            else:
                os.environ["HF_ALLOW_CODE_EVAL"] = "1"  # Allow code execution (sandboxed)

                logger.info("[INFO] Starting code evaluation...")

                pass_at_k, raw_results = compute_code_eval(
                    references=all_references,
                    predictions=all_generations,
                    k=self.generation_eval_k,
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
                    logger.info(f"[INFO] pass@k metrics saved to {eval_path}")

                # Save raw results for analysis
                raw_results_path = os.path.join(eval_dir, "raw_results.jsonl")
                with jsonlines.open(raw_results_path, mode="w") as writer:
                    for task_id, results in raw_results.items():
                        for completion_id, result in results:
                            writer.write({
                                "task_id": task_id,
                                "completion_id": completion_id,
                                **result,
                                "generation": all_generations[task_id][
                                    completion_id],
                                "reference": all_references[task_id],
                            })
                    logger.info(
                        f"[INFO] Raw evaluation results saved to {raw_results_path}")

                logger.info("[INFO] Generations saved to %s", gen_path)
        return



