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

from camel.toolkits import MathToolkit


def test_math_divide_normal():
    toolkit = MathToolkit()
    assert toolkit.math_divide(10, 4) == 2.5
    assert toolkit.math_divide(10, 3, decimal_places=3) == 3.333


def test_math_divide_by_zero_returns_message():
    toolkit = MathToolkit()
    result = toolkit.math_divide(1, 0)
    assert isinstance(result, str)
    assert "divide by zero" in result.lower()


def test_basic_operations():
    toolkit = MathToolkit()
    assert toolkit.math_add(2, 3) == 5
    assert toolkit.math_subtract(5, 2) == 3
    assert toolkit.math_multiply(2, 3) == 6
    assert toolkit.math_round(3.14159, 2) == 3.14


def test_get_tools():
    toolkit = MathToolkit()
    tools = toolkit.get_tools()
    assert len(tools) == 5
