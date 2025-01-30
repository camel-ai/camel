import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

import pandas as pd
from datasets import load_dataset
from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.responses.agent_responses import ChatAgentResponse

logger = logging.getLogger(__name__)

class GSM8KBenchmark(BaseBenchmark):
    """Benchmark for evaluating ChatAgents on the GSM8K dataset from Hugging Face Hub."""

    DATASET_NAME = "gsm8k"
    DATASET_REPO = "openai/gsm8k"

    def __init__(self, data_dir: str, save_to: str, processes: int = 1):
        """Initialize the GSM8K Benchmark."""
        super().__init__(name="GSM8K", data_dir=data_dir, save_to=save_to, processes=processes)
        self._data: Dict[str, List[Dict[str, Any]]] = {}

    def download(self) -> "GSM8KBenchmark":
        """Ensures the dataset is available. Hugging Face Datasets manages caching automatically."""
        logger.info("Ensuring GSM8K dataset is downloaded...")
        _ = load_dataset(self.DATASET_REPO, 'main', cache_dir=str(self.data_dir)
)
        logger.info("GSM8K dataset is ready.")
        return self

    def load(self, force_download: bool = False) -> "GSM8KBenchmark":
        """Loads the GSM8K dataset, optionally forcing a re-download."""
        logger.info("Loading GSM8K dataset...")

        dataset = load_dataset(
            self.DATASET_REPO,
            'main',
            cache_dir=str(self.data_dir),
            download_mode="force_redownload" if force_download else "reuse_dataset_if_exists"
        )

        self._data = {
            "train": dataset["train"].to_pandas().to_dict(orient="records"),
            "test": dataset["test"].to_pandas().to_dict(orient="records"),
        }
        return self

    @property
    def valid(self) -> List[Dict[str, Any]]:
        """GSM8K does not have a validation set; return an empty list."""
        return []

    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"] = "test",
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> "GSM8KBenchmark":
        """Runs the GSM8K benchmark on a given ChatAgent."""
        logger.info(f"Running GSM8K benchmark on {on} set...")

        if on == "valid":
            logger.warning("GSM8K does not have a validation set. Skipping run.")
            return self

        if on not in ["train", "test"]:
            raise ValueError(f"Invalid dataset split '{on}'. Use 'train', 'valid' (empty), or 'test'.")

        if not self._data:
            self.load()

        data = self._data[on].copy()

        #TODO: Make seed controllable if randomize = True
        if randomize:
            import random
            random.shuffle(data)

        if subset:
            data = data[:subset]

        df = pd.DataFrame(data)
        df["expected_answer"] = self._preprocess_answers(df["answer"])

        df["model_response"] = df["question"].apply(lambda q: agent.step(q))

        df["correct"] = df.apply(lambda row: self._evaluate_response(row["model_response"], row["expected_answer"]), axis=1)

        self._results = df.to_dict(orient="records")  # Convert back to list of dicts for compatibility
        self._save_results()

        return self

    def _preprocess_answers(self, raw_answers: pd.Series) -> pd.Series:
        """Extracts numeric answers in bulk using vectorized regex."""
        return raw_answers.str.extract(r"####\s*(-?\d+)")[0]

    def _save_results(self):
        """Saves results to a JSON file."""
        #TODO: Find better format to save results in.
        if self._results:
            results_path = Path(self.save_to) / Path("gsm8k_results.json")
            with open(results_path, "w") as f:
                json.dump(self._results, f, indent=2)
            logger.info(f"Results saved to {results_path}")

    def _evaluate_response(self, response: ChatAgentResponse, expected_answer: str) -> bool:
        """Evaluate correctness of response (currently just syntactical)."""
        # TODO: Make symbolic, use something like HF math-verify
        response_str = response.msgs[0].content
        return response_str == expected_answer
