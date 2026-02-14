# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import pytest

from camel.configs import OpenRouterConfig
from camel.models import OpenRouterModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter
import os 
@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.OPENROUTER_LLAMA_3_1_405B,
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        ModelType.OPENROUTER_OLYMPICODER_7B,
        ModelType.OPENROUTER_HORIZON_ALPHA,
    ],
)
def test_openrouter_model(model_type: ModelType):
    model = OpenRouterModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == OpenRouterConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)

def test_openrouter_gemini_caching(model_type="google/gemma-3-27b-it:free"):
    config = {"enable_prompt_caching": True}
    model = OpenRouterModel(model_type, model_config_dict=config, api_key=os.environ.get("OPENROUTER_API_KEY"))
    
    messages = [{"role": "system", "content": "Large context..."}]
    prepared = model._prepare_messages(messages)
    
    assert isinstance(prepared[0]["content"], list)
    assert "cache_control" in prepared[0]["content"][0]
    assert prepared[0]["content"][0]["cache_control"]["type"] == "ephemeral"

def test_openrouter_openai(model_type="openai/gpt-4o-mini"):
    config = {"enable_prompt_caching": True}
    model = OpenRouterModel(model_type, model_config_dict=config, api_key=os.environ.get("OPENROUTER_AP I_KEY"))
    
    messages = [{"role": "system", "content": "Large context..."}]
    prepared = model._prepare_messages(messages)
    
    assert isinstance(prepared[0]["content"], str)
    assert "cache_control" not in prepared[0]["content"][0]
