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

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


def test_tool_function():
    return "test result"


class MockToolkit(BaseToolkit):
    def __init__(self, delay_seconds=0, timeout=None):
        super().__init__(timeout=timeout)
        self.delay_seconds = delay_seconds
        self.tools = [FunctionTool(func=test_tool_function)]

    def run(self):
        time.sleep(self.delay_seconds)
        return "run success"


def test_toolkit_custom_timeout():
    r"""Test that toolkit accepts custom timeout."""
    custom_timeout = 300
    toolkit = MockToolkit(timeout=custom_timeout)
    assert toolkit.timeout == custom_timeout


def test_toolkit_within_timeout():
    r"""Test toolkit operation completes within timeout period."""
    toolkit = MockToolkit(delay_seconds=1, timeout=2)
    assert toolkit.run() == "run success"


def test_toolkit_timeout_exceeded():
    r"""Test that operation times out when exceeding timeout period."""
    toolkit = MockToolkit(delay_seconds=2, timeout=1)
    result = toolkit.run()
    assert result == "Function run execution timed out, exceeded 1 seconds."
