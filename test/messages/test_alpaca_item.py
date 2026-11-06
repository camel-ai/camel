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

from camel.messages import AlpacaItem


@pytest.mark.parametrize(
    "instruction, item_input, output",
    [
        ("Summarize the text", "", "done"),
        ("Translate to French", "Hello world", "Bonjour le monde"),
        ("List the steps", "first\nsecond", "one\ntwo"),
    ],
)
def test_to_string_from_string_roundtrip(
    instruction: str, item_input: str, output: str
):
    r"""A serialized item must parse back into an equal item, including the
    documented case where the input is an empty string."""
    item = AlpacaItem(instruction=instruction, input=item_input, output=output)

    assert AlpacaItem.from_string(item.to_string()) == item


def test_from_string_accepts_missing_input_section():
    r"""The format without an ``### Input:`` section is documented, so it
    must keep parsing to an empty input."""
    text = "### Instruction:\nDo the thing\n### Response:\nDone"

    item = AlpacaItem.from_string(text)

    assert item.instruction == "Do the thing"
    assert item.input == ""
    assert item.output == "Done"


def test_from_string_requires_instruction_and_response():
    r"""A text without the required sections is still rejected."""
    with pytest.raises(ValueError):
        AlpacaItem.from_string("### Instruction:\nDo the thing\n")
