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
from typing import Any, Dict, Optional


class BaseLoader(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        r"""Common configuration initialization.
        Args:
            config: A configuration object or dictionary.
        """
        self.config = config if config is not None else {}

    @abstractmethod
    def load(self, source, **kwargs):
        r"""Main abstract method for loading data.
        Args:
            source: The data source (e.g., file path, URL).
            **kwargs: Additional keyword arguments for loading data.

        Returns:
            Loaded data.
        """
        pass

    @property
    @abstractmethod
    def supported_formats(self):
        """
        Property to declare supported formats.

        Returns:
            A list or set of supported data formats.
        """
        pass
