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
import pytest

from camel.extractors.python_strategies import (
    BoxedStrategy,
    PythonDictStrategy,
    PythonListStrategy,
    PythonSetStrategy,
    PythonTupleStrategy,
)


@pytest.mark.asyncio
async def test_boxed_strategy():
    strategy = BoxedStrategy()

    # Test basic boxed content
    text = r"\boxed{test content}"
    result = await strategy.extract(text)
    assert result == "test content"

    # Test not so basic boxed content
    text = r"\boxed{\dfrac{9}{7}}"
    result = await strategy.extract(text)
    assert result == r"\dfrac{9}{7}"

    # Test not so basic boxed content with double backslash
    text = r"\\boxed{\dfrac{9}{7}}"
    result = await strategy.extract(text)
    assert result == r"\dfrac{9}{7}"

    # Test nested braces
    text = r"\boxed{nested {braces} test}"
    result = await strategy.extract(text)
    assert result == "nested {braces} test"

    # Test escaped characters
    text = r"\boxed{content with \{ escaped \} braces}"
    result = await strategy.extract(text)
    assert result == r"content with \{ escaped \} braces"

    # Test invalid cases
    assert await strategy.extract("no boxed content") is None
    assert await strategy.extract(r"\boxed{unclosed") is None
    assert await strategy.extract(r"\boxed{}") == ""


@pytest.mark.asyncio
async def test_python_list_strategy():
    strategy = PythonListStrategy()

    # Test basic list
    text = "[1, 2, 3]"
    result = await strategy.extract(text)
    assert result == "[1, 2, 3]"

    # Test list with mixed types
    text = '[1, "two", 3.0]'
    result = await strategy.extract(text)
    expected_list = sorted([1, "two", 3.0], key=lambda x: str(x))
    assert result == repr(expected_list)

    # Test nested list
    text = '[[1, 2], [3, 4]]'
    result = await strategy.extract(text)
    assert result == "[[1, 2], [3, 4]]"

    # Test invalid cases
    assert await strategy.extract("not a list") is None
    assert await strategy.extract("[invalid") is None
    result = await strategy.extract("[1, 2,]")
    assert result == "[1, 2]"


@pytest.mark.asyncio
async def test_python_dict_strategy():
    strategy = PythonDictStrategy()

    # Test basic dict
    text = '{"a": 1, "b": 2}'
    result = await strategy.extract(text)
    assert result == "{'a': 1, 'b': 2}"

    # Test mixed type values
    text = '{"b": [1, 2], "a": "string"}'
    result = await strategy.extract(text)
    input_dict = {"b": [1, 2], "a": "string"}
    sorted_dict = dict(sorted(input_dict.items(), key=lambda x: str(x[0])))
    assert result == repr(sorted_dict)

    # Test nested dict
    text = '{"outer": {"inner": 1}}'
    result = await strategy.extract(text)
    assert result == "{'outer': {'inner': 1}}"

    # Test invalid cases
    assert await strategy.extract("not a dict") is None
    assert await strategy.extract("{invalid}") is None
    assert await strategy.extract('{"key": value}') is None


@pytest.mark.asyncio
async def test_python_set_strategy():
    strategy = PythonSetStrategy()

    # Test basic set
    text = '{1, 2, 3}'
    result = await strategy.extract(text)
    assert result == "{1, 2, 3}"

    # Test set with mixed types
    text = '{1, "two", 3.0}'
    result = await strategy.extract(text)
    input_set = {1, "two", 3.0}
    sorted_elements = sorted(input_set, key=lambda x: str(x))
    assert result == repr(set(sorted_elements))

    # Test invalid cases
    assert await strategy.extract("not a set") is None
    assert await strategy.extract("{invalid") is None
    assert await strategy.extract("set(invalid)") is None


@pytest.mark.asyncio
async def test_python_tuple_strategy():
    strategy = PythonTupleStrategy()

    # Test basic tuple
    text = '(1, 2, 3)'
    result = await strategy.extract(text)
    assert result == '(1, 2, 3)'

    # Test tuple with mixed types
    text = '(1, "two", 3.0)'
    result = await strategy.extract(text)
    input_tuple = (1, "two", 3.0)
    sorted_tuple = tuple(sorted(input_tuple, key=lambda x: str(x)))
    assert result == repr(sorted_tuple)

    # Test nested tuple
    text = '((1, 2), (3, 4))'
    result = await strategy.extract(text)
    assert result == "((1, 2), (3, 4))"

    # Test invalid cases
    assert await strategy.extract("not a tuple") is None
    assert await strategy.extract("(invalid)") is None
