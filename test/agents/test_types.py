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

from camel.agents._types import ToolCallRequest


def test_tool_call_request_preserves_long_id():
    r"""ToolCallRequest no longer truncates; truncation is platform-specific."""
    long_id = "call_" + "a" * 50  # 55 chars
    req = ToolCallRequest(
        tool_name="test_func",
        args={},
        tool_call_id=long_id,
    )
    assert req.tool_call_id == long_id
    assert len(req.tool_call_id) == 55


def test_tool_call_request_preserves_short_id():
    r"""Tool call IDs within 40 chars should not be modified."""
    short_id = "call_abc123"
    req = ToolCallRequest(
        tool_name="test_func",
        args={},
        tool_call_id=short_id,
    )
    assert req.tool_call_id == short_id
