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

from typing import Any, Dict, List, Optional

from pydantic import Field

from camel.datasets.base import BaseDataset, DataPoint


class RNASeqDataPoint(DataPoint):
    r"""A data point containing RNA-seq analysis information.

    Attributes:
        expression_data (Dict[str, float]): Gene expression values
        differential_expression (Dict[str, Any]): Differential expression results
        pathway_analysis (Optional[Dict[str, Any]]): Pathway analysis results
        quality_metrics (Dict[str, float]): RNA-seq quality metrics
        experimental_design (Dict[str, Any]): Experimental design info
    """

    expression_data: Dict[str, float] = Field(
        ..., description="Gene expression values"
    )
    differential_expression: Dict[str, Any] = Field(
        ..., description="Differential expression results"
    )
    pathway_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Pathway analysis results"
    )
    quality_metrics: Dict[str, float] = Field(
        default_factory=dict, description="RNA-seq quality metrics"
    )
    experimental_design: Dict[str, Any] = Field(
        default_factory=dict, description="Experimental design info"
    )


class RNASeqDataset(BaseDataset):
    r"""Dataset for RNA-seq analysis tasks.

    This dataset handles RNA-seq data points and supports:
    1. Loading raw count data
    2. Differential expression analysis
    3. Pathway enrichment analysis
    4. Quality control metrics
    5. Experimental design tracking
    """

    def __init__(
        self,
        data_points: List[RNASeqDataPoint],
        cache_dir: Optional[str] = None,
        max_cache_size: int = int(1e9),
        preload: bool = False,
        shuffle: bool = True,
        **kwargs,
    ):
        r"""Initialize the RNA-seq dataset.

        Args:
            data_points: List of RNA-seq data points
            cache_dir: Directory to cache dataset files
            max_cache_size: Maximum cache size in bytes
            preload: Whether to preload dataset into memory
            shuffle: Whether to shuffle dataset on load
            **kwargs: Additional dataset parameters
        """
        super().__init__(
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
            preload=preload,
            shuffle=shuffle,
            **kwargs,
        )
        self._data_points = data_points

    def __len__(self) -> int:
        r"""Return the number of data points."""
        return len(self._data_points)

    def __getitem__(self, idx: int) -> RNASeqDataPoint:
        r"""Get a data point by index.

        Args:
            idx: Index of the data point

        Returns:
            The RNA-seq data point at the given index

        Raises:
            IndexError: If idx is out of bounds
        """
        if idx < 0 or idx >= len(self):
            raise IndexError(f"Index {idx} out of range")

        if idx in self._cache:
            return self._cache[idx]

        data_point = self._data_points[idx]
        if len(self._cache) < self._max_cache_size:
            self._cache[idx] = data_point

        return data_point

    def get_quality_summary(self) -> Dict[str, float]:
        r"""Get summary statistics of RNA-seq quality metrics.

        Returns:
            Dictionary of average quality metrics across dataset
        """
        summary = {}
        for point in self._data_points:
            for metric, value in point.quality_metrics.items():
                if metric not in summary:
                    summary[metric] = 0.0
                summary[metric] += value

        # Calculate averages
        for metric in summary:
            summary[metric] /= len(self)

        return summary