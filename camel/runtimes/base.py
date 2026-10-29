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
import os
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from camel.toolkits import FunctionTool


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    r"""Determine the API key a runtime shares with its API server.

    Falls back to the ``CAMEL_RUNTIME_API_KEY`` environment variable, then to
    a freshly generated key, so that a runtime started without configuration
    still authenticates rather than leaving its tool endpoints open. An empty
    string is honoured as an explicit request to disable authentication.

    Args:
        api_key (Optional[str]): Explicitly supplied key, if any.
            (default: :obj:`None`)

    Returns:
        str: The key to present to the API server, or an empty string when
            authentication is disabled.
    """
    if api_key is None:
        api_key = os.environ.get("CAMEL_RUNTIME_API_KEY")
    if api_key is None:
        api_key = secrets.token_urlsafe(32)
    return api_key


def _auth_headers(api_key: str) -> Dict[str, str]:
    r"""Build the authentication headers for a runtime API request.

    Args:
        api_key (str): The key to present, or an empty string when
            authentication is disabled.

    Returns:
        Dict[str, str]: Headers to merge into the request.
    """
    return {"X-API-Key": api_key} if api_key else {}


class BaseRuntime(ABC):
    r"""An abstract base class for all CAMEL runtimes."""

    def __init__(self):
        super().__init__()

        self.tools_map = dict()

    @abstractmethod
    def add(
        self,
        funcs: Union[FunctionTool, List[FunctionTool]],
        *args: Any,
        **kwargs: Any,
    ) -> "BaseRuntime":
        r"""Adds a new tool to the runtime."""
        pass

    @abstractmethod
    def reset(self, *args: Any, **kwargs: Any) -> Any:
        r"""Resets the runtime to its initial state."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        r"""Releases resources (containers, processes, connections, etc.).

        Public part of the runtime lifecycle API: callers may call
        :meth:`cleanup` or use the runtime as a context manager
        (``with runtime:``) for deterministic teardown. Subclasses must
        implement this method.
        """
        pass

    def stop(self) -> "BaseRuntime":
        r"""Stops the runtime and releases resources. Calls :meth:`cleanup`.

        Returns:
            BaseRuntime: The current runtime (for chaining).
        """
        self.cleanup()
        return self

    def __enter__(self) -> "BaseRuntime":
        r"""Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        r"""Exit the context manager; ensures cleanup is called."""
        self.cleanup()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of all tools in the runtime."""
        return list(self.tools_map.values())
