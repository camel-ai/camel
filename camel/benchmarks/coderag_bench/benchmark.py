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

from beir.retrieval.evaluation import EvaluateRetrieval
from beir.datasets.data_loader import GenericDataLoader
from camel.benchmarks.coderag_bench.generation_tasks import TASK_REGISTRY
import re

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
        super().__init__("coderag_bench", data_dir, save_to)
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



    def run(  # type: ignore[override, return]
            self,
            agent: ChatAgent,
            auto_retriever: Optional[AutoRetriever] = None, # TODO: Currently only supports canonical retriever. Add support for other retrieval types.
    )
        r"""Load the CodeRAG-Bench dataset.
            save benchmark result to files
            return evaluation result"""
        if self.corpus is None or self.queries is None or self.qrels is None or self.dataset is None:
            self.load()
        if self.run_mode in ["retrieve", "retrieve_generate"]:
            # path = os.path.join(self.datadir, "datasets")
            # os.makedirs(path, exist_ok=True)
            # os.makedirs(os.path.join(path, "humaneval"), exist_ok=True)
            # os.makedirs(os.path.join(path, "humaneval", "qrels"),
            #             exist_ok=True)
            self.queries, self.docs, self.qrels = document2code(self.dataset, split="test")
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

            if auto_retriever is None:
                raise ValueError(
                    "auto_retriever must be provided in retrieve or retrieve_generate mode")

            if self.retrieval_type != "canonical":
                raise NotImplementedError(
                    "Only canonical retrieval is supported for now.")

            # === Canonical Retrieval Logic ===
            logger.info("[INFO] Starting canonical retrieval...")


            docs = [v["text"] for v in self.corpus.values()]
            doc_id_map = {v["text"]: k for k, v in self.corpus.items()}

            # Force all documents to be stored in a single vector collection.
            # This prevents AutoRetriever from generating a separate collection for each document.
            auto_retriever._collection_name_generator = lambda _: f"{self.task}_collection"

            # Initialize the vector index once with all documents.
            # Subsequent retrievals will reuse this collection without re-embedding.
            auto_retriever.run_vector_retriever(query="dummy", contents=docs,
                                                top_k=1)

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
                    query_id = example["task_id"]
                    query_text = example["prompt"]

                    # Run retrieval using the shared vector index
                    result = auto_retriever.run_vector_retriever(
                        query=query_text,
                        contents=docs,
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

                    # Save scores for retrieval evaluation
                    retrieval_results[query_id] = scores

                    # Merge retrieved docs into the original sample and stream write
                    example_with_docs = dict(example)
                    example_with_docs["docs"] = doc_entries
                    writer.write(example_with_docs)

            self.dataset["test"] = load_dataset("json", data_files=output_path,
                                                split="train")
            # Evaluate using BEIR

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

        # ============================================
        # generation part
        if self.run_mode in ["generate", "retrieve_generate"]:
            logger.info("[INFO] Starting generation...")
            # TODO: Implement generation + save + evaluation

            generation_dir = os.path.join(self.save_to, "generation",
                                          self.task)
            os.makedirs(generation_dir, exist_ok=True)
            gen_path = os.path.join(generation_dir, "generations.json")

            # # Open retrieval results stream if needed
            # if self.run_mode == "retrieve_generate":
            #     retrieved_path = os.path.join(self.save_to, "retrieval",
            #                                   f"{self.task}_retrieved_docs.jsonl")
            #     retrieval_reader = jsonlines.open(retrieved_path, mode='r')
            # else:
            #     retrieval_reader = None


            with jsonlines.open(gen_path, mode='w') as writer:
                for data_i in tqdm(self.dataset["test"]): # data_i is equivalent to doc in <https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/tasks/humaneval.py>
                    prompt = data_i["prompt"]

                    # Build context from retrieved docs if available
                    docs = data_i.get("docs", [])
                    context = "\n\n".join(
                        doc["text"] for doc in docs[:10])  # Top-10

                    # Construct the final prompt for the agent
                    final_prompt = (
                            context +
                            '\n\nPlease complete the following function based on the example above:\n' +
                            '```python\n' +
                            prompt
                    )

                    # Run generation using the agent
                    response = agent.step(
                        [BaseMessage(role="user", content=final_prompt)])
                    generation = response.msg.content

                    # === Postprocess ===



                    # Stop words as defined in coderag-bench
                    stop_words = ["\nclass", "<file_sep>", "if __name__",
                                  "\nprint(", "\ndef"]

                    # Step 1: Extract code block from markdown if present
                    # Todo: this part of logic is adapted from extract_generation_code(), but the logic is simpler
                    # Todo: We might want to improve this part if the code generation is not as expected
                    matches = re.findall(r"```python\n(.*?)```", generation,
                                         re.DOTALL | re.IGNORECASE)
                    if matches:
                        generation = matches[0].strip()

                    # Step 2: Truncate generation at the first occurrence of any stop word
                    for stop_word in stop_words:
                        index = generation.find(stop_word)
                        if index != -1:
                            generation = generation[:index].strip()
                            break  # only cut at the first matched stop word

                    # Step 3: Add prompt back for evaluation (matches reference format)
                    generation = data_i["prompt"] + generation

                    # Save generation outputs to file
                    writer.write([generation])

                    # === Code Evaluation ===

                    # Get reference
                    test_func = data_i["test"]
                    entry_point = f"check({data_i['entry_point']})"
                    reference = "\n" + test_func + "\n" + entry_point

                    # evaluation


            logger.info("[INFO] Generations saved to %s", gen_path)

            #Todo: postprocessing + evaluation

        return



