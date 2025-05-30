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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union

from camel.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound='BaseBenchmark')


class RetrieverProtocol(Protocol):
    r"""Protocol for retriever components used in benchmarks.

    This protocol defines the interface that retriever components should
    implement to be compatible with benchmark frameworks.
    """

    def retrieve(
        self, query: str, contents: List[str], **kwargs: Any
    ) -> Dict[str, Any]:
        r"""Retrieve relevant content for the given query.

        Args:
            query (str): The query to retrieve content for.
            contents (List[str]): The list of contents to search in.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            Dict[str, Any]: The retrieved content and metadata.
        """
        ...

    def reset(self, **kwargs: Any) -> bool:
        r"""Reset the retriever state.

        Args:
            **kwargs (Any): Additional keyword arguments.

        Returns:
            bool: True if reset was successful, False otherwise.
        """
        ...


class EvalResult:
    r"""Standardized evaluation result model for benchmarks.

    This class provides a unified interface for storing and accessing
    benchmark evaluation results, supporting both aggregate metrics and
    detailed task-level results.

    Attributes:
        metrics (Dict[str, Union[int, float]]): Dictionary of metric names
            to their values (e.g., accuracy, score, etc.).
        details (List[Dict[str, Any]]): List of detailed results per item/task.
        metadata (Dict[str, Any]): Additional metadata about the evaluation
            (e.g., benchmark configuration, timestamps, etc.).
    """

    def __init__(
        self,
        metrics: Optional[Dict[str, Union[int, float]]] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        r"""Initialize the evaluation result.

        Args:
            metrics (Optional[Dict[str, Union[int, float]]]): Dictionary of
                metric names to their values.
            details (Optional[List[Dict[str, Any]]]): List of
                detailed results.
            metadata (Optional[Dict[str, Any]]): Additional metadata about
                the evaluation.
        """
        self.metrics = metrics or {}
        self.details = details or []
        self.metadata = metadata or {}

    def add_metric(self, name: str, value: Union[int, float]) -> None:
        r"""Add a metric to the result.

        Args:
            name (str): Name of the metric.
            value (Union[int, float]): Value of the metric.
        """
        self.metrics[name] = value

    def add_detail(self, item: Dict[str, Any]) -> None:
        r"""Add a detailed result item.

        Args:
            item (Dict[str, Any]): Detailed result data for an item.
        """
        self.details.append(item)

    def get_metric(self, name: str) -> Optional[Union[int, float]]:
        r"""Get a specific metric value.

        Args:
            name (str): Name of the metric.

        Returns:
            Optional[Union[int, float]]: The metric value if it exists.
        """
        return self.metrics.get(name)

    def to_dict(self) -> Dict[str, Any]:
        r"""Convert the result to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the result.
        """
        return {
            'metrics': self.metrics,
            'details': self.details,
            'metadata': self.metadata,
        }


class BaseBenchmark(ABC):
    r"""Base class for benchmarks.

    This class provides a flexible foundation for implementing various types
    of benchmarks. It supports different data loading mechanisms, evaluation
    patterns, and result formats to accommodate diverse benchmark requirements.

    Attributes:
        name (str): Name of the benchmark.
        data_dir (Optional[Path]): Suggested local path for data storage.
            Subclasses may use alternative mechanisms.
        save_to (Optional[str]): Path to save the results. Can be None if
            results are not saved to file.
        processes (int): Number of processes to use for parallel processing.
        retriever (Optional[RetrieverProtocol]): Optional retriever component
            for benchmarks that need retrieval functionality.
    """

    def __init__(
        self,
        name: str,
        data_dir: Optional[str] = None,
        save_to: Optional[str] = None,
        processes: int = 1,
        retriever: Optional[RetrieverProtocol] = None,
        **kwargs: Any,
    ):
        r"""Initialize the benchmark.

        Args:
            name (str): Name of the benchmark.
            data_dir (Optional[str]): Suggested local path for data storage.
                Subclasses may use alternative mechanisms. If provided and
                doesn't exist, will be created.
            save_to (Optional[str]): Path to save the results. Can be None
                if results are not saved to file.
            processes (int): Number of processes to use for parallel
                processing. (default: :obj:`1`)
            retriever (Optional[RetrieverProtocol]): Optional retriever
                for benchmarks that need retrieval functionality.
            **kwargs (Any): Additional keyword arguments for subclass-specific
                initialization parameters.
        """
        self.name = name
        self.data_dir = Path(data_dir) if data_dir else None
        self.save_to = save_to
        self.processes = processes
        self.retriever = retriever

        # Store additional kwargs for subclass flexibility
        self._init_kwargs = kwargs

        # Create data directory if specified and doesn't exist
        if self.data_dir:
            if not self.data_dir.exists():
                logger.info(
                    f"Data directory {self.data_dir} does not exist. "
                    "Creating it."
                )
                self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.data_dir.is_dir():
                raise NotADirectoryError(
                    f"Data directory {self.data_dir} is not a directory"
                )

        # Initialize internal data storage
        self._data: Dict[str, Any] = {}
        self._results: List[Dict[str, Any]] = []
        self._dataset: Optional[Any] = None

    @abstractmethod
    def download(self: T) -> T:
        r"""Download the benchmark data.

        Subclasses must implement their specific data acquisition logic.
        This could involve downloading from URLs, APIs, databases, etc.

        Returns:
            BaseBenchmark: The benchmark instance for method chaining.
        """
        pass

    def load(self: T, *args: Any, **kwargs: Any) -> T:
        r"""Load the benchmark data.

        Default implementation raises NotImplementedError. Subclasses should
        override this method to implement their specific data loading logic.
        The signature can vary based on subclass requirements.

        Args:
            *args: Variable positional arguments for specific parameters.
                Common patterns:
                - load(force_download=False) for simple benchmarks
                - load(level="level-1") for multi-level benchmarks
                - load(subset="hotpotqa") for dataset-based benchmarks
            **kwargs: Variable keyword arguments for specific parameters.

        Returns:
            BaseBenchmark: The benchmark instance for method chaining.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement their own load method with "
            "appropriate parameters for their specific requirements."
        )

    @abstractmethod
    def run(self, *args, **kwargs) -> EvalResult:
        r"""Run the benchmark evaluation.

        Subclasses must define their required arguments and return type.
        This method should handle the core evaluation logic.

        Args:
            *args: Variable positional arguments for specific parameters.
            **kwargs: Variable keyword arguments for specific parameters.
                Common patterns include:
                - agent: ChatAgent to evaluate
                - retriever/auto_retriever: For RAG benchmarks
                - on/split: Dataset split to run on
                - level: Difficulty level or task type
                - randomize: Whether to randomize data order
                - subset: Number of samples to evaluate

        Returns:
            EvalResult: Standardized evaluation result with metrics and
                detailed results.

        Examples:
            Different subclasses may have different signatures:

            # Simple agent-only benchmark
            result = benchmark.run(agent=my_agent, on="test")

            # RAG benchmark with retriever in run()
            result = benchmark.run(agent=my_agent, auto_retriever=my_retriever)

            # Multi-level benchmark
            result = benchmark.run(
                agent=my_agent,
                level="level-1",
                api_test_enabled=True
            )

            # Complex benchmark with multiple parameters
            result = benchmark.run(
                agent=my_agent,
                on="valid",
                level=[1, 2],
                randomize=True,
                subset=100
            )
        """
        raise NotImplementedError(
            "Subclasses should override this method to process results "
            "and return calculated metrics in a standardized format."
        )

    # Utility methods for common operations
    def get_data_split(self, split: str) -> List[Dict[str, Any]]:
        r"""Get data for a specific split.

        This is a helper method for benchmarks that use traditional
        train/valid/test splits.

        Args:
            split (str): The split name (e.g., "train", "valid", "test").

        Returns:
            List[Dict[str, Any]]: The data for the specified split.

        Raises:
            KeyError: If the split doesn't exist.
            ValueError: If data hasn't been loaded.
        """
        if not self._data:
            raise ValueError("Data not loaded. Call load() first.")

        if split not in self._data:
            available_splits = list(self._data.keys())
            raise KeyError(
                f"'{split}' not found. Available splits: {available_splits}"
            )

        return self._data[split]

    def filter_by_criteria(
        self, data: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        r"""Filter data based on specified criteria.

        This is a helper method for filtering tasks by level, type, etc.

        Args:
            data (List[Dict[str, Any]]): The data to filter.
            criteria (Dict[str, Any]): Filtering criteria.

        Returns:
            List[Dict[str, Any]]: Filtered data.
        """
        filtered_data = []
        for item in data:
            match = True
            for key, value in criteria.items():
                if key not in item:
                    match = False
                    break
                if isinstance(value, list):
                    if item[key] not in value:
                        match = False
                        break
                elif item[key] != value:
                    match = False
                    break
            if match:
                filtered_data.append(item)
        return filtered_data

    def apply_data_options(
        self,
        data: List[Dict[str, Any]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        r"""Apply common data processing options.

        Args:
            data (List[Dict[str, Any]]): The data to process.
            randomize (bool): Whether to randomize the data order.
            subset (Optional[int]): Number of samples to keep.

        Returns:
            List[Dict[str, Any]]: Processed data.
        """
        import random

        processed_data = data.copy()

        if randomize:
            random.shuffle(processed_data)

        if subset is not None:
            processed_data = processed_data[:subset]

        return processed_data

    @property
    def results(self) -> List[Dict[str, Any]]:
        r"""Get the results.

        Returns:
            List[Dict[str, Any]]: The results. Note that subclasses may
                manage results differently and override this property.
        """
        return self._results

    @property
    def dataset(self) -> Optional[Any]:
        r"""Get the external dataset (e.g., HuggingFace dataset).

        Returns:
            Optional[Any]: The external dataset if available.
        """
        return self._dataset

    def reset(self) -> None:
        r"""Reset the benchmark state.

        This method clears any cached results and resets internal state.
        Useful for running multiple evaluations or in RL training loops.
        """
        self._results = []

    def save_results(self, filepath: Optional[str] = None) -> None:
        r"""Save results to file.

        Args:
            filepath (Optional[str]): Path to save results. If None,
                uses self.save_to if available. (default: :obj:`None`)
        """
        import json
        import os

        save_path = filepath or self.save_to
        if not save_path:
            logger.warning("No save path specified. Results not saved.")
            return

        try:
            # Create directory if it doesn't exist
            os.makedirs(
                os.path.dirname(os.path.abspath(save_path)), exist_ok=True
            )

            with open(save_path, 'w', encoding='utf-8') as f:
                for result_item in self._results:
                    f.write(json.dumps(result_item, ensure_ascii=False) + '\n')
            logger.info(f"Results saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
