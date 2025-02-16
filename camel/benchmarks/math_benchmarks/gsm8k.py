import logging

from typing import Any, Dict, List, Union

import pandas as pd
from datasets import load_dataset
from camel.agents import ChatAgent
from camel.benchmarks import MathBenchmark, Mode

logger = logging.getLogger(__name__)


class GSM8KBenchmark(MathBenchmark):
    r"""Benchmark for evaluating ChatAgents on the GSM8K dataset 
    from Hugging Face Hub."""

    DATASET_NAME = "gsm8k"
    DATASET_REPO = "openai/gsm8k"
    QUESTION_COLUMN = "question"
    ANSWER_COLUMN = "answer"

    def __init__(self, data_dir: str, save_to: str, processes: int = 1):
        r"""Initialize the GSM8K Benchmark."""
        super().__init__(name="GSM8K", data_dir=data_dir, 
        save_to=save_to, processes=processes)
        self._data: Dict[str, List[Dict[str, Any]]] = {}

    def download(self) -> "GSM8KBenchmark":
        r"""Ensures the dataset is available. 
        Hugging Face Datasets manages caching automatically."""
        logger.info("Ensuring GSM8K dataset is downloaded...")
        _ = load_dataset(self.DATASET_REPO, 'main', 
        cache_dir=str(self.data_dir))
        logger.info("GSM8K dataset is ready.")
        return self

    def load(self, force_download: bool = False) -> "GSM8KBenchmark":
        r"""Loads the GSM8K dataset, optionally forcing a re-download."""
        logger.info("Loading GSM8K dataset...")

        dataset = load_dataset(
            self.DATASET_REPO,
            'main',
            cache_dir=str(self.data_dir),
            download_mode="force_redownload" if force_download 
            else "reuse_dataset_if_exists"
        )

        self._data = {
            "train": dataset["train"].to_pandas().to_dict(orient="records"),
            "test": dataset["test"].to_pandas().to_dict(orient="records"),
        }
        return self

    @property
    def valid(self) -> List[Dict[str, Any]]:
        r"""GSM8K does not have a validation set; return an empty list."""
        return []

    def _prepare_dataset(self, dataset: List[Dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(dataset)
        df["solution"] = df["answer"].str.extract(r"####\s*(-?\d+)")[0]
        return df

    def _generate_solutions(
        self,
        agent: ChatAgent,
        dataset: pd.DataFrame,
        mode: Mode
    ) -> Union[pd.DataFrame, Dict[str, List[Any]]]:
        r"""Generates model responses for the dataset."""
        dataset["answers"] = dataset["question"].apply(lambda q: 
        [agent.step(q).msgs[0].content for _ in range(mode.k)])

        return dataset

    def _preprocess_answers(self, raw_answers: pd.Series) -> pd.Series:
        r"""Extracts numeric answers in bulk using vectorized regex."""
        return raw_answers.str.extract(r"####\s*(-?\d+)")[0]
