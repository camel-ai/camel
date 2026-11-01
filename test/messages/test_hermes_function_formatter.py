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
import logging

from camel.messages.conversion.sharegpt.hermes.hermes_function_formatter import (
    HermesFunctionFormatter,
)


def test_extract_tool_calls_invalid_json_logs_warning(caplog):
    r"""Test that invalid tool call JSON triggers a warning log
    instead of a print statement."""
    formatter = HermesFunctionFormatter()
    message = "<tool_call>\n{invalid json}\n</tool_call>"

    with caplog.at_level(logging.WARNING):
        result = formatter.extract_tool_calls(message)

    assert result == []
    assert "Failed to parse tool call" in caplog.text


def test_extract_tool_response_invalid_json_logs_warning(caplog):
    r"""Test that invalid tool response JSON triggers a warning log
    instead of a print statement."""
    formatter = HermesFunctionFormatter()
    message = "<tool_response>\n{invalid json}\n</tool_response>"

    with caplog.at_level(logging.WARNING):
        result = formatter.extract_tool_response(message)

    assert result is None
    assert "Failed to parse tool response" in caplog.text


def test_extract_tool_calls_valid_json():
    r"""Test that valid tool calls are extracted correctly."""
    formatter = HermesFunctionFormatter()
    message = (
        '<tool_call>\n{"name": "add", "arguments": {"a": 1, "b": 2}}'
        "\n</tool_call>"
    )

    result = formatter.extract_tool_calls(message)

    assert len(result) == 1
    assert result[0].name == "add"
    assert result[0].arguments == {"a": 1, "b": 2}
