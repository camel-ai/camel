# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import json

from camel.messages.conversion.qa import QAItem


def test_qa_item_to_json():
    r"""Test converting a QAItem to JSON."""
    qa = QAItem(
        question="What is the capital of Australia?",
        answer="The capital city of Australia is Canberra."
    )
    json_str = qa.to_json()
    data = json.loads(json_str)

    assert data["question"] == "What is the capital of Australia?"
    assert data["answer"] == "The capital city of Australia is Canberra."


def test_qa_item_from_json():
    r"""Test parsing a QAItem from JSON."""
    json_str = '{"question": "What is the capital of Australia?", "answer": "The capital city of Australia is Canberra."}'
    qa = QAItem.from_json(json_str)

    assert qa.question == "What is the capital of Australia?"
    assert qa.answer == "The capital city of Australia is Canberra."
