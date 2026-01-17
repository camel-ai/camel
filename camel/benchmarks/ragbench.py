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

from typing import Any, Dict, List, Optional

from datasets import Dataset, load_dataset

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.benchmarks._utils import (
    LLMScoreEvaluator,
    build_context_relevance_prompt,
    build_faithfulness_prompt,
)
from camel.logger import get_logger
from camel.retrievers import AutoRetriever

logger = get_logger(__name__)


class RAGBenchBenchmark(BaseBenchmark):
    r"""RAGBench Benchmark for evaluating RAG performance.

    This benchmark uses the galileo-ai/ragbench dataset to evaluate
    retrieval-augmented generation (RAG) systems. It measures context
    relevancy and faithfulness metrics as described in
    https://arxiv.org/abs/2407.11005.

    Args:
        processes (int, optional): Number of processes for parallel processing.
            Defaults to 1.
    """

    DEFAULT_DATASET_NAME = "galileo-ai/ragbench"
    DEFAULT_SUBSET = "techqa"
    DEFAULT_SPLIT = "test"

    def __init__(self, processes: int = 1) -> None:
        super().__init__("ragbench", "", processes)
        self.dataset: Optional[Dataset] = None
        self.dataset_name: Optional[str] = None
        self.subset: Optional[str] = None
        self.split: Optional[str] = None

        self._agent: Optional[ChatAgent] = None
        self._auto_retriever: Optional[AutoRetriever] = None
        self._top_k: int = 1
        self._similarity_threshold: float = 0.5
        self._context_relevance_evaluator: Optional[LLMScoreEvaluator] = None
        self._faithfulness_evaluator: Optional[LLMScoreEvaluator] = None

    def download(self) -> None:
        r"""Download the RAGBench dataset using stored configuration.

        Raises:
            ValueError: If dataset configuration is not set via load().
            Exception: If dataset download fails.
        """
        if self.dataset_name is None:
            raise ValueError(
                "Dataset configuration not set. Please call load() first."
            )

        try:
            self.dataset = load_dataset(
                self.dataset_name, self.subset, split=self.split
            )
        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            raise

    def load(
        self,
        name: str = DEFAULT_DATASET_NAME,
        subset: Optional[str] = DEFAULT_SUBSET,
        split: Optional[str] = DEFAULT_SPLIT,
        force_download: bool = False,
    ) -> None:
        r"""Load the RAGBench dataset.

        Args:
            name (str): Dataset name/path. Defaults to "galileo-ai/ragbench".
            subset (Optional[str]): Dataset subset. Defaults to "techqa".
            split (Optional[str]): Dataset split. Defaults to "test".
            force_download (bool): Whether to force re-download. Defaults to False.
        """
        self.dataset_name = name
        self.subset = subset
        self.split = split

        if force_download or self.dataset is None:
            logger.info(
                "%s dataset: %s (subset=%s, split=%s)",
                "Force downloading" if force_download else "Loading",
                name,
                subset,
                split,
            )
            self.download()

    def _retrieve_contexts(self, example: Dict[str, Any]) -> List[str]:
        """Retrieve relevant contexts for a question."""
        retrieved_info = self._auto_retriever.run_vector_retriever(
            query=example['question'],
            contents=example['documents'],
            top_k=self._top_k,
            return_detailed_info=True,
            similarity_threshold=self._similarity_threshold,
        )
        return [c['text'] for c in retrieved_info['Retrieved Context']]

    def _generate_answer(self, example: Dict[str, Any]) -> str:
        """Generate answer using the agent."""
        prompt = f"Question: {example['question']}\n\nContexts: {example.get('contexts', [])}\n\nAnswer:"
        assistant_response = self._agent.step(prompt)
        return assistant_response.msg.content

    def _process_example(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single example: retrieve contexts and generate answer."""
        example["contexts"] = self._retrieve_contexts(example)
        example["answer"] = self._generate_answer(example)
        return example

    def _evaluate_example(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate faithfulness and context relevance."""
        result = {}

        # Evaluate faithfulness if answer exists
        if example.get("answer"):
            result["faithfulness"] = self._faithfulness_evaluator.evaluate(
                question=example["question"],
                contexts=example["contexts"],
                answer=example["answer"],
            )
        else:
            result["faithfulness"] = None

        # Evaluate context relevance
        result["context_relevance"] = (
            self._context_relevance_evaluator.evaluate(
                question=example["question"],
                contexts=example["contexts"],
            )
        )

        return result

    def run(
        self,
        pipeline_template: ChatAgent,
        auto_retriever: AutoRetriever,
    ) -> Dict[str, Any]:
        r"""Run the benchmark evaluation.

        Args:
            pipeline_template (ChatAgent): Chat agent for generating answers.
            auto_retriever (AutoRetriever): Retriever for finding relevant contexts.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total_samples: Total number of samples evaluated
                - faithfulness score: Average faithfulness score
                - context_relevance score: Average context relevance score

        Raises:
            ValueError: If dataset is not loaded.
        """
        if self.dataset is None:
            raise ValueError(
                "Dataset not loaded. Please call load() before run()."
            )

        self._agent = pipeline_template
        self._auto_retriever = auto_retriever

        self._context_relevance_evaluator = LLMScoreEvaluator(
            agent=pipeline_template,
            prompt_builder=build_context_relevance_prompt,
            default_score=0.0,
        )
        self._faithfulness_evaluator = LLMScoreEvaluator(
            agent=pipeline_template,
            prompt_builder=build_faithfulness_prompt,
            default_score=0.0,
        )

        logger.info(
            "Processing examples: retrieving contexts and generating answers"
        )
        processed_dataset = self.dataset.map(
            self._process_example,
            # num_proc=self.processes this works on jup notebook, check why pickling on py scripts
        )

        logger.info("Evaluating examples: computing metrics")
        evaluated_dataset = processed_dataset.map(
            self._evaluate_example,
            # num_proc=self.processes
        )

        faithfulness_scores = [
            x for x in evaluated_dataset["faithfulness"] if x is not None
        ]
        context_scores = [
            x for x in evaluated_dataset["context_relevance"] if x is not None
        ]

        results = {
            "total_samples": len(evaluated_dataset),
            "faithfulness_avg": (
                sum(faithfulness_scores) / len(faithfulness_scores)
                if faithfulness_scores
                else 0.0
            ),
            "context_relevance_avg": (
                sum(context_scores) / len(context_scores)
                if context_scores
                else 0.0
            ),
        }

        logger.info("Evaluation complete: %s", results)
        return results
