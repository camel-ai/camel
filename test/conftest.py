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
from typing import List

import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from dotenv import load_dotenv

load_dotenv()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--full-test-mode", action="store_true", help="Run all tests"
    )
    parser.addoption(
        "--default-test-mode",
        action="store_true",
        help="Run all tests except the very slow ones",
    )
    parser.addoption(
        "--fast-test-mode",
        action="store_true",
        help="Run only tests without LLM inference",
    )
    parser.addoption(
        "--llm-test-only",
        action="store_true",
        help="Run only tests with LLM inference except the very slow ones",
    )
    parser.addoption(
        "--very-slow-test-only",
        action="store_true",
        help="Run only the very slow tests",
    )


def pytest_collection_modifyitems(config: Config, items: List[Item]) -> None:
    if config.getoption("--llm-test-only"):
        skip_fast = pytest.mark.skip(reason="Skipped for llm test only")
        for item in items:
            if "model_backend" not in item.keywords:
                item.add_marker(skip_fast)
        return
    elif config.getoption("--very-slow-test-only"):
        skip_fast = pytest.mark.skip(reason="Skipped for very slow test only")
        for item in items:
            if "very_slow" not in item.keywords:
                item.add_marker(skip_fast)
        return
    # Run all tests in full test mode
    elif config.getoption("--full-test-mode"):
        return
    # Skip all tests involving LLM inference both remote
    # (including OpenAI API) and local ones, since they are slow
    # and may drain money if fast test mode is enabled.
    elif config.getoption("--fast-test-mode"):
        skip = pytest.mark.skip(reason="Skipped for fast test mode")
        for item in items:
            if "optional" in item.keywords or "model_backend" in item.keywords:
                item.add_marker(skip)
        return
    else:
        skip_full_test = pytest.mark.skip(
            reason="Very slow test runs only in full test mode"
        )
        for item in items:
            if "very_slow" in item.keywords:
                item.add_marker(skip_full_test)
        return
