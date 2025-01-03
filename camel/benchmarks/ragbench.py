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

import logging

from camel.retrievers import AutoRetriever
from typing import Callable, Dict, List, Literal, Optional

import numpy as np
from datasets import Dataset  # type: ignore[import]
from ragas import evaluate  # type: ignore[import]
from ragas.metrics import (  # type: ignore[import]
    context_relevancy,
    faithfulness,
)
from sklearn.metrics import roc_auc_score  # type: ignore[import]

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from datasets import load_dataset

logger = logging.getLogger(__name__)

def annotate_dataset(
    dataset: Dataset,
    context_call: Optional[Callable[[Dict], List[str]]],
    answer_call: Optional[Callable[[Dict], str]],
) -> Dataset:
    r"""
    Annotate the dataset by adding context and answers using the provided
    functions.
    """

    def process_example(example: Dict) -> Dict:
        if context_call:
            example["contexts"] = context_call(example)
        if answer_call:
            example["answer"] = answer_call(example)
        return example

    return dataset.map(process_example)

class RagasFields:
    INPUT_CONTEXT = "contexts"
    INPUT_QUESTOIN = "question"
    INPUT_ANSWER = "answer"


def rmse(
    input_trues: List[float], input_preds: List[float]
) -> Optional[float]:
    r"""
    Calculate Root Mean Squared Error (RMSE) between input ground truth
    (`trues`) and predictions (`preds`)
    """
    if len(input_trues) != len(input_preds):
        return None

    trues = np.array(input_trues)
    preds = np.array(input_preds, dtype=float)

    # Ignore Nulls in predictions
    eval_idx = ~np.isnan(preds)
    trues = trues[eval_idx]
    preds = preds[eval_idx]

    return np.sqrt(np.mean((preds - trues) ** 2))


def auroc(trues: List[bool], preds: List[float]) -> float:
    r"""
    Calculate Area Under Reciever Operator Characteristic Curve (AUROC) between
     input ground truth (`trues`) and predictions (`preds`)
    """
    eval_idx = ~np.isnan(preds)
    return roc_auc_score(trues[eval_idx], preds[eval_idx])


def ragas_calculate_metrics(
    dataset: Dataset,
    pred_context_relevance_field: Optional[str],
    pred_faithfulness_field: Optional[str],
    metrics_to_evaluate: Optional[List[str]] = None,
    ground_truth_context_relevance_field: str = "relevance_score",
    ground_truth_faithfulness_field: str = "adherence_score",
) -> Dict[str, Optional[float]]:
    calculated_metrics: Dict[str, Optional[float]] = {}
    if metrics_to_evaluate is None:
        metrics_to_evaluate = ["context_relevancy", "faithfulness"]
    if "context_relevancy" in metrics_to_evaluate:
        trues_relevance = dataset[ground_truth_context_relevance_field]
        preds_relevance = dataset[pred_context_relevance_field]
        calculated_metrics["relevance_rmse"] = rmse(
            trues_relevance, preds_relevance
        )

    if "faithfulness" in metrics_to_evaluate:
        trues_hallucination = ~np.array(
            dataset[ground_truth_faithfulness_field]
        )
        preds_hallucination = 1 - np.array(
            dataset[pred_faithfulness_field], dtype=float
        )
        calculated_metrics["hallucination_auroc"] = auroc(
            trues_hallucination.tolist(), preds_hallucination.tolist()
        )

    return calculated_metrics


def ragas_evaluate_dataset(
    dataset: Dataset,
    contexts_field_name: Optional[str],
    answer_field_name: Optional[str],
    metrics_to_evaluate: Optional[List[str]] = None,
) -> Dict[str, float]:
    r"""
    Evaluate the dataset using RAGAS metrics for context relevancy and
    faithfulness.
    """
    if metrics_to_evaluate is None:
        metrics_to_evaluate = ["context_relevancy", "faithfulness"]
    if (
        contexts_field_name
        and contexts_field_name != RagasFields.INPUT_CONTEXT
    ):
        dataset = dataset.rename_column(
            contexts_field_name, RagasFields.INPUT_CONTEXT
        )
    if answer_field_name and answer_field_name != RagasFields.INPUT_ANSWER:
        dataset = dataset.rename_column(
            answer_field_name, RagasFields.INPUT_ANSWER
        )

    # Evaluate the dataset with RAGAS
    metrics = []
    if "context_relevancy" in metrics_to_evaluate:
        metrics.append(context_relevancy)
    if "faithfulness" in metrics_to_evaluate:
        metrics.append(faithfulness)
    ragas_result = evaluate(dataset, metrics=[context_relevancy, faithfulness])

    ragas_df = ragas_result.to_pandas()
    annotated_dataset = Dataset.from_pandas(ragas_df)

    return annotated_dataset


class RAGBenchBenchmark(BaseBenchmark):
    r"""RAGBench Benchmark evaluates the Rag performance.
    <https://huggingface.co/datasets/rungalileo/ragbench>.

    Args:
        save_to (str): The file to save the results.
        subset (str, optional): The subset to use.
            (default: :obj:`"hotpotqa"`)
        split (str, optional): The split to use.
            (default: :obj:`"test"`).
    """
    def __init__(
        self,
        subset: str = "hotpotqa",
        split: str = "test",
    ):
        r"""Initialize the APIBench benchmark.

        Args:
            save_to (str): The file to save the results.
            subset (str, optional): The subset to use.
                (default: :obj:`"hotpotqa"`)
            split (str, optional): The split to use.
                (default: :obj:`"test"`).
        """
        super().__init__("ragbench")

        self.subset = subset
        self.split = split
        self.dataset = None


    def download(self):
        r"""Download the APIBench dataset."""

        self.dataset = load_dataset("rungalileo/ragbench", self.subset, split=self.split)

    def load(self, force_download: bool = False):
        r"""Load the RAGBench Benchmark dataset.
        Args:
            force_download (bool, optional): Whether to force
                download the data. (default: :obj:`False`)
        """
        if force_download:
            logger.info("Force downloading data.")
            self.download()

    def run(
            self, 
    ) -> Dict[str, Optional[float]]:
        
        auto_retriever = AutoRetriever()
        def context_call(example):
            retrieved_info = auto_retriever.run_vector_retriever(
                query=example['question'],
                contents=example['documents'],
                top_k=1,
                return_detailed_info=True,
                similarity_threshold=0.5,
            )
            return [c['text'] for c in retrieved_info['Retrieved Context']]


        def answer_call(example):
            user_msg = str(example)
            assistant_sys_msg = """You are a helpful assistant to answer question,
                I will give you the Original Query and Retrieved Context,
                answer the Original Query based on the Retrieved Context,
                if you can't answer the question just say I don't know."""
            agent = ChatAgent(assistant_sys_msg)
            assistant_response = agent.step(user_msg)
            return assistant_response.msg.content

        # Annotate the dataset
        annotated_ds = annotate_dataset(self.dataset, context_call, answer_call)

        evaluated_ds = ragas_evaluate_dataset(
            annotated_ds,
            contexts_field_name="contexts",
            answer_field_name="answer",
            metrics_to_evaluate=["context_relevancy", "faithfulness"]
        )

        # Calculate metrics
        # See https://arxiv.org/abs/2407.11005 for more details 
        # on the metrics, right now only context_relevancy and
        # faithfulness are supported
        calculated_metrics = ragas_calculate_metrics(
            evaluated_ds,
            pred_context_relevance_field="context_relevancy",
            pred_faithfulness_field="faithfulness",
        )

        return calculated_metrics
