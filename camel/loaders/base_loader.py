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
from typing import Any, Dict, List, Union


class BaseLoader(ABC):
    r"""Abstract base class for all data loaders in CAMEL."""

    @abstractmethod
    def _load_single(self, source: Union[str, Path]) -> Any:
        r"""Load data from a single source.

        Args:
            source (Union[str, Path]): The data source to load from.

        Returns:
            Any: Loaded data by the source.
        """
        pass

    def load(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
    ) -> Dict[str, Any]:
        r"""Load data from one or multiple sources.

        Args:
            source (Union[str, Path, List[Union[str, Path]]]): The data source
                (s) to load from. Can be:
                - A single path/URL (str or Path)
                - A list of paths/URLs

        Returns:
            Dict[str, Any]: A dictionary of loaded data. If a single source
                is provided, the dictionary will contain a single item.

        Raises:
            ValueError: If no sources are provided
            Exception: If loading fails for any source
        """
        if not source:
            raise ValueError("At least one source must be provided")

        # Convert single source to list for uniform processing
        sources = [source] if isinstance(source, (str, Path)) else list(source)

        # Process all sources
        results = {}
        for i, src in enumerate(sources, 1):
            try:
                content = self._load_single(src)
                results[str(src)] = content
            except Exception as e:
                raise RuntimeError(
                    f"Error loading source {i}/{len(sources)}: {src}"
                ) from e

        return results

    @property
    @abstractmethod
    def supported_formats(self) -> set[str]:
        r"""Get the set of supported file formats or data sources.

        Returns:
            set[str]: A set of strings representing the supported formats/
            sources.
        """
        pass
