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
                     help="Run all tests")
    parser.addoption("--fast-test-mode", action="store_true",
                     help="Run all tests without LLM inference")
    parser.addoption("--main-test-only", action="store_true",
                     help="Run all tests except ones of optional modules")
    parser.addoption("--optional-test-only", action="store_true",
                     help="Run only tests with \"optional\" mark")
    parser.addoption("--slow-test-only", action="store_true",
                     help="Run only tests with LLM inefrence")


def pytest_collection_modifyitems(config: Config, items: List[Item]) -> None:
    # Run all tests in full test mode
    if config.getoption("--full-test-mode"):
        return

    # Skip all tests involving LLM inference both remote
    # (including OpenAI API) and local ones, since they are slow
    # and may drain money if fast test mode is enabled.
    if config.getoption("--fast-test-mode"):
        skip_slow = pytest.mark.skip(reason="Skipped for fast test mode")
        for item in items:
            if "model_backend" in item.keywords or "optional" in item.keywords:
                item.add_marker(skip_slow)
        return
