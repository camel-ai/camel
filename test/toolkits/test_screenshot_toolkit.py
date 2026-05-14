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

from unittest.mock import MagicMock, patch

from PIL import Image

from camel.toolkits.screenshot_toolkit import ScreenshotToolkit


def test_read_image_uses_helper_agent_instead_of_registered_parent_agent(
    tmp_path,
):
    r"""Test image reading avoids re-entering the registered parent agent."""
    image_path = tmp_path / "screenshot.png"
    Image.new("RGB", (1, 1)).save(image_path)

    parent_agent = MagicMock()
    parent_agent.model_backend = MagicMock()
    parent_agent.output_language = "Chinese"
    parent_agent.step.side_effect = AssertionError("parent re-entered")

    helper_agent = MagicMock()
    helper_agent.step.return_value.msgs = [MagicMock(content="visible text")]

    toolkit = ScreenshotToolkit(working_directory=str(tmp_path))
    toolkit.register_agent(parent_agent)

    with patch(
        "camel.agents.ChatAgent", return_value=helper_agent
    ) as chat_agent:
        result = toolkit.read_image(str(image_path), "read it")

    assert result == "visible text"
    parent_agent.step.assert_not_called()
    helper_agent.step.assert_called_once()
    helper_agent.reset.assert_called_once()

    chat_agent.assert_called_once()
    _, kwargs = chat_agent.call_args
    assert kwargs["model"] is parent_agent.model_backend
    assert kwargs["output_language"] == "Chinese"


def test_read_image_creates_isolated_helper_agent_for_each_read(tmp_path):
    r"""Test each image read gets a fresh helper agent."""
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    Image.new("RGB", (1, 1)).save(first_path)
    Image.new("RGB", (1, 1)).save(second_path)

    parent_agent = MagicMock()
    parent_agent.model_backend = MagicMock()
    parent_agent.output_language = None

    first_helper = MagicMock()
    first_helper.step.return_value.msgs = [MagicMock(content="first")]
    second_helper = MagicMock()
    second_helper.step.return_value.msgs = [MagicMock(content="second")]

    toolkit = ScreenshotToolkit(working_directory=str(tmp_path))
    toolkit.register_agent(parent_agent)

    with patch(
        "camel.agents.ChatAgent",
        side_effect=[first_helper, second_helper],
    ) as chat_agent:
        assert toolkit.read_image(str(first_path)) == "first"
        assert toolkit.read_image(str(second_path)) == "second"

    assert chat_agent.call_count == 2
    first_helper.reset.assert_called_once()
    second_helper.reset.assert_called_once()
