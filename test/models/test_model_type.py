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
