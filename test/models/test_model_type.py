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
from camel.types import PredefinedModelType
from camel.types.model_type import ModelType


def test_predefined_model():
    model_type = ModelType(PredefinedModelType.GPT_4O_MINI)
    assert model_type.type == PredefinedModelType.GPT_4O_MINI
    assert model_type.value == "gpt-4o-mini"


def test_predefined_model_str():
    model_type = ModelType("gpt-4o-mini")
    assert model_type.type == PredefinedModelType.GPT_4O_MINI
    assert model_type.value == "gpt-4o-mini"


def test_open_source_model():
    model_type = ModelType("random-open-source")
    assert model_type.type == PredefinedModelType.OPEN_SOURCE
    assert model_type.value == "random-open-source"


def test_duplicated_model_types():
    model_type_1 = ModelType("random-open-source")
    model_type_2 = ModelType("random-open-source")
    assert model_type_1 == model_type_2

    model_type_3 = ModelType(PredefinedModelType.GPT_4O_MINI)
    model_type_4 = ModelType("gpt-4o-mini")
    assert model_type_3 == model_type_4
