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


import uuid

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

            def _run(self, messages, response_format=None, tools=None):
                pass

            async def _arun(self, messages, response_format=None, tools=None):
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

        # Test normal thinking sections
        messages = [
            {'role': 'user', 'content': 'Start <think>Think</think>End'}
        ]
        processed = model.preprocess_messages(messages)
        assert processed[0]['content'] == 'Start End'

        # Test system messages (should not be processed)
        messages = [
            {
                'role': 'system',
                'content': 'System <think>thinking</think> message',
            }
        ]
        processed = model.preprocess_messages(messages)
        assert (
            processed[0]['content'] == 'System <think>thinking</think> message'
        )

        # Test empty thinking tags
        messages = [
            {'role': 'assistant', 'content': 'Before<think></think>After'}
        ]
        processed = model.preprocess_messages(messages)
        assert processed[0]['content'] == 'BeforeAfter'

        # Test multiple thinking tags in one message
        messages = [
            {
                'role': 'assistant',
                'content': 'Start <think>First thought</think> middle '
                '<think>Second thought</think> end',
            }
        ]
        processed = model.preprocess_messages(messages)
        assert processed[0]['content'] == 'Start  middle  end'

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

            def _run(self, messages, response_format=None, tools=None):
                pass

            async def _arun(self, messages, response_format=None, tools=None):
                pass

        model = TestModel(ModelType.GPT_4O_MINI)
        messages = [
            {'role': 'user', 'content': 'Hello <think>hi</think> world'}
        ]

        # Call run method and verify messages were preprocessed
        model.run(messages)
        assert processed_messages is not None
        assert processed_messages[0]['content'] == 'Hello  world'

    def test_preprocess_tool_calls(self):
        r"""Test message preprocessing formats tool calls and responses
        correctly.
        """

        class DummyModel(BaseModelBackend):
            @property
            def token_counter(self):
                pass

            def run(self, messages):
                pass

            def _run(self, messages, response_format=None, tools=None):
                pass

            async def _arun(self, messages, response_format=None, tools=None):
                pass

        model = DummyModel(ModelType.GPT_4O_MINI)

        # Helper function to create tool call objects
        def create_tool_call(id, name, args):
            return {
                'id': id,
                'type': 'function',
                'function': {'name': name, 'arguments': args},
            }

        # Test 1: No tool calls - should return processed messages unchanged
        messages = [
            {'role': 'user', 'content': 'Hello world'},
            {'role': 'assistant', 'content': 'Hi there!'},
        ]
        processed = model.preprocess_messages(messages)
        assert processed == messages

        # Test 2: Simple tool call and response
        tool_call_id = str(uuid.uuid4())
        messages = [
            {'role': 'user', 'content': 'What is the weather?'},
            {
                'role': 'assistant',
                'content': None,
                'tool_calls': [
                    create_tool_call(
                        tool_call_id, 'get_weather', '{"location":"New York"}'
                    )
                ],
            },
            {
                'role': 'tool',
                'tool_call_id': tool_call_id,
                'content': '{"temperature": 72, "condition": "sunny"}',
            },
            {
                'role': 'assistant',
                'content': 'The weather in New York is sunny and 72°F.',
            },
        ]

        processed = model.preprocess_messages(messages)
        assert processed == messages

        # Test 3: Out of order tool calls and responses
        tool_call_id1 = str(uuid.uuid4())
        tool_call_id2 = str(uuid.uuid4())
        messages = [
            {'role': 'user', 'content': 'What is the weather and time?'},
            # First tool response appears before the tool call
            {
                'role': 'tool',
                'tool_call_id': tool_call_id1,
                'content': '{"temperature": 72, "condition": "sunny"}',
            },
            {
                'role': 'assistant',
                'content': None,
                'tool_calls': [
                    create_tool_call(
                        tool_call_id1, 'get_weather', '{"location":"New York"}'
                    ),
                    create_tool_call(
                        tool_call_id2, 'get_time', '{"timezone":"EST"}'
                    ),
                ],
            },
            {
                'role': 'tool',
                'tool_call_id': tool_call_id2,
                'content': '{"time": "10:30 AM"}',
            },
            {
                'role': 'assistant',
                'content': 'The weather in New York is sunny and 72°F. '
                'The time is 10:30 AM.',
            },
        ]

        processed = model.preprocess_messages(messages)
        assert len(processed) == 5
        assert processed[0]['role'] == 'user'
        assert (
            processed[1]['role'] == 'assistant'
            and 'tool_calls' in processed[1]
        )
        assert (
            processed[2]['role'] == 'tool'
            and processed[2]['tool_call_id'] == tool_call_id1
        )
        assert (
            processed[3]['role'] == 'tool'
            and processed[3]['tool_call_id'] == tool_call_id2
        )
        assert processed[4]['role'] == 'assistant'

        # Test 4: Complex conversation with multiple tool calls
        # Create IDs for tool calls
        ids = [str(uuid.uuid4()) for _ in range(3)]

        messages = [
            {'role': 'user', 'content': 'What is the weather?'},
            # First assistant message with tool call
            {
                'role': 'assistant',
                'content': None,
                'tool_calls': [
                    create_tool_call(
                        ids[0], 'get_weather', '{"location":"New York"}'
                    )
                ],
            },
            {
                'role': 'tool',
                'tool_call_id': ids[0],
                'content': '{"temperature": 72, "condition": "sunny"}',
            },
            {'role': 'user', 'content': 'What about the time?'},
            # Second assistant message with multiple tool calls
            {
                'role': 'assistant',
                'content': None,
                'tool_calls': [
                    create_tool_call(ids[1], 'get_time', '{"timezone":"EST"}'),
                    create_tool_call(ids[2], 'get_date', '{"format":"short"}'),
                ],
            },
            {
                'role': 'tool',
                'tool_call_id': ids[1],
                'content': '{"time": "10:30 AM"}',
            },
            {
                'role': 'tool',
                'tool_call_id': ids[2],
                'content': '{"date": "2023-04-15"}',
            },
            {
                'role': 'assistant',
                'content': 'The time is 10:30 AM EST and the date is '
                'April 15, 2023.',
            },
        ]

        processed = model.preprocess_messages(messages)
        assert len(processed) == 8

        # Verify correct ordering of tool calls and responses
        assert (
            processed[1]['role'] == 'assistant'
            and processed[1]['tool_calls'][0]['id'] == ids[0]
        )
        assert (
            processed[2]['role'] == 'tool'
            and processed[2]['tool_call_id'] == ids[0]
        )
        assert (
            processed[4]['role'] == 'assistant'
            and len(processed[4]['tool_calls']) == 2
        )
        assert (
            processed[5]['role'] == 'tool'
            and processed[5]['tool_call_id'] == ids[1]
        )
        assert (
            processed[6]['role'] == 'tool'
            and processed[6]['tool_call_id'] == ids[2]
        )

        # Test 5: Edge cases - Missing tool responses and orphaned tool
        # responses
        tests = [
            # Missing tool response
            {
                'messages': [
                    {
                        'role': 'user',
                        'content': 'What is the weather and time?',
                    },
                    {
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': [
                            create_tool_call(
                                ids[0],
                                'get_weather',
                                '{"location":"New York"}',
                            ),
                            create_tool_call(
                                ids[1], 'get_time', '{"timezone":"EST"}'
                            ),
                        ],
                    },
                    # Only one tool response is provided
                    {
                        'role': 'tool',
                        'tool_call_id': ids[0],
                        'content': '{"temperature": 72}',
                    },
                    {
                        'role': 'assistant',
                        'content': 'The weather in New York is 72°F.',
                    },
                ],
                'assertions': lambda p: (
                    len(p) == 4
                    and p[0]['role'] == 'user'
                    and p[1]['role'] == 'assistant'
                    and 'tool_calls' in p[1]
                    and p[2]['role'] == 'tool'
                    and p[2]['tool_call_id'] == ids[0]
                    and p[3]['role'] == 'assistant'
                ),
            },
            # Orphaned tool response
            {
                'messages': [
                    {'role': 'user', 'content': 'What is the weather?'},
                    {
                        'role': 'tool',
                        'tool_call_id': ids[0],
                        'content': '{"temperature": 72}',
                    },
                    {'role': 'assistant', 'content': 'The weather is 72°F.'},
                ],
                'assertions': lambda p: (
                    len(p) == 3
                    and p[0]['role'] == 'user'
                    and p[1]['role'] == 'assistant'
                    and p[2]['role'] == 'tool'
                    and p[2]['tool_call_id'] == ids[0]
                ),
            },
        ]

        for test in tests:
            processed = model.preprocess_messages(test['messages'])
            assert test['assertions'](processed)

        # Test 6: Combined thinking removal and tool call formatting
        tool_call_id = str(uuid.uuid4())
        messages = [
            {
                'role': 'user',
                'content': 'What is the weather <think>in New York</think>?',
            },
            {
                'role': 'assistant',
                'content': '<think>I should check the weather</think>',
                'tool_calls': [
                    create_tool_call(
                        tool_call_id, 'get_weather', '{"location":"New York"}'
                    )
                ],
            },
            {
                'role': 'tool',
                'tool_call_id': tool_call_id,
                'content': '{"temperature": 72}',
            },
            {
                'role': 'assistant',
                'content': '<think>Format nicely</think>The weather is 72°F.',
            },
        ]

        processed = model.preprocess_messages(messages)
        assert len(processed) == 4
        assert (
            processed[0]['role'] == 'user'
            and processed[0]['content'] == 'What is the weather ?'
        )
        assert (
            processed[1]['role'] == 'assistant'
            and processed[1]['content'] == ''
        )
        assert (
            processed[2]['role'] == 'tool'
            and processed[2]['tool_call_id'] == tool_call_id
        )
        assert (
            processed[3]['role'] == 'assistant'
            and processed[3]['content'] == 'The weather is 72°F.'
        )
