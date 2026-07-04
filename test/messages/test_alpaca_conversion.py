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

from camel.messages.conversion import AlpacaItem


def test_roundtrip_with_empty_input():
    r"""An item with an empty ``input`` must survive a
    ``to_string`` -> ``from_string`` round-trip unchanged.

    Regression test: previously the ``### Input:`` regex greedily consumed the
    section delimiter and captured the following ``### Response:`` block as the
    input value.
    """
    item = AlpacaItem(instruction="Say hi", input="", output="hi")
    parsed = AlpacaItem.from_string(item.to_string())
    assert parsed.instruction == "Say hi"
    assert parsed.input == ""
    assert parsed.output == "hi"


def test_roundtrip_with_populated_input():
    item = AlpacaItem(
        instruction="Summarize the following article",
        input="A long article about camels.",
        output="Camels are great.",
    )
    parsed = AlpacaItem.from_string(item.to_string())
    assert parsed.instruction == item.instruction
    assert parsed.input == item.input
    assert parsed.output == item.output


def test_roundtrip_with_multiline_fields():
    item = AlpacaItem(
        instruction="Do the thing",
        input="line one\nline two",
        output="result one\nresult two",
    )
    parsed = AlpacaItem.from_string(item.to_string())
    assert parsed.input == "line one\nline two"
    assert parsed.output == "result one\nresult two"


def test_from_string_without_input_section():
    r"""The documented "without input" format (no ``### Input:`` section)
    must parse with an empty input."""
    text = "### Instruction:\nSay hi\n### Response:\nhi"
    parsed = AlpacaItem.from_string(text)
    assert parsed.instruction == "Say hi"
    assert parsed.input == ""
    assert parsed.output == "hi"


def test_from_string_missing_required_sections_raises():
    with pytest.raises(ValueError):
        AlpacaItem.from_string("### Instruction:\nonly instruction")
