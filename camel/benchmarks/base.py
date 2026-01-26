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

import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.societies.role_playing import RolePlaying
from camel.societies.workforce.workforce import Workforce

logger = logging.getLogger(__name__)


class BaseBenchmark(ABC):
    r"""Base class for benchmarks.

    Attributes:
        name (str): Name of the benchmark.
        data_dir (str): Path to the data directory.
        save_to (str): Path to save the results.
        processes (int): Number of processes to use for parallel
            processing. :(default: :obj:`1`)
    """

    def __init__(self, name: str, data_dir: Optional[str], save_to: Optional[str], processes: int = 1):
        r"""Initialize the benchmark.

        Args:
            name (str): Name of the benchmark.
            data_dir (Optional[str]): Path to the data directory.
            save_to (str): Path to save the results.
            processes (int): Number of processes to use for parallel
                processing. :(default: :obj:`1`)

        """
        self.name = name
        self.data_dir = data_dir
        self.save_to = save_to
        self.processes = processes
        self._data: Dict[str, List[Dict[str, Any]]] = dict()
        self._results: List[Dict[str, Any]] = []

    @abstractmethod
    def download(self) -> "BaseBenchmark":
        r"""Download the benchmark data.
        Returns:
            BaseBenchmark: The benchmark instance.
        """
        pass

    @abstractmethod
    def load(
        self,
        name: str,
        subset: Optional[str],
        split: Optional[str],
        force_download: bool = False,
    ) -> "BaseBenchmark":
        r"""Load the benchmark data.

        Args:
            name (str): Name of the dataset or the github repo to be loaded.
            subset (Optional[str]): Name of the huggingface dataset subset to load.
            split (Optional[str]): Name of the split to load (train, test, validation)
            force_download (bool): Whether to force download the data.

        Returns:
            BaseBenchmark: The benchmark instance.
        """
        pass

    @property
    def train_data(self) -> List[Dict[str, Any]]:
        r"""Get the training data.

        Returns:
            List[Dict[str, Any]]: The training data.
        """
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data.get("train", [])

    @property
    def valid_data(self) -> List[Dict[str, Any]]:
        r"""Get the validation data.

        Returns:
            List[Dict[str, Any]]: The validation data.
        """
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data["valid", []]

    @property
    def test_data(self) -> List[Dict[str, Any]]:
        r"""Get the test data.

        Returns:
            List[Dict[str, Any]]: The test data.
        """
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data["test", []]

    def shuffle(self, seed: Optional[int] = 42) -> "BaseBenchmark":
        r"""Shuffle all data splits.

        Args:
            seed: Random seed for reproducibility.
                (default: :obj:`42`)

        Returns:
            BaseBenchmark: The benchmark instance.
        """
        random.seed(seed)
        logger.info(f"Shuffling data with seed: {seed}")

        for _, split_data in self._data.items():
            if split_data:
                random.shuffle(split_data)

        return self

    def subset(
        self,
        n: int,
        split: Optional[str] = None,
    ) -> "BaseBenchmark":
        r"""Take first N samples from data splits.

        Args:
            n: Number of samples to keep.
            split: Specific split to subset. If None, subsets all splits.
                (default: :obj:`None`)

        Returns:
            BaseBenchmark: The benchmark instance.
        """
        splits = [split] if split else self._data.keys()

        for split_name in splits:
            if self._data.get(split_name):
                self._data[split_name] = self._data[split_name][:n]
        return self

    @abstractmethod
    def run(
        self,
        pipeline_template: Union[ChatAgent, RolePlaying, Workforce],
        randomize: bool = False,
        subset: Optional[int] = None,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            pipeline_template (Union[ChatAgent, RolePlaying, Workforce]): The
                template agent or framework to use for processing examples.
                Can be a ChatAgent, RolePlaying, or Workforce instance that
                will be cloned for each example.
            randomize (bool): Whether to randomize the data.
            subset (int): The subset of the data to run the benchmark on.

        Returns:
            Dict[str, Any]: The results of the benchmark.
        """
        pass

    @property
    def results(self) -> List[Dict[str, Any]]:
        r"""Get the results.

        Returns:
            List[Dict[str, Any]]: The results.
        """
        return self._results
