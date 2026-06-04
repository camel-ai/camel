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
import requests

from camel.toolkits import ZeroGPUToolkit


@pytest.fixture
def toolkit():
    return ZeroGPUToolkit(
        api_key="zgpu-api-test",
        project_id="test-project",
        base_url="https://api.zerogpu.ai"
    )


def mock_success_response(text_output):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "output": [
                    {
                        "content": [
                            {"text": text_output}
                        ]
                    }
                ]
            }

    return MockResponse()


def mock_post_success(*args, **kwargs):
    return mock_success_response('{"key": "value"}')


def mock_post_text(*args, **kwargs):
    return mock_success_response("some plain text response")


def mock_post_error(status_code):
    class MockResponse:
        def __init__(self):
            self.status_code = status_code
            self.text = "error"

    return MockResponse()


def test_get_tools(toolkit):
    tools = toolkit.get_tools()

    assert len(tools) == 11

    tool_names = {tool.func.__name__ for tool in tools}

    expected = {
        "chat",
        "chat_thinking",
        "summarize",
        "classify_iab",
        "classify_iab_enriched",
        "classify_zero_shot",
        "classify_structured",
        "extract_entities",
        "extract_json",
        "extract_pii",
        "redact_pii",
    }

    assert tool_names == expected


def test_invalid_api_key():
    with pytest.raises(ValueError):
        ZeroGPUToolkit(api_key="bad", project_id="test")


def test_chat(monkeypatch, toolkit):
    monkeypatch.setattr(requests, "post", mock_post_text)

    result = toolkit.chat("hello")

    assert isinstance(result, str)


def test_summarize(monkeypatch, toolkit):
    monkeypatch.setattr(requests, "post", mock_post_text)

    result = toolkit.summarize("text")

    assert isinstance(result, str)


def test_classify_iab(monkeypatch, toolkit):
    monkeypatch.setattr(requests, "post", mock_post_success)

    result = toolkit.classify_iab("text")

    assert isinstance(result, dict)


def test_classify_zero_shot(monkeypatch, toolkit):
    captured = {}

    def mock_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        return mock_success_response('{"sports": 0.9}')

    monkeypatch.setattr(requests, "post", mock_post)

    labels = ["sports", "finance"]
    toolkit.classify_zero_shot("text", labels)

    assert "categories" in captured["json"] or "instructions" in captured["json"]


def test_extract_pii_categories(monkeypatch, toolkit):
    captured = {}

    def mock_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        return mock_success_response('{"entities": []}')

    monkeypatch.setattr(requests, "post", mock_post)

    toolkit.extract_pii("text", threshold=0.5, categories=["email"])

    metadata = captured["json"]["metadata"]

    assert "categories" in metadata
    assert "threshold" in metadata


def test_redact_pii(monkeypatch, toolkit):
    captured = {}

    def mock_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        return mock_success_response(
            '{"redacted_text": "Hello [PERSON]"}'
        )

    monkeypatch.setattr(requests, "post", mock_post)

    result = toolkit.redact_pii("text")

    metadata = captured["json"]["metadata"]

    assert metadata["usecase"] == "redact"
    assert metadata["mask"] == "label"
    assert isinstance(result, str)


def test_error_mapping(monkeypatch, toolkit):
    def mock_post(*args, **kwargs):
        return mock_post_error(401)

    monkeypatch.setattr(requests, "post", mock_post)

    # dict-returning tool
    result_dict = toolkit.classify_iab("text")
    assert "error" in result_dict

    # str-returning tool
    result_str = toolkit.chat("text")
    assert isinstance(result_str, str)
    assert "Error" in result_str