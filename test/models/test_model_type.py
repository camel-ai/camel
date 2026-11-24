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
from camel.types import ModelType, UnifiedModelType


def test_predefined_model():
    model_type = UnifiedModelType("gpt-4o-mini")
    assert model_type == ModelType.GPT_4O_MINI
    assert f"test_prefix/{model_type}" == "test_prefix/gpt-4o-mini"


def test_duplicated_model_types():
    model_type_1 = UnifiedModelType("random-open-source")
    model_type_2 = UnifiedModelType("random-open-source")
    assert id(model_type_1) == id(model_type_2)
    assert f"test_prefix/{model_type_1}" == "test_prefix/random-open-source"

    model_type_3 = UnifiedModelType(ModelType.GPT_4O_MINI)
    model_type_4 = UnifiedModelType("gpt-4o-mini")
    assert id(model_type_3) == id(model_type_4)


def test_default_model_is_gpt_6_luna():
    # camel-ai/camel#4542: GPT-4.1 mini shuts down Jan 14, 2027;
    # the default must be its replacement, gpt-6-luna.
    assert ModelType.DEFAULT.value == "gpt-6-luna"
    # DEFAULT used to be an alias of GPT_4_1_MINI (same value);
    # with its own value it is a distinct member again.
    assert ModelType.DEFAULT is not ModelType.GPT_4_1_MINI
    assert ModelType.GPT_4_1_MINI.value == "gpt-4.1-mini-2025-04-14"


def test_gpt_6_luna_model_type():
    assert ModelType.GPT_6_LUNA.value == "gpt-6-luna"
    assert ModelType.GPT_6_LUNA.is_openai
    assert ModelType.GPT_6_LUNA.value_for_tiktoken == "gpt-6-luna"
    # OpenAI model page: 1,050,000-token context window.
    assert ModelType.GPT_6_LUNA.token_limit == 1_050_000
    assert ModelType.DEFAULT.token_limit == 1_050_000


def test_claude_sonnet_5_5_model_type():
    # camel-ai/camel#4542: Sonnet 4.5 retires Nov 30, 2026;
    # the replacement is claude-sonnet-5-5 (1M-token context window).
    assert ModelType.CLAUDE_SONNET_5_5.value == "claude-sonnet-5-5"
    assert ModelType.CLAUDE_SONNET_5_5.is_anthropic
    assert ModelType.CLAUDE_SONNET_5_5.token_limit == 1_000_000
    assert ModelType.CLAUDE_SONNET_4_5.token_limit == 200_000
