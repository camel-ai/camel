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
from typing import Any, Union

from camel.tasks.task import Task
from camel.utils.channel import Channel


class BaseWorkforce(ABC):
    def __init__(
        self, workforce_id: str, description: str, channel: Channel
    ) -> None:
        self.workforce_id = workforce_id
        self.description = description
        self.channel = channel

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        """Resets the workforce to its initial state."""
        pass

    async def send_message_receive_result(
        self, workforce_id, func_name, params
    ):
        """Sends a message to a specified workforce and waits for the result.

        Args:
            workforce_id: The ID of the workforce to which the message should
                be sent.
            func_name: The name of the function to be invoked.
            params: The parameters to be passed to the function.

        Returns:
            The result of the function execution.
        """
        message_id = await self.channel.write_to_receive_queue(
            workforce_id, func_name, params
        )
        excu_result = await self.channel.read_from_send_queue(message_id)
        return excu_result

    async def listening(self):
        """Continuously listens for incoming messages and processes them
        accordingly.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        while True:
            message_id, data = await self.channel.receive_from()
            Workforce_id, func_name, params = data
            if Workforce_id == self.workforce_id:
                if func_name == "process_task":
                    process_result = await self.process_task(params)
                    await self.channel.send_to((message_id, process_result))
                elif func_name == "assign_other_workforce":
                    assign_result = await self.process_task(params)
                    await self.channel.send_to((message_id, assign_result))
                elif func_name == "exit":
                    break
                else:
                    raise ValueError("Unsupported function.")

    @abstractmethod
    async def process_task(self, task: Task) -> Union[str, None]:
        pass
