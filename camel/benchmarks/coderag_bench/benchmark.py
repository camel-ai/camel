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

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.messages import BaseMessage
from camel.retrievers.auto_retriever import AutoRetriever
from datasets import Dataset
logger = logging.getLogger(__name__)
from .utils import save_tsv_dict, save_file_jsonl

from beir.datasets.data_loader import GenericDataLoader

def document2code(data, split="test"):
    r"""Convert document to code. Helper function from Coderag-bench."""
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

def get_top_docs(results: dict, corpus: dict, task_id: str, topk: int = 10) -> list[str]:
    if task_id not in results: return []
    doc_scores = results[task_id]
    doc_scores_sorted = sorted(doc_scores.items(), key=lambda item: item[1], reverse=True)
    doc_scores_sorted = doc_scores_sorted[:topk]
    doc_code_snippets = [corpus[code_id] for code_id, score in doc_scores_sorted]
    return doc_code_snippets

class CodeRagBenchBenchmark(BaseBenchmark):
    r"""CodeRag-Bench Benchmark for evaluating RAG performance."""


    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
        task: Literal[
            "humaneval","mbpp","live_code_bench","ds1000", "odex","repoeval_repo","swebench_repo"
        ] = "humaneval",
        run_mode: Literal["retrieve", "generate", "retrieve_generate"] = "retrieve_generate",
        retrieval_type: Literal['canonical','open'] = "canonical",

    ) -> None:
        r"""Initialize the benchmark.

            Args:
                name (str): Name of the benchmark.
                data_dir (str): Path to the data directory.
                save_to (str): Path to save the results.
                processes (int): Number of processes to use for parallel
                    processing. :(default: :obj:`1`)

            """
        super().__init__("coderag_bench", data_dir, save_to, processes)
        self.task = task
        self.retrieval_type: retrieval_type
        self.run_mode = run_mode
        self.dataset: Optional[Dataset] = None
        self.corpus: Optional[dict] = None
        self.queries: Optional[dict] = None
        self.qrels: Optional[dict] = None


    def download(self):
        r"""Download and preprocess the CodeRag-Bench data.

        Returns:

        """
        if self.task == "humaneval":
            logger.info(f"[INFO] Downloading and processing dataset for task: {self.task}")
            dataset = datasets.load_dataset("openai_humaneval")
            #self.dataset = dataset
            path = os.path.join(self.datadir, "datasets")
            os.makedirs(path, exist_ok=True)
            os.makedirs(os.path.join(path, "humaneval"), exist_ok=True)
            os.makedirs(os.path.join(path, "humaneval","qrels"), exist_ok=True)
            queries, docs, qrels = document2code(dataset, split="test")
            save_file_jsonl(queries, os.path.join(path, "queries.jsonl"))
            save_file_jsonl(docs, os.path.join(path, "corpus.jsonl"))
            qrels_path = os.path.join(path, "qrels", "test.tsv")
            save_tsv_dict(qrels, qrels_path, ["query-id", "corpus-id", "score"])

            # create canonical file path if not existent yet
            os.makedirs(os.path.join(path,"canonical"), exist_ok=True)
            # Todo: Maybe later allow users to specify canonical file name
            canonical_file = os.path.join(path, "canonical", "humaneval_solutions.json")
            if not os.path.exists(canonical_file):
                canonical_solutions = []
                for doc in docs:
                    canonical_solutions.append([{
                        "text": doc["text"], "title": doc["title"]
                    }])
                canonical_dataset = dataset["test"].add_column("docs",
                                                               canonical_solutions)
                canonical_dataset.to_json(canonical_file)
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

        path = os.path.join(self.datadir, "datasets")
        self.corpus, self.queries, self.qrels = GenericDataLoader(
            data_folder=os.path.join(path, self.task)).load(split="test")

    def run(  # type: ignore[override, return]
            self,
            agent: ChatAgent,
            auto_retriever: Optional[AutoRetriever] = None, # TODO: Currently only supports canonical retriever. Add support for other retrieval types.
    )
        r"""Load the CodeRAG-Bench dataset.
            save benchmark result to files
            return evaluation result"""

        if self.run_mode in ["retrieve", "retrieve_generate"]:
            if auto_retriever is None:
                raise ValueError(
                    "auto_retriever must be provided in retrieve or retrieve_generate mode")

            if self.retrieval_type == "open":
                raise NotImplementedError("open retrieval not yet supported")

            # === Canonical Retrieval Logic ===
            logger.info("[INFO] Starting canonical retrieval...")
            if self.corpus is None or self.queries is None or self.qrels is None:
                self.load()
            results = auto_retriever.retrieve(corpus=corpus, queries=queries)

            def get_top_docs(results: Dict[str, Dict[str, float]],
                             corpus: Dict[str, Dict], task_id: str,
                             top_k: int):
                scores = results[task_id]
                top_doc_ids = sorted(scores.items(), key=lambda x: x[1],
                                     reverse=True)[:top_k]
                return [corpus[doc_id] for doc_id, _ in top_doc_ids]

            top_docs = {
                task_id: get_top_docs(results, corpus, task_id, top_k)
                for task_id in queries
            }

            # Save top docs for future eval or generation
            output_dir = os.path.join(self.save_path, "retrieval")
            os.makedirs(output_dir, exist_ok=True)
            save_file_jsonl([
                {"task_id": tid, "docs": docs} for tid, docs in
                top_docs.items()
            ], os.path.join(output_dir, f"{self.task}_retrieved_docs.jsonl"))

            logger.info("[INFO] Canonical retrieval completed.")
            return {"retrieval_done": True, "num_queries": len(queries)}

        elif self.run_mode == "generate":
            # === Generation-only logic ===
            logger.info("[INFO] Generation mode selected, skipping retrieval.")
            raise NotImplementedError("generate-only mode not implemented yet")

        else:
            raise ValueError(f"Unknown run_mode: {self.run_mode}")





