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
from typing import Any, Optional

from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import check_if_running


class BaseNode(ABC):
    r"""Base class for all nodes in the workforce.

    Args:
        description (str): Description of the node.
        node_id (Optional[str]): ID of the node. If not provided, it will
            be generated automatically. (default: :obj:`None`)
    """

    def __init__(
        self, description: str, node_id: Optional[str] = None
    ) -> None:
        self.node_id = node_id if node_id is not None else str(id(self))
        self.description = description
        self._channel: TaskChannel = TaskChannel()
        self._running = False

    @check_if_running(False)
    def reset(self, *args: Any, **kwargs: Any) -> Any:
        r"""Resets the node to its initial state."""
        self._channel = TaskChannel()
        self._running = False

    @abstractmethod
    def set_channel(self, channel: TaskChannel):
        r"""Sets the channel for the node."""
        pass

    @abstractmethod
    async def _listen_to_channel(self):
        r"""Listens to the channel and handle tasks. This method should be
        the main loop for the node.
        """
        pass

    @abstractmethod
    async def start(self):
        r"""Start the node."""
        pass

    @abstractmethod
    def stop(self):
        r"""Stop the node."""
        pass
