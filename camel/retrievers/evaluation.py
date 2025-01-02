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
from typing import Callable, Dict, List, Optional

import numpy as np
from datasets import Dataset  # type: ignore[import]
from ragas import evaluate  # type: ignore[import]
from ragas.metrics import (  # type: ignore[import]
    context_relevancy,
    answer_relevancy,
    faithfulness,
)
from sklearn.metrics import roc_auc_score  # type: ignore[import]

"""
This implementation is based on ragas and ragbench paper and code.
"""


class RagasFields:
    INPUT_CONTEXT = "contexts"
    INPUT_QUESTOIN = "question"
    INPUT_ANSWER = "answer"


def rmse(
    input_trues: List[float], input_preds: List[float]
) -> Optional[float]:
    """
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
    """
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


def annotate_dataset(
    dataset: Dataset,
    context_call: Optional[Callable[[Dict], List[str]]],
    answer_call: Optional[Callable[[Dict], str]],
) -> Dataset:
    """
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


def ragas_evaluate_dataset(
    dataset: Dataset,
    contexts_field_name: Optional[str],
    answer_field_name: Optional[str],
    metrics_to_evaluate: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
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


def ragas_benchmark(
    dataset: Dataset,
    context_call: Optional[Callable[[Dict], List[str]]],
    answer_call: Optional[Callable[[Dict], str]],
) -> Dict[str, Optional[float]]:
    """
    Annotate the dataset and evaluate it using RAGAS metrics.
    """
    annotated_dataset = annotate_dataset(dataset, context_call, answer_call)
    evaluated_dataset = ragas_evaluate_dataset(
        annotated_dataset,
        contexts_field_name=RagasFields.INPUT_CONTEXT
        if context_call
        else None,
        answer_field_name=RagasFields.INPUT_ANSWER if answer_call else None,
    )
    metrics = ragas_calculate_metrics(
        evaluated_dataset,
        pred_context_relevance_field="context_relevancy"
        if context_call
        else None,
        pred_faithfulness_field="faithfulness" if answer_call else None,
    )
    return metrics
