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
from PIL import Image

from camel.toolkits.async_browser_toolkit import (
    AsyncBaseBrowser,
    AsyncBrowserToolkit,
)

TEST_URL = "https://example.com"


@pytest.fixture
def dummy_playwright_setup():
    dummy_instance = (
        MagicMock()
    )  # This is the object returned by playwright.start()

    # Mock for non-persistent launch (browser object)
    dummy_browser_obj = MagicMock(name="BrowserObjectMock")
    dummy_instance.chromium = MagicMock()
    dummy_instance.chromium.launch = AsyncMock(return_value=dummy_browser_obj)
    dummy_browser_obj.close = AsyncMock()

    # Mock for context created from dummy_browser_obj
    dummy_context_from_browser = AsyncMock(name="ContextFromBrowserMock")
    dummy_browser_obj.new_context = AsyncMock(
        return_value=dummy_context_from_browser
    )
    dummy_context_from_browser.new_page = AsyncMock(
        return_value=MagicMock(name="PageFromContextFromBrowser")
    )
    dummy_context_from_browser.close = AsyncMock()

    # Mock for persistent context launch
    dummy_persistent_context = AsyncMock(name="PersistentContextMock")
    dummy_instance.chromium.launch_persistent_context = AsyncMock(
        return_value=dummy_persistent_context
    )
    dummy_persistent_context.pages = []  # Simulate no pre-existing pages
    # initially
    dummy_persistent_context.new_page = AsyncMock(
        return_value=MagicMock(name="PageFromPersistentContext")
    )
    dummy_persistent_context.close = AsyncMock()

    dummy_playwright_entry = MagicMock(
        name="PlaywrightEntryMock"
    )  # This is the playwright module itself
    dummy_playwright_entry.start = AsyncMock(return_value=dummy_instance)

    return dummy_playwright_entry


