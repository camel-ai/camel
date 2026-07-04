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
import os
from typing import List

import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from dotenv import load_dotenv

load_dotenv()

# Some test modules construct a model backend at import/collection time (for
# example as a ``pytest.mark.parametrize`` value). Backend construction only
# checks that the relevant API key is present and non-empty -- it does not
# validate the key -- so without a placeholder those modules fail to collect
# on environments that have no credentials (notably fork pull requests, whose
# CI runs do not receive repository secrets), which aborts the whole test job
# before any test runs.
#
# Provide non-empty placeholders so collection succeeds everywhere. A real key
# (from the environment or ``.env``) is always preserved: each placeholder is
# only applied when its variable is unset or empty. Tests that make real API
# calls are gated behind the ``model_backend`` marker and skipped in fast-test
# mode, so these placeholders are never used for an actual request.
#
# ``OPENAI_API_KEY`` covers the agent/model test modules (e.g.
# test/agents/test_chat_agent.py builds an OpenAI model as a parametrize
# value); ``DEEPSEEK_API_KEY`` covers services/agent_mcp/agent_config.py, which
# builds a DeepSeek model at import time and is imported by
# test/services/test_agent_mcp_server.py.
for _collection_env_var in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
    if not os.environ.get(_collection_env_var):
        os.environ[_collection_env_var] = "placeholder-key-for-collection"


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
