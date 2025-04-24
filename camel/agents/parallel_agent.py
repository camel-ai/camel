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
import asyncio
from typing import Any, Dict

from camel.agents import ChatAgent
from camel.agents.base import BaseAgent


class ParallelAgent(BaseAgent):
    """
    A ParallelAgent that manages multiple sub-agents and
    executes their tasks concurrently.
    """

    def __init__(self, sub_agents: Dict[str, ChatAgent]) -> None:
        """
        Initializes the ParallelAgent with a dictionary of sub-agents.

        Args:
            sub_agents (Dict[str, BaseAgent]): A dictionary where keys are
                        agent names and values are BaseAgent instances.
        """
        self.agents = sub_agents

    async def step(self, input_message: Any) -> Dict[str, Any]:
        """
        Executes the `astep` method of all sub-agents concurrently.

        Args:
            input_message (Any): The input message to be processed
                                                by the sub-agents.

        Returns:
            Dict[str, Any]: A dictionary containing the results
                from each sub-agent,with agent names as keys.
        """
        tasks = [agent.astep(input_message) for agent in self.agents.values()]
        results = await asyncio.gather(*tasks)
        return {
            agent_name: result
            for agent_name, result in zip(self.agents.keys(), results)
        }

    def reset(self) -> None:
        """
        Resets all sub-agents to their initial state.
        """
        for agent in self.agents.values():
            agent.reset()