@pytest.fixture(scope="function")
async def async_base_browser_fixture(dummy_playwright_setup):
    with (
        patch(
            'playwright.async_api.async_playwright',
            return_value=dummy_playwright_setup,
        ),
        patch.object(
            AsyncBaseBrowser, '_ensure_browser_installed', AsyncMock()
        ),
    ):  # Mock install for all tests using this fixture
        browser = AsyncBaseBrowser(headless=True, cache_dir="test_cache")
        yield browser
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.fixture(scope="function")
async def async_browser_toolkit_fixture(dummy_playwright_setup):
    with (
        patch(
            'playwright.async_api.async_playwright',
            return_value=dummy_playwright_setup,
        ),
        patch.object(
            AsyncBaseBrowser, '_ensure_browser_installed', AsyncMock()
        ),
    ):
        toolkit = AsyncBrowserToolkit(headless=True, cache_dir="test_cache")
        yield toolkit
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.mark.asyncio
async def test_async_base_browser_init(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
    assert browser.headless is True
    assert browser.cache_dir == "test_cache"
    assert isinstance(browser.history, list)
    assert isinstance(browser.page_history, list)
    assert browser.user_data_dir is None  # Added for default user_data_dir


@pytest.mark.asyncio
async def test_async_base_browser_init_with_user_data_dir(
    dummy_playwright_setup,
):
    test_user_dir = "test_user_data_dir_async"
    browser = None  # Define browser outside try for finally block
    try:
        with (
            patch(
                'playwright.async_api.async_playwright',
                return_value=dummy_playwright_setup,
            ),
            patch.object(
                AsyncBaseBrowser, '_ensure_browser_installed', AsyncMock()
            ) as mock_ensure_installed,
        ):
            browser = AsyncBaseBrowser(
                headless=True, user_data_dir=test_user_dir
            )
            await browser.async_init()  # Call async_init before asserting mock
            mock_ensure_installed.assert_called_once()
            assert browser.user_data_dir == test_user_dir
            assert os.path.exists(test_user_dir)
    finally:
        if os.path.exists(test_user_dir):
            shutil.rmtree(test_user_dir)
        if (
            browser
            and hasattr(browser, 'playwright_started')
            and browser.playwright_started
        ):
            await browser.close()


@pytest.mark.asyncio
async def test_async_base_browser_initialization_order_async(
    async_base_browser_fixture, dummy_playwright_setup
):
    browser = async_base_browser_fixture  # await the fixture

    # Assert initial state (AsyncBaseBrowser __init__ doesn't set these up yet)
    assert browser.browser is None
    assert browser.page is None
    assert browser.context is None

    await browser.async_init()

    # Assertions for user_data_dir=None path
    mock_chromium_api = dummy_playwright_setup.start.return_value.chromium
    mock_chromium_api.launch.assert_called_once()

    # browser.browser should be the mocked browser object
    assert browser.browser == mock_chromium_api.launch.return_value
    # browser.context should be the context from the mocked browser object
    assert (
        browser.context
        == mock_chromium_api.launch.return_value.new_context.return_value
    )
    # browser.page should be the page from that context
    assert (
        browser.page
        == mock_chromium_api.launch.return_value.new_context.return_value.new_page.return_value
    )
    assert browser.page is not None


@pytest.mark.asyncio
# ruff: noqa: E501
async def test_async_base_browser_initialization_order_with_user_data_dir_async(
    dummy_playwright_setup,
):
    test_init_dir = "test_init_user_data_async"
    browser = None  # Define browser outside try for finally block
    try:
        with (
            patch(
                'playwright.async_api.async_playwright',
                return_value=dummy_playwright_setup,
            ),
            patch.object(
                AsyncBaseBrowser, '_ensure_browser_installed', AsyncMock()
            ) as mock_ensure_installed,
        ):
            browser = AsyncBaseBrowser(
                headless=True, user_data_dir=test_init_dir
            )
            # Assertions for __init__ behaviour
            mock_ensure_installed.assert_not_called()  # __init__ does not call it
            assert os.path.exists(test_init_dir)
            assert browser.browser is None
            assert browser.page is None
            assert browser.context is None

            await browser.async_init()
            mock_ensure_installed.assert_called_once()  # async_init calls it

            # Assertions for init() behaviour with user_data_dir
            mock_chromium_api = (
                dummy_playwright_setup.start.return_value.chromium
            )
            mock_chromium_api.launch_persistent_context.assert_called_once()

            call_kwargs = (
                mock_chromium_api.launch_persistent_context.call_args.kwargs
            )
            assert call_kwargs['user_data_dir'] == test_init_dir
            assert call_kwargs['headless'] is True
            assert call_kwargs['channel'] == "chromium"
            assert call_kwargs['accept_downloads'] is True
            assert isinstance(call_kwargs['user_agent'], str)
            assert call_kwargs['java_script_enabled'] is True
            assert isinstance(call_kwargs['args'], list)

            assert browser.browser is None  # Key: No separate browser object
            assert (
                browser.context
                == mock_chromium_api.launch_persistent_context.return_value
            )
            assert (
                browser.page
                == mock_chromium_api.launch_persistent_context.return_value.new_page.return_value
            )
    finally:
        if os.path.exists(test_init_dir):
            shutil.rmtree(test_init_dir)
        if (
            browser
            and hasattr(browser, 'playwright_started')
            and browser.playwright_started
        ):
            await browser.close()


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
    with (
        patch(
            'playwright.async_api.async_playwright',
            return_value=dummy_playwright_setup,
        ),
        patch.object(
            AsyncBaseBrowser, '_ensure_browser_installed', AsyncMock()
        ),
    ):  # Also mock install here for standalone test
        browser = AsyncBaseBrowser(headless=True, channel=channel)
        assert browser.channel == channel


@pytest.mark.asyncio
async def test_async_browser_visit_page(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
    await browser.async_init()

    browser_page = MagicMock()
    browser.page.goto = AsyncMock(return_value=browser_page)
    browser.page.wait_for_load_state = AsyncMock()

    await browser.visit_page(TEST_URL)

    browser.page.goto.assert_called_once_with(TEST_URL)
    browser.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_browser_get_screenshot(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
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
    toolkit = async_browser_toolkit_fixture  # await the fixture

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
    browser = async_base_browser_fixture  # await the fixture

    os.makedirs(browser.cache_dir, exist_ok=True)
    test_file = os.path.join(browser.cache_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    browser.clean_cache()
    assert not os.path.exists(browser.cache_dir)


@pytest.mark.asyncio
async def test_async_browser_click_blank_area(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
    await browser.async_init()

    browser.page.mouse.click = AsyncMock()
    browser.page.wait_for_load_state = AsyncMock()

    await browser.click_blank_area()

    browser.page.mouse.click.assert_called_once_with(0, 0)
    browser.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_browser_get_url(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
    await browser.async_init()

    browser.page.url = TEST_URL
    assert browser.get_url() == TEST_URL


@pytest.mark.asyncio
async def test_async_browser_back_navigation(async_base_browser_fixture):
    browser = async_base_browser_fixture  # await the fixture
    await browser.async_init()

    browser.page.go_back = AsyncMock()
    browser.page.wait_for_load_state = AsyncMock()

    await browser.back()

    browser.page.go_back.assert_called_once()
    browser.page.wait_for_load_state.assert_called_once()
