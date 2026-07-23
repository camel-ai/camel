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
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class BaseLoader(ABC):
    r"""Abstract base class for all data loaders in CAMEL."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        r"""Initializes the loader with a standard configuration dictionary."""
        self.config = config or {}

    @abstractmethod
    def _load_single(
        self, source: Union[str, Path], **kwargs: Any
    ) -> Dict[str, Any]:
        r"""Load data from a single source.

        Args:
            source (Union[str, Path]): The data source to load from.
            **kwargs: Additional loader-specific parameters.

        Returns:
            Dict[str, Any]: A dictionary containing the loaded data.
        """
        pass

    def load(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
        **kwargs: Any,
    ) -> Dict[str, List[Dict[str, Any]]]:
        r"""Load data from one or multiple sources.

        Args:
            source (Union[str, Path, List[Union[str, Path]]]): The data
                source(s).
            **kwargs: Additional loader-specific parameters.

        Returns:
            Dict[str, List[Dict[str, Any]]]: A dictionary with a single key
                "contents" containing a list of loaded data.
        """
        if not source:
            raise ValueError("At least one source must be provided")

        sources = [source] if isinstance(source, (str, Path)) else list(source)
        results = []

        for i, src in enumerate(sources, 1):
            try:
                content = self._load_single(src, **kwargs)
                results.append(content)
            except Exception as e:
                raise RuntimeError(
                    f"Error loading source {i}/{len(sources)}: {src}"
                ) from e

        return {"contents": results}

    @property
    @abstractmethod
    def supported_formats(self) -> set[str]:
        r"""Get the set of supported file formats or data sources."""
        pass
