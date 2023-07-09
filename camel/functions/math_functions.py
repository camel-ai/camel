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
from dataclasses import dataclass
from typing import Callable, List

from camel.functions import BaseFuncs


def add(a, b):
    """
    Adds Two Numbers

    Args
    ----------
    a : integer
        number to be added
    b : integer
        number to be added

    Returns
    -------
    integer
        sum
    """
    return a + b


def sub(a, b):
    """
    Subs Two Numbers

    Args
    ----------
    a : integer
        number to be subbed
    b : integer
        number to be subbed

    Returns
    -------
    int
        sub
    """
    return a - b


def mul(a, b):
    """
    Muls Two Numbers

    Args
    ----------
    a : integer
        number to be muled
    b : integer
        number to be muled

    Returns
    -------
    int
        mul
    """
    return a * b


@dataclass
class MathFuncs(BaseFuncs):
    r"""Class for math function collection, which currently includes
    integere addition, subtraction and multiplication.
    """

    def __init__(self):
        self.functions: List[Callable] = [
            add,
            sub,
            mul,
        ]
