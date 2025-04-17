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
        eval_result = {}
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

            docs = [v["text"] for v in self.corpus.values()]
            doc_id_map = {v["text"]: k for k, v in self.corpus.items()}

            # Force all documents to be stored in a single vector collection.
            # This prevents AutoRetriever from generating a separate collection for each document.
            auto_retriever._collection_name_generator = lambda \
                x: "humaneval_collection"

            # Initialize the vector index once with all documents.
            # Subsequent retrievals will reuse this collection without re-embedding.
            auto_retriever.run_vector_retriever(query="dummy", contents=docs,
                                                top_k=1)

            retrieval_results = {}

            # Prepare output directory
            output_dir = os.path.join(self.save_path, "retrieval")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir,
                                       f"{self.task}_retrieved_docs.jsonl")
            metrics_path = os.path.join(output_dir,
                                        f"{self.task}_retrieval_metrics.json")


            with jsonlines.open(output_path, mode='w') as writer:
                for query_id, query_text in tqdm(self.queries.items()):
                    result = auto_retriever.run_vector_retriever(
                        query=query_text,
                        contents=docs,  # Reuses the existing vector index
                        top_k=10,
                        return_detailed_info=True
                    )
                    doc_entries = []
                    scores = {}

                    for item in result["Retrieved Context"]:
                        doc_text = item["text"]
                        doc_id = doc_id_map.get(doc_text)
                        if doc_id is None:
                            continue
                        scores[doc_id] = item.get("similarity score", 0.0)
                        doc_entries.append({
                            "doc_id": doc_id,
                            "text": doc_text,
                            "title": self.corpus[doc_id].get("title", ""),
                            "similarity": item.get("similarity score", 0.0)
                        })

                    # Accumulate retrieval scores for evaluation
                    retrieval_results[query_id] = scores

                    # Stream write one record per query
                    writer.write({
                        "task_id": query_id,
                        "docs": doc_entries
                    })

                    # Evaluate using BEIR
                    from beir.retrieval.evaluation import EvaluateRetrieval
                    retriever = EvaluateRetrieval(model=None,
                                                  score_function="dot")
                    k_values = [1, 5, 10]
                    ndcg, _map, recall, precision = retriever.evaluate(
                        self.qrels, retrieval_results, k_values)
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

                if self.run_mode in ["generate", "retrieve_generate"]:
                    logger.info("[INFO] Generation step not yet implemented.")

        if self.run_mode in ["generate", "retrieve_generate"]:
            logger.info("[INFO] Starting generation...")
            # TODO: Implement generation + save + evaluation

            # Load retrieval docs if needed
            retrieval_docs = {}
            if self.run_mode == "retrieve_generate":
                retrieved_path = os.path.join(self.save_path, "retrieval",
                                              f"{self.task}_retrieved_docs.jsonl")
                with jsonlines.open(retrieved_path, mode='r') as reader:
                    for obj in reader:
                        retrieval_docs[obj["task_id"]] = obj["docs"]
            generations = []
            for task_id, prompt in tqdm(self.queries.items()):
                context = ""
                if self.run_mode == "retrieve_generate":
                    docs = retrieval_docs.get(task_id, [])
                    context = "\n\n".join([doc["text"] for doc in docs])
                full_prompt = f"{context}\n\n{prompt}" if context else prompt

                response = agent.generate(
                    [BaseMessage(role="user", content=full_prompt)])
                generations.append({
                    "task_id": task_id,
                    "prompt": full_prompt,
                    "generation": response.msg.content
                })

                # Save generations
            generation_dir = os.path.join(self.save_path, "generation")
            os.makedirs(generation_dir, exist_ok=True)
            gen_path = os.path.join(generation_dir,
                                    f"{self.task}_generations.jsonl")
            save_file_jsonl(generations, gen_path)
            logger.info("[INFO] Generations saved to %s", gen_path)

            # Evaluate generations
            logger.info("[INFO] Evaluating generation results...")
            generation_metrics = evaluate_humaneval_completion(generations)
            metrics_path = os.path.join(generation_dir,
                                        f"{self.task}_metrics.json")
            with open(metrics_path, "w") as f:
                json.dump(generation_metrics, f, indent=2)
            logger.info("[INFO] Generation metrics saved to %s", metrics_path)

        return



