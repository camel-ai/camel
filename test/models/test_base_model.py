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


from camel.models import BaseModelBackend
from camel.types import ModelType


class TestBaseModelBackend:
    r"""Unit tests for the BaseModelBackend class."""

    def test_preprocess_messages(self):
        r"""Test message preprocessing removes thinking content correctly."""

        class DummyModel(BaseModelBackend):
            @property
            def token_counter(self):
                pass

            def run(self, messages):
                pass

            def check_model_config(self):
                pass

        model = DummyModel(ModelType.GPT_4O_MINI)

        # Test basic thinking removal
        messages = [
            {
                'role': 'user',
                'content': 'Hello <think>thinking about response</think> '
                'world',
            },
            {
                'role': 'assistant',
                'content': '<think>Let me think...\nThinking more...</'
                'think>Response',
            },
        ]

        processed = model.preprocess_messages(messages)
        assert len(processed) == 2
        assert processed[0]['content'] == 'Hello  world'
        assert processed[1]['content'] == 'Response'

        # Test message without thinking tags
        messages = [{'role': 'user', 'content': 'plain message'}]
        processed = model.preprocess_messages(messages)
        assert processed[0]['content'] == 'plain message'

    def test_metaclass_preprocessing(self):
        r"""Test that metaclass automatically preprocesses messages in run
        method."""
        processed_messages = None

        class TestModel(BaseModelBackend):
            @property
            def token_counter(self):
                pass

            def run(self, messages):
                nonlocal processed_messages
                processed_messages = messages
                return None

            def check_model_config(self):
                pass

        model = TestModel(ModelType.GPT_4O_MINI)
        messages = [
            {'role': 'user', 'content': 'Hello <think>hi</think> world'}
        ]

        # Call run method and verify messages were preprocessed
        model.run(messages)
        assert processed_messages is not None
        assert processed_messages[0]['content'] == 'Hello  world'
