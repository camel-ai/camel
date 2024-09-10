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
# test_smol_model.py
import pytest

from camel.models.smollm_model import SmolLMModel
from camel.types import ChatCompletionUserMessageParam


@pytest.fixture
def smol_model():
    model_type = "HuggingFaceTB/SmolLM-360M-Instruct"
    model_config = {
        'max_new_tokens': 10,
        'temperature': 0.7,
        'top_p': 0.9,
        'top_k': 50,
        'do_sample': True,
    }
    return SmolLMModel(model_type=model_type, model_config_dict=model_config)


def test_model_initialization(smol_model):
    assert smol_model.model is not None, "Model not initialized correctly"
    assert (
        smol_model.tokenizer is not None
    ), "Tokenizer not initialized correctly"
    assert smol_model.device in [
        "cpu",
        "cuda",
        "mps",
    ], "Incorrect device selected"


def test_run_inference(smol_model):
    messages = [
        ChatCompletionUserMessageParam(
            role="user", content="What is the capital of France?"
        )
    ]

    response = smol_model.run(messages)

    assert response.model == smol_model.model_type, "Model ID does not match"
    assert isinstance(
        response.choices[0].message.content, str
    ), "Output should be a string"
    assert (
        len(response.choices[0].message.content) > 0
    ), "Model output is empty"


def test_invalid_model_config():
    invalid_model_config = {'invalid_param': 123}
    with pytest.raises(ValueError, match=r"Unexpected argument"):
        SmolLMModel(
            model_type="HuggingFaceTB/SmolLM-360M-Instruct",
            model_config_dict=invalid_model_config,
        )
