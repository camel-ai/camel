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
from typing import List

import pytest
from _pytest.config import Config
from _pytest.nodes import Item


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--full-test-mode", action="store_true",
                     help="Enable full test mode")
    parser.addoption("--fast-test-mode", action="store_true",
                     help="Enable fast test mode")


def pytest_collection_modifyitems(config: Config, items: List[Item]) -> None:
    # Skip full test only tests if not in full test mode
    if not config.getoption("--full-test-mode"):
        skip_full_test = pytest.mark.skip(
            reason="Test runs only in full test mode")
        for item in items:
            if "full_test_only" in item.keywords:
                item.add_marker(skip_full_test)

    # Skip all tests involving LLM inference both remote
    # (including OpenAI API) and local ones, since they are slow
    # and may drain money if fast test mode is enabled.
    if config.getoption("--fast-test-mode"):
        skip_slow = pytest.mark.skip(reason="Skipped for fast test mode")
        for item in items:
            if "slow" in item.keywords or "model_backend" in item.keywords:
                item.add_marker(skip_slow)
