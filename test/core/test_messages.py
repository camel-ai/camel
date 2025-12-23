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
from typing import cast

from camel.core.messages import (
    CamelContentPart,
    CamelMessage,
    OpenAIMessage,
    camel_messages_to_openai,
)


def test_camel_messages_to_openai_preserves_input_text_and_image() -> None:
    msg = CamelMessage(
        role="user",
        content=[
            CamelContentPart(type="input_text", payload={"text": "hello"}),
            CamelContentPart(
                type="input_image",
                payload={"url": "https://example.com/img.png"},
            ),
        ],
    )

    converted = camel_messages_to_openai([msg])

    assert len(converted) == 1
    content = converted[0]["content"]
    assert isinstance(content, list) and len(content) == 2

    text_part = content[0]
    image_part = content[1]

    assert text_part["type"] == "text"
    assert text_part["text"] == "hello"

    assert image_part["type"] == "image_url"
    assert image_part["image_url"]["url"] == "https://example.com/img.png"
    # default detail should be present to mirror Chat schema
    assert image_part["image_url"]["detail"] == "auto"


def test_openai_messages_to_camel_handles_input_image_dict() -> None:
    from camel.core.messages import openai_messages_to_camel

    messages = cast(
        list[OpenAIMessage],
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": {"url": "https://example.com/x.png"},
                    },
                ],
            }
        ],
    )

    camel_msgs = openai_messages_to_camel(messages)

    assert len(camel_msgs) == 1
    parts = camel_msgs[0].content
    assert len(parts) == 1
    assert parts[0].type == "input_image"
    assert parts[0].payload["url"] == "https://example.com/x.png"


def test_camel_messages_to_responses_request_preserves_assistant_role() -> (
    None
):
    from camel.core.messages import camel_messages_to_responses_request

    msg_user = CamelMessage(
        role="user",
        content=[CamelContentPart(type="input_text", payload={"text": "hi"})],
    )
    msg_assistant = CamelMessage(
        role="assistant",
        content=[
            CamelContentPart(type="input_text", payload={"text": "hello"})
        ],
    )

    body = camel_messages_to_responses_request([msg_user, msg_assistant])
    assert "input" in body
    assert body["input"][0]["role"] == "user"
    assert body["input"][1]["role"] == "assistant"


def test_tool_message_converted_to_function_call_output() -> None:
    from camel.core.messages import camel_messages_to_responses_request

    msg_tool = CamelMessage(
        role="tool",
        tool_call_id="call_123",
        content=[
            CamelContentPart(type="text", payload={"text": "result value"}),
        ],
    )

    body = camel_messages_to_responses_request([msg_tool])
    assert body["input"][0]["role"] == "assistant"
    frag = body["input"][0]["content"][0]
    assert frag["type"] == "function_call_output"
    assert frag["call_id"] == "call_123"
    assert frag["output"] == "result value"
