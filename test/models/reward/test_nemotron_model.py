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

from unittest.mock import MagicMock, patch

import pytest

from camel.models.reward import NemotronRewardModel
from camel.types import ModelType

pytestmark = pytest.mark.heavy_dependency


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.NVIDIA_NEMOTRON_340B_REWARD,
    ],
)
@patch("camel.models.reward.nemotron_model.OpenAI")
def test_nemotron_reward_model(mock_openai, model_type: ModelType):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    model = NemotronRewardModel(model_type)
    assert model.model_type == model_type
    assert model._client == mock_client


@pytest.mark.model_backend
@patch("camel.models.reward.nemotron_model.OpenAI")
def test_nemotron_reward_model_evaluate(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    model = NemotronRewardModel(ModelType.NVIDIA_NEMOTRON_340B_REWARD)
    messages = [{"role": "user", "content": "Hello"}]
    mock_response = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(
        model, "_parse_scores", return_value={"helpfulness": 0.9}
    ):
        scores = model.evaluate(messages)
        assert scores == {"helpfulness": 0.9}
        mock_client.chat.completions.create.assert_called_once_with(
            messages=messages, model=ModelType.NVIDIA_NEMOTRON_340B_REWARD
        )


@pytest.mark.model_backend
def test_nemotron_reward_model_get_scores_types():
    model = NemotronRewardModel(ModelType.NVIDIA_NEMOTRON_340B_REWARD)
    score_types = model.get_scores_types()
    assert score_types == [
        "helpfulness",
        "correctness",
        "coherence",
        "complexity",
        "verbosity",
    ]


@pytest.mark.model_backend
def test_nemotron_reward_model_parse_scores():
    model = NemotronRewardModel(ModelType.NVIDIA_NEMOTRON_340B_REWARD)
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            logprobs=MagicMock(
                content=[MagicMock(token="helpfulness", logprob=0.9)]
            )
        )
    ]

    scores = model._parse_scores(mock_response)
    assert scores == {"helpfulness": 0.9}
