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

    def add_google_style(a, b):
        """Adds two numbers.

        Args:
            a (int): The first number to be added.
            b (int): The second number to be added.
        """
        return a + b

    parsed = parse_doc(add_google_style)
    assert parsed['name'] == 'add_google_style'
    assert parsed['description'] == 'Adds two numbers.'
    assert parsed['parameters']['properties']['a']['type'] == 'int'
    assert parsed['parameters']['properties']['b']['type'] == 'int'

    def add_rest_style(a, b):
        """
        Adds two numbers.

        :param a: The first number to be added.
        :type a: int
        :param b: The second number to be added.
        :type b: int
        :return: The sum of the two numbers.
        :rtype: int
        """
        return a + b

    parsed = parse_doc(add_rest_style)
    assert parsed['name'] == 'add_rest_style'
    assert parsed['description'] == 'Adds two numbers.'
    assert parsed['parameters']['properties']['a']['type'] == 'int'
    assert parsed['parameters']['properties']['b']['type'] == 'int'

    def add_numpy_style(a, b):
        """
        Adds two numbers.

        Parameters
        ----------
        a : int
            The first number to be added.
        b : int
            The second number to be added.

        Returns
        -------
        int
            The sum of the two numbers.
        """
        return a + b

    parsed = parse_doc(add_numpy_style)
    assert parsed['name'] == 'add_numpy_style'
    assert parsed['description'] == 'Adds two numbers.'
    assert parsed['parameters']['properties']['a']['type'] == 'int'
    assert parsed['parameters']['properties']['b']['type'] == 'int'

    def add_epydoc_style(a, b):
        """
        Adds two numbers.

        @param a: The first number to be added.
        @type a: int
        @param b: The second number to be added.
        @type b: int
        @return: The sum of the two numbers.
        @rtype: int
        """
        return a + b

    parsed = parse_doc(add_epydoc_style)
    assert parsed['name'] == 'add_epydoc_style'
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
            ValueError, match="Parameter 'c' in function signature" +
            " is missing in the docstring."):
        parse_doc(mul)

    def return_param(a):
        """Return the parameter.

        Args:
            b (int): The parameter to be returned.
        """
        return a

    with pytest.raises(
            ValueError, match="Parameter 'a' in function signature" +
            " is missing in the docstring."):
        parse_doc(return_param)


def test_parse_doc_with_default_parameter():

    def add_default(a, b=1):
        """Return the parameter.
            Args:
                a (int): The first number to be added.
                b (int): The second default number to be added.
        """
        return a + b

    parse_doc(add_default)
