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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from PIL import Image

from camel.toolkits.async_browser_toolkit import (
    AsyncBaseBrowser,
    AsyncBrowserToolkit,
)

TEST_URL = "https://example.com"


@pytest.fixture
def dummy_playwright_setup():
    dummy_instance = MagicMock()

    dummy_browser = MagicMock()
    dummy_instance.chromium = MagicMock()
    dummy_instance.chromium.launch = AsyncMock(return_value=dummy_browser)

    dummy_context = MagicMock()
    dummy_browser.new_context = AsyncMock(return_value=dummy_context)
    dummy_browser.close = AsyncMock()

    dummy_page = MagicMock()
    dummy_context.new_page = AsyncMock(return_value=dummy_page)

    dummy_playwright = MagicMock()
    dummy_playwright.start = AsyncMock(return_value=dummy_instance)

    return dummy_playwright


@pytest_asyncio.fixture(scope="function")
async def async_base_browser_fixture(dummy_playwright_setup):
    with patch(
        'playwright.async_api.async_playwright',
        return_value=dummy_playwright_setup,
    ):
        browser = AsyncBaseBrowser(headless=True, cache_dir="test_cache")
        yield browser
        if os.path.exists("test_cache"):
            os.rmdir("test_cache")


@pytest_asyncio.fixture(scope="function")
async def async_browser_toolkit_fixture(dummy_playwright_setup):
    with patch(
        'playwright.async_api.async_playwright',
        return_value=dummy_playwright_setup,
    ):
        toolkit = AsyncBrowserToolkit(headless=True, cache_dir="test_cache")
        yield toolkit
        if os.path.exists("test_cache"):
            os.rmdir("test_cache")


@pytest.mark.asyncio
async def test_async_base_browser_init(async_base_browser_fixture):
    browser = async_base_browser_fixture
    assert browser.headless is True
    assert browser.cache_dir == "test_cache"
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
@pytest.mark.parametrize(
    "channel",
    [
        "chrome",
        "msedge",
        "chromium",
    ],
)
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

    browser_page = MagicMock()
    browser.page.goto = AsyncMock(return_value=browser_page)
    browser.page.wait_for_load_state = AsyncMock()

    await browser.visit_page(TEST_URL)

    browser.page.goto.assert_called_once_with(TEST_URL)
    browser.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_browser_get_screenshot(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create a dummy image and its byte representation
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

    class DummyMessage:
        def __init__(self, content):
            self.content = content

    class DummyResp:
        def __init__(self, content):
            self.msgs = [DummyMessage(content)]

    toolkit.planning_agent.step = MagicMock(
        return_value=DummyResp("1. Restate the task\n2. Make a plan")
    )

    toolkit.browser.visit_page = AsyncMock()
    toolkit.async_observe = AsyncMock(return_value=("obs", "reason", "stop()"))
    toolkit._get_final_answer = MagicMock(return_value="Task completed")

    # 4) 调用并断言
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
