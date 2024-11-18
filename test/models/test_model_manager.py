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

from typing import TYPE_CHECKING, List

import pytest
from mock import Mock

from camel.models import BaseModelBackend
from camel.models.base_model import ModelManager


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "models_number, strategy, calls_count, times_each_model_called",
    [
        (1, "round_robin", 9, 9),
        (3, "round_robin", 9, 3),
        (1, "not_existent", 9, 9),
        (3, "not_existent", 9, 3),
    ],
)
def test_model_manager(
    models_number: int,
    strategy: str,
    calls_count: int,
    times_each_model_called: int,
):
    models = (
        [Mock(run=Mock()) for _ in range(models_number)]
        if models_number > 1
        else Mock()
    )
    if TYPE_CHECKING:
        assert type(models) == List[BaseModelBackend]
    model_manager = ModelManager(models, scheduling_strategy=strategy)
    # The statement below shall be updated after new strategies are introduced.
    assert model_manager.scheduling_strategy.__name__ == "round_robin"
    assert isinstance(model_manager.models, list)
    assert len(model_manager.models) == models_number
    for _ in range(calls_count):
        model_manager.run(["message"] for _ in range(calls_count))
    for model in model_manager.models:
        if TYPE_CHECKING:
            assert isinstance(model, Mock)
        assert model.run.call_count == times_each_model_called
