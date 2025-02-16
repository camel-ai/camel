import pytest
import json
from pydantic import ValidationError

from camel.messages.conversion.code_model import CodeItem


def test_code_item_valid():
    r"""Test valid CodeItem creation."""
    item = CodeItem(
        description="Write a Python function to compute factorial.",
        code="def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)"
    )
    assert item.description == "Write a Python function to compute factorial."
    assert "def factorial" in item.code

def test_code_item_valid_2():
    r"""Test valid CodeItem creation."""
    item = CodeItem(
        description="Write a sample SQL code",
        code="SELECT * FROM VALID_DATA;"
    )

    # Assert that the object is created successfully
    assert item.description == "Write a sample SQL code"
    assert item.code == "SELECT * FROM VALID_DATA;"

    # Assert that the validation method correctly identifies SQL as code
    assert CodeItem.is_code_using_pygments(item.code) == True



def test_code_item_invalid_code():
    r"""Test invalid CodeItem with missing code structure."""
    with pytest.raises(ValueError):
        CodeItem(description="Write a function.", code="bLAH bLAH blah blah")


def test_code_item_non_ascii_code():
    r"""Test CodeItem with non-ASCII characters in code."""
    invalid_code = "def test():\n    print('Hello 👋')"
    with pytest.raises(ValidationError):
        CodeItem(description="Function with emoji.", code=invalid_code)


def test_code_item_from_string():
    r"""Test parsing a CodeItem from a formatted string."""
    text = r"""Description: Write a Python function to check if a number is prime.
Code:
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True"""

    code_item = CodeItem.from_string(text)

    assert code_item.description == "Write a Python function to check if a number is prime."
    assert "def is_prime" in code_item.code
    assert "return False" in code_item.code


def test_code_item_to_string():
    r"""Test converting a CodeItem to a formatted string."""
    code_item = CodeItem(
        description="Write a Python function to check if a number is prime.",
        code=r"""def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True"""
    )

    text = code_item.to_string()

    assert "Description:" in text
    assert "Write a Python function to check if a number is prime." in text
    assert "def is_prime" in text
    assert "return False" in text
