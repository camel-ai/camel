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
import os
from typing import Dict, List, Optional, Union

from openai import OpenAI

from camel.models.reward import BaseRewardModel
from camel.types import ChatCompletion, ModelType
from camel.utils import api_keys_required


class NemotronRewardModel(BaseRewardModel):
    r"""Reward model based on the Nemotron model with OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        api_key (Optional[str], optional): The API key for authenticating
            with the model service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.

    Note:
        The Nemotron model does not support model config.
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        url = url or os.environ.get(
            "NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        super().__init__(model_type, api_key, url)
        self._client = OpenAI(
            timeout=180,
            max_retries=3,
            base_url=self.url,
            api_key=self.api_key,
        )

    @api_keys_required(
        [
            (None, "NVIDIA_API_KEY"),
        ]
    )
    def evaluate(self, messages: List[Dict[str, str]]) -> Dict[str, float]:
        r"""Evaluate the messages using the Nemotron model.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary format.

        Returns:
            Dict[str, float]:  A dictionary mapping score types to their
                values.
        """
        response = self._client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            model=self.model_type,
        )
        scores = self._parse_scores(response)
        return scores

    def get_scores_types(self) -> List[str]:
        r"""Get the list of score types that the reward model can return.

        Returns:
            List[str]: A list of score types that the reward model can return.
        """
        return [
            "helpfulness",
            "correctness",
            "coherence",
            "complexity",
            "verbosity",
        ]

    def _parse_scores(self, response: ChatCompletion) -> Dict[str, float]:
        r"""Parse the scores from the response.

        Args:
            response (ChatCompletion): A ChatCompletion object with the scores.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        try:
            choices = response.choices
            logprobs = (
                choices[0].logprobs.content
                if choices and choices[0].logprobs
                else None
            )
            scores = (
                {entry.token: entry.logprob for entry in logprobs if entry}
                if logprobs
                else {}
            )
            return scores
        except Exception as e:
            raise ValueError(f"Failed to parse scores: {e}")
