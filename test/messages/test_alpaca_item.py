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
from camel.messages.conversion.alpaca import AlpacaItem


def test_alpaca_item_empty_input_roundtrip():
    item = AlpacaItem(instruction="Summarize the text", input="", output="done")
    assert AlpacaItem.from_string(item.to_string()) == item


def test_alpaca_item_empty_input_single_blank_line():
    item = AlpacaItem.from_string(
        "### Instruction:\nSummarize the text\n\n"
        "### Input:\n\n"
        "### Response:\ndone"
    )
    assert item.instruction == "Summarize the text"
    assert item.input == ""
    assert item.output == "done"


def test_alpaca_item_non_empty_sections():
    item = AlpacaItem.from_string(
        "### Instruction:\nDo X\n\n"
        "### Input:\nsome context\n\n"
        "### Response:\nOK"
    )
    assert (item.instruction, item.input, item.output) == (
        "Do X",
        "some context",
        "OK",
    )
