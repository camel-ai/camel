import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

import pandas as pd
import re
from datasets import load_dataset
from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.responses.agent_responses import ChatAgentResponse

logger = logging.getLogger(__name__)

class MATHBenchmark(BaseBenchmark):
    """Benchmark for evaluating ChatAgents on the MATH dataset from Hugging Face Hub."""

    DATASET_NAME = "math"
    DATASET_REPO = "EleutherAI/hendrycks_math"
    DATASET_CONFIGS = ['algebra', 'counting_and_probability', 'geometry', 'intermediate_algebra', 'number_theory', 'prealgebra', 'precalculus']

    def __init__(self, data_dir: str, save_to: str, processes: int = 1):
        """Initialize the MATH Benchmark."""
        super().__init__(name="MATH", data_dir=data_dir, save_to=save_to, processes=processes)
        self._data: Dict[str, List[Dict[str, Any]]] = {}

    def download(self) -> "MATHBenchmark":
        """Ensures the dataset is available. Hugging Face Datasets manages caching automatically."""
        logger.info("Ensuring MATH dataset is downloaded...")
        for config in self.DATASET_CONFIGS:
            _ = load_dataset(self.DATASET_REPO, config, cache_dir=str(self.data_dir))
        logger.info("MATH dataset is ready.")
        return self

    def load(self, force_download: bool = False) -> "MATHBenchmark":
        """Loads the MATH dataset, optionally forcing a re-download."""
        logger.info("Loading MATH dataset...")
        
        self._data = {"train": [], "test": []}
        
        for config in self.DATASET_CONFIGS:
            dataset = load_dataset(
                self.DATASET_REPO,
                config,
                cache_dir=str(self.data_dir),
                download_mode="force_redownload" if force_download else "reuse_dataset_if_exists"
            )
            self._data["train"].extend(dataset["train"].to_pandas().to_dict(orient="records"))
            self._data["test"].extend(dataset["test"].to_pandas().to_dict(orient="records"))
        
        return self

    @property
    def valid(self) -> List[Dict[str, Any]]:
        """MATH does not have a validation set; return an empty list."""
        return []

    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "test"] = "test",
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> "MATHBenchmark":
        """Runs the MATH benchmark on a given ChatAgent."""
        logger.info(f"Running MATH benchmark on {on} set...")

        if on not in ["train", "test"]:
            raise ValueError(f"Invalid dataset split '{on}'. Use 'train', 'valid' (empty), or 'test'.")

        if not self._data:
            self.load()

        data = self._data[on].copy()

        if randomize:
            import random
            random.shuffle(data)

        if subset:
            data = data[:subset]

        df = pd.DataFrame(data)
        df["expected_answer"] = self._preprocess_answers(df["solution"])

        df["model_response"] = df["problem"].apply(lambda q: agent.step(q).msgs[0].content)

        df["correct"] = df.apply(lambda row: self._evaluate_response(row["model_response"], row["expected_answer"]), axis=1)

        self._results = df.to_dict(orient="records")
        self._save_results()

        return self

    def _preprocess_answers(self, solutions: pd.Series) -> pd.Series:
        """
        Uses a stack-based PDA approach to extract the exact content inside `\boxed{}` 
        while ensuring proper nesting of `{}`.
        """

        def extract_boxed(text: str) -> str:
            """Extracts the content inside the first correctly balanced `\boxed{}`."""
            start_seq = r"\boxed{"
            stack = []  # Stack to track `{}` nesting
            content = []
            inside_boxed = False
            i = 0

            while i < len(text):
                if text[i:i+len(start_seq)] == start_seq and not inside_boxed:
                    # Found `\boxed{`, start capturing
                    inside_boxed = True
                    stack.append("{")
                    i += len(start_seq)  # Skip the `\boxed{`
                    continue

                if inside_boxed:
                    if text[i] == "{":
                        stack.append("{")
                    elif text[i] == "}":
                        stack.pop()  # Remove one `{` from stack
                        if not stack:  # If stack is empty, we've closed `\boxed{}` correctly
                            return "".join(content)
                    
                    content.append(text[i])

                i += 1

            raise ValueError("Couldn't extract value")

        return solutions.apply(extract_boxed)

    def _save_results(self):
        """Saves results to a JSON file, ensuring the directory exists."""
        if self._results:
            results_path = Path(self.save_to) / "math_results.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)

            with open(results_path, "w") as f:
                json.dump(self._results, f, indent=2)

            logger.info(f"Results saved to {results_path}")

    def _evaluate_response(self, response: str, expected_answer: str) -> bool:
        """Evaluate correctness of response (currently just syntactical)."""
        return response == expected_answer

# TODO: Extend evaluation to support symbolic correctness, Pass@k eval and majority voting.
