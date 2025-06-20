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
import io
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from PIL import Image

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.toolkits.async_browser_toolkit import (
    AsyncBaseBrowser,
    AsyncBrowserToolkit,
)

TEST_URL = "https://example.com"


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyResp:
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return self._value

    @property
    def text(self):
        return self._value


@pytest_asyncio.fixture
async def dummy_playwright_setup():
    dummy_instance = MagicMock()
    dummy_browser = MagicMock()
    dummy_context = MagicMock()
    dummy_page = MagicMock()

    dummy_instance.chromium = MagicMock()
    dummy_instance.chromium.launch = AsyncMock(return_value=dummy_browser)
    dummy_instance.chromium.launch_persistent_context = AsyncMock(
        return_value=dummy_context
    )
    dummy_instance.stop = AsyncMock()

    dummy_browser.new_context = AsyncMock(return_value=dummy_context)
    dummy_browser.close = AsyncMock()

    dummy_context.new_page = AsyncMock(return_value=dummy_page)
    dummy_context.pages = []
    dummy_context.close = AsyncMock()

    dummy_playwright = MagicMock()
    dummy_playwright.start = AsyncMock(return_value=dummy_instance)

    return dummy_playwright


@pytest_asyncio.fixture(scope="function")
async def async_base_browser_fixture(tmp_path, dummy_playwright_setup):
    with patch(
        'playwright.async_api.async_playwright',
        return_value=dummy_playwright_setup,
    ):
        browser = AsyncBaseBrowser(headless=True, cache_dir=str(tmp_path))
        yield browser
        shutil.rmtree(str(tmp_path), ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def async_browser_toolkit_fixture(tmp_path, dummy_playwright_setup):
    with patch(
        'playwright.async_api.async_playwright',
        return_value=dummy_playwright_setup,
    ):
        toolkit = AsyncBrowserToolkit(headless=True, cache_dir=str(tmp_path))
        yield toolkit
        shutil.rmtree(str(tmp_path), ignore_errors=True)


@pytest.mark.asyncio
async def test_async_base_browser_init(async_base_browser_fixture):
    browser = async_base_browser_fixture
    assert browser.headless is True
    assert isinstance(browser.cache_dir, str)
    assert isinstance(browser.history, list)
    assert isinstance(browser.page_history, list)


@pytest.mark.asyncio
async def test_async_base_browser_initialization_order_async(
    async_base_browser_fixture,
):
    browser = async_base_browser_fixture
    assert browser.browser is None
    assert browser.page is None
    await browser.async_init()
    assert browser.browser is not None
    assert browser.page is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["chrome", "msedge", "chromium"])
async def test_async_browser_channel_selection(
    channel, dummy_playwright_setup
):
    with patch(
        'playwright.async_api.async_playwright',
        return_value=dummy_playwright_setup,
    ):
        browser = AsyncBaseBrowser(headless=True, channel=channel)
        assert browser.channel == channel


@pytest.mark.asyncio
async def test_async_browser_visit_page(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.goto = AsyncMock()
    browser.page.wait_for_load_state = AsyncMock()
    await browser.visit_page(TEST_URL)
    browser.page.goto.assert_called_once_with(TEST_URL)
    browser.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_browser_get_screenshot(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    browser.page.screenshot = AsyncMock(return_value=img_bytes)
    image, file_path = await browser.async_get_screenshot(save_image=False)
    assert isinstance(image, Image.Image)
    assert file_path is None


@pytest.mark.asyncio
async def test_async_browser_toolkit_browse_url(async_browser_toolkit_fixture):
    toolkit = async_browser_toolkit_fixture
    mock_response_plan = ChatAgentResponse(
        msgs=[
            BaseMessage(
                role_name="assistant",
                role_type="assistant",
                meta_dict=None,
                content="1. Restate the task\n2. Make a plan",
            )
        ],
        terminated=False,
        info={},
    )
    mock_response_final = ChatAgentResponse(
        msgs=[
            BaseMessage(
                role_name="assistant",
                role_type="assistant",
                meta_dict=None,
                content="Task completed",
            )
        ],
        terminated=False,
        info={},
    )
    toolkit.planning_agent.astep = AsyncMock(
        side_effect=[mock_response_plan, mock_response_final]
    )
    toolkit.browser.visit_page = AsyncMock()
    toolkit.async_observe = AsyncMock(return_value=("obs", "reason", "stop()"))

    result = await toolkit.browse_url(
        task_prompt="Test task", start_url=TEST_URL, round_limit=1
    )
    assert result == "Task completed"
    toolkit.browser.visit_page.assert_called_once_with(TEST_URL)


@pytest.mark.asyncio
async def test_async_browser_clean_cache(async_base_browser_fixture):
    browser = async_base_browser_fixture
    os.makedirs(browser.cache_dir, exist_ok=True)
    test_file = os.path.join(browser.cache_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    browser.clean_cache()
    assert not os.path.exists(browser.cache_dir)


@pytest.mark.asyncio
async def test_async_browser_click_blank_area(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.mouse.click = AsyncMock()
    browser.page.wait_for_load_state = AsyncMock()
    await browser.click_blank_area()
    browser.page.mouse.click.assert_called_once_with(0, 0)
    browser.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_browser_get_url(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.url = TEST_URL
    assert browser.get_url() == TEST_URL


@pytest.mark.asyncio
async def test_async_browser_back_navigation(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.go_back = AsyncMock()
    browser.page.wait_for_load_state = AsyncMock()
    await browser.back()
    browser.page.go_back.assert_called_once()
    browser.page.wait_for_load_state.assert_called_once()
