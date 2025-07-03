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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union

from typing_extensions import Generic

from camel.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class LoaderResult(Generic[T]):
    r"""Container for load operation results."""

    content: Optional[T] = None
    success: bool = True
    error: Optional[Exception] = None
    source: Optional[Union[str, Path]] = None

    @property
    def failed(self) -> bool:
        r"""Check if the load operation failed.

        Returns:
            bool: True if the load operation failed, False otherwise.
        """
        return not self.success


class BaseLoader(ABC, Generic[T]):
    r"""Abstract base class for all data loaders in CAMEL.

    This class defines the common interface for loading data from various
    sources. Subclasses should implement the `_load_single` method to handle
    individual source loading.
    """

    @abstractmethod
    def _load_single(self, source: Union[str, Path], **kwargs) -> T:
        """Load data from a single source.

        Args:
            source: The data source to load from
            **kwargs: Additional keyword arguments for loading data.

        Returns:
            The loaded data of type T.

        Raises:
            Exception: If loading fails for any reason.
        """
        pass

    def load(
        self,
        source: Optional[
            Union[str, Path, List[Union[str, Path]], set[Union[str, Path]]]
        ] = None,
        **kwargs: Any,
    ) -> Dict[str, List[LoaderResult[T]]]:
        r"""Load data from one or multiple sources.

        Args:
            source: The data source(s) to load from. Can be:
                - A single path/URL (str or Path)
                - A list/set of paths/URLs
                (default: :obj:`None`)
            **kwargs: Additional keyword arguments for loading data.
                - raise_on_error: If True (default), raises an exception
                on first error. If False, returns failed results with error
                information.
                (default: :obj:`True`)

        Returns:
            A dictionary with a single key 'results' containing a list of
            LoaderResult objects. Each LoaderResult contains the loaded
            content (if successful) or error information.

        Raises:
            ValueError: If no sources are provided
            Exception: If loading fails for any source and raise_on_error
                is True
        """
        if not source:
            raise ValueError("At least one source must be provided")

        # Convert single source to list for uniform processing
        sources = [source] if isinstance(source, (str, Path)) else list(source)

        # Process all sources
        results: List[LoaderResult[T]] = []
        for src in sources:
            try:
                content = self._load_single(src, **kwargs)
                logger.debug(f"Successfully loaded source {src}")
                results.append(
                    LoaderResult(content=content, success=True, source=src)
                )
            except Exception as e:
                logger.error(f"Failed to load source {src}: {e}")
                if kwargs.get('raise_on_error', True):
                    raise ValueError(
                        f"Failed to load source {src}: {e}"
                    ) from e
                results.append(
                    LoaderResult(success=False, error=e, source=src)
                )

        return {'results': results}

    @property
    @abstractmethod
    def supported_formats(self) -> set[str]:
        r"""Get the set of supported file formats or data sources.

        Returns:
            A set of strings representing the supported formats/sources.
        """
        pass
