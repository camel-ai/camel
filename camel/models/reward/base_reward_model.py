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
from typing import Dict, List, Optional, Union

from camel.types import ModelType


class BaseRewardModel(ABC):
    r"""Abstract base class for reward models. Reward models are used to
    evaluate messages and return scores based on different criteria.

    Subclasses should implement the 'evaluate' and 'get_scores_types' methods.
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        self.model_type = model_type
        self.api_key = api_key
        self.url = url

    @abstractmethod
    def evaluate(self, messages: List[Dict[str, str]]) -> Dict[str, float]:
        r"""Evaluate the messages and return scores based on different
        criteria.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        pass

    @abstractmethod
    def get_scores_types(self) -> List[str]:
        r"""Get the list of score types that the reward model can return.

        Returns:
            List[str]: A list of score types that the reward model can return.
        """
        pass
