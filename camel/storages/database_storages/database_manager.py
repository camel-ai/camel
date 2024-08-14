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
from typing import Dict, List

from camel.messages import OpenAIMessage
from camel.messages.base import BaseMessage


# Generic database manager
class DatabaseManager(ABC):
    r"""Abstract base class for a database manager."""

    @abstractmethod
    def save_agent_infos(
        self, model_config_dict: Dict, model_type_value: str
    ) -> None:
        r"""Abstract method to save agent information to the database.
        Args:
            model_config_dict (Dict): A dictionary containing the agent's
            configuration settings.
            model_type_value (str): The type of model associated with the
            agent.
        """
        pass

    @abstractmethod
    def save_message_infos(
        self, base_message: BaseMessage, is_system_message: bool
    ) -> None:
        r"""Abstract method to save message information to the database.
        Args:
            base_message (BaseMessage): The system message of chat agent.
            is_system_message (bool): Indicates if the message is a system
            message.
        """
        pass

    @abstractmethod
    def save_memory_infos(
        self,
        openai_messages: List[OpenAIMessage],
        role_type: str,
        role_name: str,
    ) -> None:
        r"""Abstract method to save memory information to the database.
        Args:
            openai_messages (List[OpenAIMessage]): A list of OpenAI messages
            to be saved.
            role_type (str): The type of role associated with the messages.
            role_name (str): The name of the role associated with the messages.
        """
        pass
