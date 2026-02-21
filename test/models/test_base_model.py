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


import json
import uuid

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from camel.models import BaseModelBackend
from camel.types import ModelType


class TestBaseModelBackend:
    r"""Unit tests for the BaseModelBackend class."""

    def test_log_request_records_model_config_with_env_flag(
        self, monkeypatch, tmp_path
    ):
        r"""Test logging model_config_dict is controlled by env vars."""

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

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "true")

        model_config_dict = {
            "temperature": 0.2,
            "system_prompt": "你好,世界",
            "greeting": "こんにちは",
        }
        messages = [{"role": "user", "content": "请帮我写一首诗"}]
        model = DummyModel(
            ModelType.GPT_4O_MINI, model_config_dict=model_config_dict
        )

        log_path = model._log_request(messages)
        assert log_path is not None

        with open(log_path, "r", encoding="utf-8") as f:
            log_text = f.read()

        log_data = json.loads(log_text)
        assert log_data["request"]["messages"] == messages
        assert log_data["request"]["model_config_dict"] == model_config_dict
        assert "你好,世界" in log_text
        assert "请帮我写一首诗" in log_text
        assert r"\u4f60\u597d" not in log_text

    def test_log_request_skips_model_config_when_disabled(
        self, monkeypatch, tmp_path
    ):
        r"""Test model_config_dict is omitted when env flag is disabled."""

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

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "false")

        model = DummyModel(
            ModelType.GPT_4O_MINI,
            model_config_dict={"temperature": 0.1, "lang": "中文"},
        )
        log_path = model._log_request(
            [{"role": "user", "content": "test message"}]
        )
        assert log_path is not None

        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert "model_config_dict" not in log_data["request"]

    def test_log_request_model_config_enabled_by_default_when_log_on(
        self, monkeypatch, tmp_path
    ):
        r"""Test model_config logging defaults to enabled with log enabled."""

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

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.delenv(
            "CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", raising=False
        )

        model = DummyModel(
            ModelType.GPT_4O_MINI, model_config_dict={"temperature": 0.3}
        )
        log_path = model._log_request(
            [{"role": "user", "content": "test message"}]
        )
        assert log_path is not None

        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert log_data["request"]["model_config_dict"] == {"temperature": 0.3}

    def test_log_response_preserves_multilingual_text(
        self, monkeypatch, tmp_path
    ):
        r"""Test response logging keeps multilingual text readable."""

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

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "true")

        model = DummyModel(
            ModelType.GPT_4O_MINI, model_config_dict={"lang": "多语言"}
        )
        log_path = model._log_request(
            [{"role": "user", "content": "你好,مرحبا,こんにちは"}]
        )
        assert log_path is not None

        model._log_response(
            log_path,
            {
                "content": "回复:你好,مرحبا,こんにちは",
                "extra": "Русский текст",
            },
        )

        with open(log_path, "r", encoding="utf-8") as f:
            log_text = f.read()

        assert "回复:你好,مرحبا,こんにちは" in log_text
        assert "Русский текст" in log_text
        assert r"\u56de\u590d" not in log_text

    def test_run_logs_final_client_payload_model_config_dict(
        self, monkeypatch, tmp_path
    ):
        r"""Test run logs the final payload passed to the model client."""

        class FakeCompletions:
            def create(self, **kwargs):
                return {"status": "ok", "request_keys": sorted(kwargs)}

        class FakeChat:
            def __init__(self):
                self.completions = FakeCompletions()

        class FakeClient:
            def __init__(self):
                self.chat = FakeChat()

        class DummyModel(BaseModelBackend):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._client = FakeClient()

            @property
            def token_counter(self):
                pass

            def _run(self, messages, response_format=None, tools=None):
                return self._client.chat.completions.create(
                    messages=messages,
                    model=self.model_type,
                    tools=tools,
                    temperature=0.9,
                )

            async def _arun(self, messages, response_format=None, tools=None):
                return {"status": "ok", "tool_count": len(tools or [])}

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "true")

        model = DummyModel(
            ModelType.GPT_4O_MINI,
            model_config_dict={
                "temperature": 0.1,
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "default_tool"},
                    }
                ],
            },
        )
        runtime_tools = [
            {
                "type": "function",
                "function": {
                    "name": "weather_lookup",
                    "description": "查询天气信息",
                },
            }
        ]

        model.run(
            messages=[{"role": "user", "content": "帮我查北京天气"}],
            tools=runtime_tools,
        )

        log_files = list(tmp_path.rglob("conv_*.json"))
        assert len(log_files) == 1

        with open(log_files[0], "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert (
            log_data["request"]["model_config_dict"]["tools"] == runtime_tools
        )
        assert log_data["request"]["model_config_dict"]["temperature"] == 0.9

    @pytest.mark.asyncio
    async def test_arun_logs_final_client_payload_model_config_dict(
        self, monkeypatch, tmp_path
    ):
        r"""Test arun logs final payload passed to the async client."""

        class FakeAsyncCompletions:
            async def create(self, **kwargs):
                return {"status": "ok", "request_keys": sorted(kwargs)}

        class FakeAsyncChat:
            def __init__(self):
                self.completions = FakeAsyncCompletions()

        class FakeAsyncClient:
            def __init__(self):
                self.chat = FakeAsyncChat()

        class DummyModel(BaseModelBackend):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._async_client = FakeAsyncClient()

            @property
            def token_counter(self):
                pass

            def _run(self, messages, response_format=None, tools=None):
                return {"status": "unused"}

            async def _arun(self, messages, response_format=None, tools=None):
                return await self._async_client.chat.completions.create(
                    messages=messages,
                    model=self.model_type,
                    tools=tools,
                    temperature=0.6,
                )

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "true")

        model = DummyModel(
            ModelType.GPT_4O_MINI,
            model_config_dict={"temperature": 0.1},
        )
        runtime_tools = [
            {
                "type": "function",
                "function": {"name": "search"},
            }
        ]

        await model.arun(
            messages=[{"role": "user", "content": "test async"}],
            tools=runtime_tools,
        )

        log_files = list(tmp_path.rglob("conv_*.json"))
        assert len(log_files) == 1

        with open(log_files[0], "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert (
            log_data["request"]["model_config_dict"]["tools"] == runtime_tools
        )
        assert log_data["request"]["model_config_dict"]["temperature"] == 0.6

    def test_run_logs_payload_from_positional_client_args(
        self, monkeypatch, tmp_path
    ):
        r"""Test positional client args are normalized into request logs."""

        class FakeCompletions:
            def create(
                self,
                messages,
                model,
                tools=None,
                temperature=None,
            ):
                return {"status": "ok", "model": str(model)}

        class FakeChat:
            def __init__(self):
                self.completions = FakeCompletions()

        class FakeClient:
            def __init__(self):
                self.chat = FakeChat()

        class DummyModel(BaseModelBackend):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._client = FakeClient()

            @property
            def token_counter(self):
                pass

            def _run(self, messages, response_format=None, tools=None):
                return self._client.chat.completions.create(
                    messages,
                    self.model_type,
                    tools,
                    0.7,
                )

            async def _arun(self, messages, response_format=None, tools=None):
                return {"status": "unused"}

        monkeypatch.setenv("CAMEL_MODEL_LOG_ENABLED", "true")
        monkeypatch.setenv("CAMEL_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED", "true")

        model = DummyModel(ModelType.GPT_4O_MINI, model_config_dict={})
        runtime_tools = [
            {
                "type": "function",
                "function": {"name": "positional_tool"},
            }
        ]

        model.run(
            messages=[{"role": "user", "content": "positional call"}],
            tools=runtime_tools,
        )

        log_files = list(tmp_path.rglob("conv_*.json"))
        assert len(log_files) == 1

        with open(log_files[0], "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert (
            log_data["request"]["model_config_dict"]["tools"] == runtime_tools
        )
        assert log_data["request"]["model_config_dict"]["temperature"] == 0.7

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

    def _make_completion(self, content, reasoning_content=None):
        r"""Helper to create a ChatCompletion with given content."""
        msg = ChatCompletionMessage(role='assistant', content=content)
        if reasoning_content is not None:
            msg.reasoning_content = reasoning_content
        return ChatCompletion(
            id='test',
            model='test',
            object='chat.completion',
            created=0,
            choices=[Choice(index=0, finish_reason='stop', message=msg)],
        )

    def _make_model(self, extract_thinking_from_response=True):
        r"""Helper to create a DummyModel for postprocess tests."""

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

        return DummyModel(
            ModelType.GPT_4O_MINI,
            extract_thinking_from_response=extract_thinking_from_response,
        )

    def test_postprocess_extracts_think_tags(self):
        r"""Test that postprocess_response extracts <think> tags into
        reasoning_content."""
        model = self._make_model()
        response = self._make_completion('<think>reasoning here</think>\n\n4')

        result = model.postprocess_response(response)
        assert result.choices[0].message.content == '4'
        assert result.choices[0].message.reasoning_content == 'reasoning here'

    def test_postprocess_multiline_think_tags(self):
        r"""Test extraction of multiline think tags."""
        model = self._make_model()
        response = self._make_completion(
            '<think>\nline1\nline2\n</think>\n\nanswer'
        )

        result = model.postprocess_response(response)
        assert result.choices[0].message.content == 'answer'
        assert result.choices[0].message.reasoning_content == 'line1\nline2'

    def test_postprocess_no_think_tags(self):
        r"""Test that content without think tags is unchanged."""
        model = self._make_model()
        response = self._make_completion('just a normal response')

        result = model.postprocess_response(response)
        assert result.choices[0].message.content == 'just a normal response'
        assert (
            getattr(result.choices[0].message, 'reasoning_content', None)
            is None
        )

    def test_postprocess_preserves_existing_reasoning_content(self):
        r"""Test that existing reasoning_content is not overridden."""
        model = self._make_model()
        response = self._make_completion(
            '<think>in content</think>\n\n4',
            reasoning_content='already set',
        )

        result = model.postprocess_response(response)
        # Content should NOT be cleaned since reasoning_content exists
        assert (
            result.choices[0].message.content
            == '<think>in content</think>\n\n4'
        )
        assert result.choices[0].message.reasoning_content == 'already set'

    @pytest.mark.parametrize("extract_thinking_from_response", [True, False])
    def test_think_tags(self, extract_thinking_from_response):
        r"""Test that extract_thinking_from_response controls both
        preprocessing (input) and postprocessing (output) of think tags."""
        model = self._make_model(
            extract_thinking_from_response=extract_thinking_from_response
        )

        # Test preprocessing
        messages = [
            {
                'role': 'assistant',
                'content': '<think>thinking</think>Response',
            },
            {
                'role': 'user',
                'content': 'Hello <think>thought</think> world',
            },
        ]
        processed = model.preprocess_messages(messages)

        # Test postprocessing
        response = self._make_completion('<think>reasoning here</think>\n\n4')
        result = model.postprocess_response(response)

        if extract_thinking_from_response:
            # Preprocessing: think tags should be stripped
            assert processed[0]['content'] == 'Response'
            assert processed[1]['content'] == 'Hello  world'
            # Postprocessing: think tags extracted into reasoning_content
            assert result.choices[0].message.content == '4'
            assert (
                result.choices[0].message.reasoning_content == 'reasoning here'
            )
        else:
            # Preprocessing: think tags should be preserved
            assert processed[0]['content'] == '<think>thinking</think>Response'
            assert (
                processed[1]['content'] == 'Hello <think>thought</think> world'
            )
            # Postprocessing: think tags should be preserved
            assert (
                result.choices[0].message.content
                == '<think>reasoning here</think>\n\n4'
            )
            assert (
                getattr(result.choices[0].message, 'reasoning_content', None)
                is None
            )

    def test_postprocess_multiple_think_tags(self):
        r"""Test extraction with multiple think tags in content."""
        model = self._make_model()
        response = self._make_completion(
            '<think>first thought</think> middle '
            '<think>second thought</think> end'
        )

        result = model.postprocess_response(response)
        assert result.choices[0].message.content == 'middle  end'
        assert result.choices[0].message.reasoning_content == 'first thought'

    def test_postprocess_empty_think_tags(self):
        r"""Test that empty think tags are stripped without setting
        reasoning_content."""
        model = self._make_model()
        response = self._make_completion('<think></think>content after')

        result = model.postprocess_response(response)
        assert result.choices[0].message.content == 'content after'

    def test_metaclass_postprocessing(self):
        r"""Test that metaclass wraps run with postprocessing."""

        class TestModel(BaseModelBackend):
            @property
            def token_counter(self):
                pass

            def run(self, messages, response_format=None, tools=None):
                return self._make_response()

            def _run(self, messages, response_format=None, tools=None):
                pass

            async def _arun(self, messages, response_format=None, tools=None):
                pass

            def _make_response(self):
                return ChatCompletion(
                    id='test',
                    model='test',
                    object='chat.completion',
                    created=0,
                    choices=[
                        Choice(
                            index=0,
                            finish_reason='stop',
                            message=ChatCompletionMessage(
                                role='assistant',
                                content='<think>thought</think>answer',
                            ),
                        )
                    ],
                )

        model = TestModel(ModelType.GPT_4O_MINI)
        result = model.run([{'role': 'user', 'content': 'test'}])

        # Metaclass should have applied postprocess_response
        assert result.choices[0].message.content == 'answer'
        assert result.choices[0].message.reasoning_content == 'thought'
