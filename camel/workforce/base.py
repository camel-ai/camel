# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from abc import ABC, abstractmethod
from typing import Any

from camel.workforce.task_channel import TaskChannel


class BaseNode(ABC):
    def __init__(self, description: str) -> None:
        self.node_id = str(id(self))
        self.description = description
        # every node is initialized to use its own channel
        self._channel: TaskChannel = TaskChannel()
        self._running = False

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        """Resets the node to its initial state."""
        raise NotImplementedError()

    @abstractmethod
    def set_channel(self, channel: TaskChannel):
        r"""Sets the channel for the node."""

    @abstractmethod
    async def _listen_to_channel(self):
        r"""Listens to the channel and handle tasks. This method should be
        the main loop for the node.
        """

    @abstractmethod
    async def start(self):
        r"""Start the node."""

    @abstractmethod
    def stop(self):
        r"""
        Stop the node.
        """
