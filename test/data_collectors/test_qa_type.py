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

import pytest

from camel.messages.conversion.qa import QAItem

def test_qa_item_to_string():
    r"""Test converting a QAItem to a formatted string."""
    qa_item = QAItem(
        question="What is the capital of Australia?",
        answer="The capital city of Australia is Canberra."
    )

    text = qa_item.to_string()

    assert "Question:" in text
    assert "What is the capital of Australia?" in text
    assert "Answer:" in text
    assert "The capital city of Australia is Canberra." in text

def test_qa_item_from_string():
    r"""Test parsing a QAItem from a formatted string."""
    text = "Question: What is the capital city of Australia?\nAnswer: The capital city of Australia is Canberra."

    # Create QAItem using from_string()
    item = QAItem.from_string(text)

    # Assertions to verify correct parsing
    assert isinstance(item, QAItem)  # Ensure it's an instance of QAItem
    assert item.question == "What is the capital city of Australia?"
    assert item.answer == "The capital city of Australia is Canberra."