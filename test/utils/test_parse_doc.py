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

from camel.utils import parse_doc


def test_parse_doc_valid():

    def add(a, b):
        """Adds two numbers.

        Args:
            a (int): The first number to be added.
            b (int): The second number to be added.
        """
        return a + b

    parsed = parse_doc(add)
    assert parsed['name'] == 'add'
    assert parsed['description'] == 'Adds two numbers.'
    assert parsed['parameters']['properties']['a']['type'] == 'int'
    assert parsed['parameters']['properties']['b']['type'] == 'int'


def test_parse_doc_no_docstring():

    def sub(a, b):
        return a - b

    with pytest.raises(
            ValueError,
            match=f"Invalid function {sub.__name__}: no docstring provided."):
        parse_doc(sub)


def test_parse_doc_mismatch():

    def mul(a, b, c):
        """Multiplies three numbers.

        Args:
            a (int): The first number to be multiplied.
            b (int): The second number to be multiplied.
        """
        return a * b * c

    with pytest.raises(
            ValueError,
            match=(r"Number of parameters in function signature "
                   r"\(3\) does not match that in docstring \(2\).")):
        parse_doc(mul)


def test_parse_doc_no_args_section():

    def return_param(a):
        """Return the parameter.

        Args:
            b (int): The parameter to be returned.
        """
        return a

    with pytest.raises(
            ValueError, match=("Parameter 'a' in function signature"
                               " is missing in the docstring.")):
        parse_doc(return_param)
