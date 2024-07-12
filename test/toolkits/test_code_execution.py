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

import pytest

from camel.toolkits.code_execution import CodeExecutionToolkit


@pytest.fixture
def code_execution_toolkit():
    return CodeExecutionToolkit()


def test_execute_code(code_execution_toolkit):
    code = "x = 'a'\ny = 'b'\nx + y"
    result = code_execution_toolkit.execute_code(code)

    # ruff: noqa: E501
    expected_result = f"Executed the code below:\n```py\n{code}\n```\n> Executed Results:\nab"
    assert expected_result == result
