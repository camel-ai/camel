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
from typing import Dict, List

from camel.models.reward import BaseRewardModel


class Evaluator:
    r"""Evaluator class to evaluate messages using a reward model and filter
    data based on the scores.

    Args:
        reward_model (BaseRewardModel): A reward model to evaluate messages.
    """

    def __init__(self, reward_model: BaseRewardModel):
        self.reward_model = reward_model

    def evaluate(self, messages: List[Dict[str, str]]) -> Dict[str, float]:
        r"""Evaluate the messages using the reward model.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        scores = self.reward_model.evaluate(messages)
        return scores

    def filter_data(
        self, messages: List[Dict[str, str]], thresholds: Dict[str, float]
    ) -> bool:
        r"""Filter messages based on the scores.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.
            thresholds (Dict[str, float]): A dictionary mapping score types to
                their values.

        Returns:
            bool: A boolean indicating whether the messages pass the filter.
        """
        scores = self.evaluate(messages)
        for score_type, threshold in thresholds.items():
            if score_type not in scores:
                raise ValueError(f"Score type {score_type} not found.")
            if scores.get(score_type, 0) < threshold:
                return False
        return True
