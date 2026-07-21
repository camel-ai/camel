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
import pytest

from camel.toolkits import FunctionTool
from camel.utils.async_func import sync_funcs_to_async


@pytest.mark.asyncio
async def test_sync_funcs_to_async_binds_each_function():
    def add(a: int, b: int) -> int:
        r"""Add two integers."""
        return a + b

    def multiply(a: int, b: int) -> int:
        r"""Multiply two integers."""
        return a * b

    add_tool, multiply_tool = sync_funcs_to_async(
        [FunctionTool(add), FunctionTool(multiply)]
    )

    assert await add_tool.func(3, 4) == 7
    assert await multiply_tool.func(3, 4) == 12
    assert add_tool.get_function_name() == "add"
    assert multiply_tool.get_function_name() == "multiply"
