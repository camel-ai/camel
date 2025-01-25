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

import time
from typing import List

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


def test_tool_function():
    return "test result"


class MockToolkit(BaseToolkit):
    def __init__(self, delay_seconds=0, timeout=None):
        super().__init__(timeout=timeout)
        self.delay_seconds = delay_seconds
        self.tools = [FunctionTool(func=test_tool_function)]

    def _get_tools_impl(self) -> List[FunctionTool]:
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        return self.tools


def test_toolkit_default_timeout():
    r"""Test that toolkit uses default timeout."""
    toolkit = MockToolkit()
    assert toolkit.timeout == toolkit.DEFAULT_TIMEOUT


def test_toolkit_custom_timeout():
    r"""Test that toolkit accepts custom timeout."""
    custom_timeout = 300
    toolkit = MockToolkit(timeout=custom_timeout)
    assert toolkit.timeout == custom_timeout


def test_toolkit_no_timeout_needed():
    r"""Test toolkit operation completes when no timeout needed."""
    toolkit = MockToolkit(delay_seconds=0)
    tools = toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)
    assert tools[0].func == test_tool_function


def test_toolkit_within_timeout():
    r"""Test toolkit operation completes within timeout period."""
    toolkit = MockToolkit(delay_seconds=1, timeout=2)
    tools = toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)
    assert tools[0].func == test_tool_function


def test_toolkit_timeout_exceeded():
    r"""Test that operation times out when exceeding timeout period."""
    toolkit = MockToolkit(delay_seconds=2, timeout=1)
    result = toolkit.get_tools()
    assert isinstance(result, str)
    assert "Error: Toolkit operation timed out after 1 seconds" in result


def test_toolkit_disable_timeout():
    r"""Test that timeout can be disabled."""
    # Create toolkit with timeout disabled
    toolkit = MockToolkit(delay_seconds=2, timeout=0)
    tools = toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)
    assert tools[0].func == test_tool_function
