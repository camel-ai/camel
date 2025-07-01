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
from typing import Any, Dict, Optional, Union


class BaseLoader(ABC):
    r"""Abstract base class for all data loaders in CAMEL.

    This class defines the common interface for loading data from various
    sources. Subclasses should be implement theproperty to indicate which
    file formats or data sources they support.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        r"""Initialize the loader with optional configuration.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary for the
                loader. The specific keys and values depend on the
                implementation. (default: :obj:`None`)
        """
        self.config = config or {}

    @abstractmethod
    def load(self, source: Union[str, Path, Any], **kwargs) -> Any:
        r"""Main abstract method for loading data.
        Args:
            source: The data source, which can be:
                - A string representing a file path or URL
                - A pathlib.Path object
                - Any other source type supported by the specific loader
                 implementation
            **kwargs: Additional keyword arguments for loading data.

        Returns:
            The loaded data, type depends on the specific loader
            implementation.
        """
        pass

    @property
    @abstractmethod
    def supported_formats(self):
        """Property to declare supported formats.

        Returns:
            A list or set of supported data formats.
        """
        pass
