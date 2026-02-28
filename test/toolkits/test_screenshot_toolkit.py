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

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from camel.agents import ChatAgent
from camel.toolkits.screenshot_toolkit import ScreenshotToolkit


def test_read_image_uses_separate_vision_agent():
    """Verify read_image delegates to a dedicated vision agent, not the
    calling agent, to prevent re-entrant step() calls that corrupt the
    tool-call message sequence.

    Regression test for https://github.com/camel-ai/camel/issues/3869.
    """
    toolkit = ScreenshotToolkit.__new__(ScreenshotToolkit)
    toolkit.screenshots_dir = Path(tempfile.mkdtemp())
    toolkit._vision_agent = None

    # Create a small test image
    from PIL import Image

    img_path = toolkit.screenshots_dir / "test.png"
    Image.new("RGB", (10, 10), color="red").save(str(img_path))

    # Mock the registered agent (the calling agent)
    mock_agent = MagicMock(spec=ChatAgent)
    mock_agent.agent_id = "caller"
    mock_agent.model_backend = MagicMock()
    toolkit._agent = mock_agent

    # Pre-inject a mock vision agent to avoid building a real ChatAgent
    mock_vision_agent = MagicMock(spec=ChatAgent)
    mock_vision_response = MagicMock()
    mock_vision_response.msgs = [MagicMock(content="Image analysis result")]
    mock_vision_agent.step.return_value = mock_vision_response
    toolkit._vision_agent = mock_vision_agent

    result = toolkit.read_image(str(img_path), "describe this")

    # The calling agent's step() must NOT be called
    mock_agent.step.assert_not_called()

    # The vision agent's step() should have been called instead
    mock_vision_agent.step.assert_called_once()
    assert result == "Image analysis result"
