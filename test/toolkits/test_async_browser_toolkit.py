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
import asyncio
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

    # Add AsyncMock for is_closed method
    dummy_page.is_closed = AsyncMock(return_value=False)

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
    # Add this line to mock the _async_get_final_answer method
    toolkit._async_get_final_answer = AsyncMock(return_value="Task completed")

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


@pytest.mark.asyncio
async def test_async_base_browser_multi_tab_initialization(
    async_base_browser_fixture,
):
    """Test that multi-tab support is properly initialized."""
    browser = async_base_browser_fixture
    await browser.async_init()

    assert hasattr(browser, 'tabs')
    assert isinstance(browser.tabs, dict)

    assert hasattr(browser, 'current_tab_id')
    assert browser.current_tab_id == 0

    assert 0 in browser.tabs
    assert browser.tabs[0] == browser.page


@pytest.mark.asyncio
async def test_async_switch_tab_invalid_id(async_base_browser_fixture):
    """Test that switching to an invalid tab ID raises an error."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Set up tabs with only tab 0
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    # Test switching to non-existent tab
    with pytest.raises(ValueError, match="Tab 5 does not exist"):
        await browser.async_switch_tab(5)


@pytest.mark.asyncio
async def test_async_close_tab(async_base_browser_fixture):
    """Test closing a tab."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed = AsyncMock(return_value=False)
    mock_page_1.is_closed = AsyncMock(return_value=False)
    mock_page_2.is_closed = AsyncMock(return_value=False)

    # Configure close method to be AsyncMock
    mock_page_0.close = AsyncMock()
    mock_page_1.close = AsyncMock()
    mock_page_2.close = AsyncMock()

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}

    await browser.async_switch_tab(1)

    # Test closing tab 2 (not the current tab)
    await browser.async_close_tab(2)

    # Verify tab 2 is removed
    assert 2 not in browser.tabs
    assert browser.current_tab_id == 1  # Current tab unchanged
    assert browser.page == mock_page_1  # Page unchanged

    # Verify tab 2 was closed
    mock_page_2.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_close_current_tab(async_base_browser_fixture):
    """Test closing the current tab and switching to another tab."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed = AsyncMock(return_value=False)
    mock_page_1.is_closed = AsyncMock(return_value=False)
    mock_page_2.is_closed = AsyncMock(return_value=False)

    # Configure close method to be AsyncMock
    mock_page_0.close = AsyncMock()
    mock_page_1.close = AsyncMock()
    mock_page_2.close = AsyncMock()

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    await browser.async_switch_tab(1)  # Currently on tab 1

    # Test closing current tab (tab 1)
    await browser.async_close_tab(1)

    # Verify tab 1 is removed
    assert 1 not in browser.tabs

    # Verify current tab switched to the first remaining tab (tab 0)
    assert browser.current_tab_id == 0
    assert browser.page == mock_page_0

    # Verify tab 1 was closed
    mock_page_1.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_close_last_tab(async_base_browser_fixture):
    """Test closing the last remaining tab."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Set up only one tab
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    # Configure close method to be AsyncMock
    browser.page.close = AsyncMock()

    page_to_close = browser.page
    # Test closing the last tab
    await browser.async_close_tab(0)

    # Verify tab is removed
    assert 0 not in browser.tabs

    # Verify current tab is reset
    assert browser.current_tab_id is None
    assert browser.page is None

    # Verify page was closed
    page_to_close.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_close_tab_invalid_id(async_base_browser_fixture):
    """Test that closing an invalid tab ID raises an error."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Set up tabs with only tab 0
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    # Test closing non-existent tab
    with pytest.raises(ValueError, match="This tab does not exist"):
        await browser.async_close_tab(3)


@pytest.mark.asyncio
async def test_async_multi_tab_integration(async_base_browser_fixture):
    """Test a complete multi-tab workflow."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Configure the original page's is_closed method
    browser.page.is_closed = AsyncMock(return_value=False)
    browser.page.close = AsyncMock()

    # Mock context and page creation
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    browser.context.new_page = AsyncMock(
        side_effect=[mock_page_1, mock_page_2]
    )

    for mock_page in [mock_page_1, mock_page_2]:
        mock_page.goto = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)

    # Step 1: Open first new tab
    tab1_id = await browser.async_open_tab("https://example1.com")
    assert tab1_id == 1
    assert browser.tabs[1] == mock_page_1

    # Step 2: Open second new tab
    tab2_id = await browser.async_open_tab("https://example2.com")
    assert tab2_id == 2
    assert browser.tabs[2] == mock_page_2

    # Step 3: Switch to tab 1
    await browser.async_switch_tab(1)
    assert browser.current_tab_id == 1
    assert browser.page == mock_page_1

    # Step 4: Switch to tab 2
    await browser.async_switch_tab(2)
    assert browser.current_tab_id == 2
    assert browser.page == mock_page_2

    # Step 5: Close tab 1
    await browser.async_close_tab(1)
    assert 1 not in browser.tabs
    assert browser.current_tab_id == 2  # Should stay on current tab

    # Step 6: Close current tab (tab 2)
    await browser.async_close_tab(2)
    assert 2 not in browser.tabs
    assert browser.current_tab_id == 0  # Should switch to remaining tab
    assert browser.page == browser.tabs[0]  # Should be the original page


@pytest.mark.asyncio
async def test_async_browser_toolkit_reset_multi_tab(
    async_browser_toolkit_fixture,
):
    """Test that _reset properly clears multi-tab state."""
    toolkit = async_browser_toolkit_fixture

    # Initialize browser and add some tabs
    await toolkit.browser.async_init()
    toolkit.browser.tabs = {
        0: toolkit.browser.page,
        1: MagicMock(),
        2: MagicMock(),
    }
    toolkit.browser.current_tab_id = 2

    # Call _reset
    await toolkit._reset()

    # Verify tabs are cleared
    assert toolkit.browser.tabs == {}
    assert toolkit.browser.current_tab_id is None


@pytest.mark.asyncio
async def test_async_browse_url_with_multi_tab_info(
    async_browser_toolkit_fixture,
):
    """Test that browse_url includes multi-tab information in trajectory."""
    toolkit = async_browser_toolkit_fixture

    # Mock necessary components
    toolkit.browser.visit_page = AsyncMock()
    toolkit.async_observe = AsyncMock(return_value=("obs", "reason", "stop()"))
    toolkit.async_get_final_answer = AsyncMock(return_value="Task completed")

    # Set up some tabs
    toolkit.browser.tabs = {0: toolkit.browser.page, 1: MagicMock()}
    toolkit.browser.current_tab_id = 1

    result = await toolkit.browse_url(
        task_prompt="Test task", start_url=TEST_URL, round_limit=1
    )

    assert result is not None
    # Verify the trajectory includes multi-tab info
    assert len(toolkit.history) == 1
    trajectory = toolkit.history[0]
    assert "current_tab_id" in trajectory
    assert "open_tabs" in trajectory
    # The current_tab_id should be 0 because browse_url resets the tab_id
    assert trajectory["current_tab_id"] == 0
    assert trajectory["open_tabs"] == [0]


@pytest.mark.asyncio
async def test_async_open_tab_with_user_data_dir(dummy_playwright_setup):
    """Test opening tabs with user data directory setup."""
    test_user_dir = "test_user_data_dir_async"
    try:
        with patch(
            'playwright.async_api.async_playwright',
            return_value=dummy_playwright_setup,
        ):
            # Mock _ensure_browser_installed to prevent actual browser checks
            with patch.object(
                AsyncBaseBrowser, 'async_ensure_browser_installed', AsyncMock()
            ) as mock_ensure_installed:
                browser = AsyncBaseBrowser(
                    headless=True, user_data_dir=test_user_dir
                )
                # Call async_init to trigger the ensure_browser_installed call
                await browser.async_init()
                mock_ensure_installed.assert_called_once()
                assert browser.user_data_dir == test_user_dir
                assert os.path.exists(
                    test_user_dir
                )  # Check if __init__ created it
    finally:
        if os.path.exists(test_user_dir):
            shutil.rmtree(test_user_dir)


@pytest.mark.asyncio
async def test_async_tab_id_lock_safety(async_base_browser_fixture):
    """Test that tab ID generation is thread-safe with async lock."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock the context and page creation - provide enough pages
    # for both initial test and stress test
    mock_pages = [
        MagicMock() for _ in range(30)
    ]  # 10 for initial + 20 for stress test
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

    # Create a list to track the order of tab ID assignments
    tab_id_order = []

    # Create a custom async function that records when tab
    #  IDs are assigned
    async def open_tab_and_record(url: str):
        # Add a small delay to increase chance of race conditions
        await asyncio.sleep(0.01)
        tab_id = await browser.async_open_tab(url)
        tab_id_order.append(tab_id)
        return tab_id

    urls = [
        "https://example1.com",
        "https://example2.com",
        "https://example3.com",
        "https://example4.com",
        "https://example5.com",
        "https://example6.com",
        "https://example7.com",
        "https://example8.com",
        "https://example9.com",
        "https://example10.com",
    ]

    # Create all tasks simultaneously to maximize race condition potential
    tasks = [open_tab_and_record(url) for url in urls]

    # Execute all tasks concurrently
    tab_ids = await asyncio.gather(*tasks)

    # Verify all tab IDs are unique
    # (no race conditions caused duplicates)
    assert len(set(tab_ids)) == len(
        tab_ids
    ), "Race condition detected: duplicate tab IDs"

    # Verify tab IDs are sequential (lock is working properly)
    assert sorted(tab_ids) == list(
        range(1, len(tab_ids) + 1)
    ), "Tab IDs are not sequential"

    # Verify all tabs are in the tabs dictionary
    for tab_id in tab_ids:
        assert (
            tab_id in browser.tabs
        ), f"Tab {tab_id} not found in tabs dictionary"

    # Verify the total number of tabs is correct
    assert (
        len(browser.tabs) == len(tab_ids) + 1
    ), "Incorrect total number of tabs"  # +1 for original tab

    # Test that the lock prevents concurrent access to the tab ID counter
    # by creating a scenario where multiple operations try to
    #  access the counter simultaneously
    async def stress_test_lock():
        # Capture the current max tab id before opening new tabs
        current_max_tab_id = max(browser.tabs.keys())
        # Create many concurrent operations that all try to access
        #  the tab ID counter
        stress_tasks = []
        for i in range(20):
            task = asyncio.create_task(
                open_tab_and_record(f"https://stress{i}.com")
            )
            stress_tasks.append(task)

        stress_results = await asyncio.gather(*stress_tasks)

        # Verify no duplicates in stress test
        assert len(set(stress_results)) == len(
            stress_results
        ), "Race condition in stress test"

        # Verify sequential IDs in stress test
        #  (should start from current_max_tab_id + 1)
        expected_start = current_max_tab_id + 1
        expected_ids = list(
            range(expected_start, expected_start + len(stress_results))
        )
        assert (
            sorted(stress_results) == expected_ids
        ), "Non-sequential IDs in stress test"

        return stress_results

    # Run the stress test
    stress_tab_ids = await stress_test_lock()

    # Verify that stress test results don't conflict with original results
    all_tab_ids = tab_ids + stress_tab_ids
    assert len(set(all_tab_ids)) == len(
        all_tab_ids
    ), "Conflict between original and stress test tab IDs"


@pytest.mark.asyncio
async def test_async_open_tab_navigation_failure(async_base_browser_fixture):
    """Test opening a tab when navigation fails."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock the context and page creation
    mock_new_page = MagicMock()
    browser.context.new_page = AsyncMock(return_value=mock_new_page)
    mock_new_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
    mock_new_page.close = AsyncMock()

    # Test opening a tab with navigation failure
    with pytest.raises(ValueError, match="Failed to navigate to"):
        await browser.async_open_tab("https://invalid-url.com")

    # Verify the page was closed after navigation failure
    mock_new_page.close.assert_called_once()

    # Verify no new tab was added to tabs dictionary
    assert len(browser.tabs) == 1  # Only the original tab
    assert 0 in browser.tabs  # Only tab 0 exists


@pytest.mark.asyncio
async def test_concurrent_tab_operations(async_base_browser_fixture):
    """Test concurrent tab operations to verify thread safety."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock the context and page creation
    mock_pages = [MagicMock() for _ in range(10)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()

    # Create concurrent tasks for opening tabs
    async def open_tab_concurrently(url: str):
        return await browser.async_open_tab(url)

    urls = [f"https://example{i}.com" for i in range(10)]
    tasks = [open_tab_concurrently(url) for url in urls]

    # Execute all tasks concurrently
    tab_ids = await asyncio.gather(*tasks)

    # Verify all tab IDs are unique and sequential
    assert len(set(tab_ids)) == len(tab_ids)  # All unique
    assert sorted(tab_ids) == list(range(1, len(tab_ids) + 1))  # Sequential

    # Verify all tabs are in the tabs dictionary
    for tab_id in tab_ids:
        assert tab_id in browser.tabs

    # Test concurrent switching between tabs
    async def switch_tab_concurrently(tab_id: int):
        await browser.async_switch_tab(tab_id)
        return browser.current_tab_id

    switch_tasks = [switch_tab_concurrently(tab_id) for tab_id in tab_ids[:5]]
    current_tab_ids = await asyncio.gather(*switch_tasks)

    # Verify switching worked correctly
    assert len(set(current_tab_ids)) == len(current_tab_ids)  # All unique


@pytest.mark.asyncio
async def test_tab_recovery_after_failure(async_base_browser_fixture):
    """Test recovery behavior when tab operations fail mid-process."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock the context and page creation
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    browser.context.new_page = AsyncMock(
        side_effect=[mock_page_1, mock_page_2]
    )

    for mock_page in [mock_page_1, mock_page_2]:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()

    # Open first tab successfully
    tab1_id = await browser.async_open_tab("https://example1.com")
    assert tab1_id == 1

    # Simulate a failure during second tab opening
    mock_page_2.goto.side_effect = Exception("Network error")
    mock_page_2.close = AsyncMock()

    # Test that failure is handled gracefully
    with pytest.raises(ValueError, match="Failed to navigate to"):
        await browser.async_open_tab("https://example2.com")

    # Verify the failed page was closed
    mock_page_2.close.assert_called_once()

    # Verify browser state is still consistent
    assert len(browser.tabs) == 2  # Original tab + tab 1
    assert 0 in browser.tabs
    assert 1 in browser.tabs
    assert browser.current_tab_id == 0  # Should remain on original tab

    # Test recovery by opening a new tab successfully
    mock_page_3 = MagicMock()
    browser.context.new_page = AsyncMock(return_value=mock_page_3)
    mock_page_3.goto = AsyncMock()
    mock_page_3.wait_for_load_state = AsyncMock()
    mock_page_3.is_closed = AsyncMock(return_value=False)

    tab3_id = await browser.async_open_tab("https://example3.com")
    assert tab3_id == 2  # Should get next available ID
    assert 2 in browser.tabs


@pytest.mark.asyncio
async def test_multi_tab_persistent_context(dummy_playwright_setup):
    """Test multi-tab functionality with persistent context."""
    test_user_dir = "test_persistent_context_async"
    try:
        with patch(
            'playwright.async_api.async_playwright',
            return_value=dummy_playwright_setup,
        ):
            with patch.object(
                AsyncBaseBrowser, 'async_ensure_browser_installed', AsyncMock()
            ):
                browser = AsyncBaseBrowser(
                    headless=True, user_data_dir=test_user_dir
                )
                await browser.async_init()

                # Mock persistent context behavior
                mock_page_1 = MagicMock()
                mock_page_2 = MagicMock()
                browser.context.new_page = AsyncMock(
                    side_effect=[mock_page_1, mock_page_2]
                )

                for mock_page in [mock_page_1, mock_page_2]:
                    mock_page.goto = AsyncMock()
                    mock_page.wait_for_load_state = AsyncMock()
                    mock_page.is_closed = AsyncMock(return_value=False)

                # Test opening tabs with persistent context
                tab1_id = await browser.async_open_tab("https://example1.com")
                tab2_id = await browser.async_open_tab("https://example2.com")

                assert tab1_id == 1
                assert tab2_id == 2
                assert browser.user_data_dir == test_user_dir

                # Verify tabs are properly managed
                assert 1 in browser.tabs
                assert 2 in browser.tabs
                assert browser.tabs[1] == mock_page_1
                assert browser.tabs[2] == mock_page_2

    finally:
        if os.path.exists(test_user_dir):
            shutil.rmtree(test_user_dir)


@pytest.mark.asyncio
async def test_multi_tab_navigation_scenarios(async_base_browser_fixture):
    """Test complex navigation scenarios with multiple tabs."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock pages for different domains
    mock_pages = [MagicMock() for _ in range(5)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for i, mock_page in enumerate(mock_pages):
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_page.url = f"https://domain{i}.com"

    # Open tabs to different domains
    urls = [
        "https://google.com",
        "https://github.com",
        "https://stackoverflow.com",
        "https://reddit.com",
        "https://wikipedia.org",
    ]

    tab_ids = []
    for url in urls:
        tab_id = await browser.async_open_tab(url)
        tab_ids.append(tab_id)

    # Test switching between tabs and verify URL tracking
    for i, tab_id in enumerate(tab_ids):
        await browser.async_switch_tab(tab_id)
        assert browser.current_tab_id == tab_id
        assert browser.page == browser.tabs[tab_id]
        # Verify the page navigated to the correct URL
        browser.page.goto.assert_called_with(urls[i])

    # Test navigation within a specific tab
    await browser.async_switch_tab(tab_ids[0])
    browser.page.goto = AsyncMock()  # Reset mock for new navigation
    await browser.visit_page("https://google.com/search")
    browser.page.goto.assert_called_with("https://google.com/search")


@pytest.mark.asyncio
async def test_many_tabs_performance(async_base_browser_fixture):
    """Test performance with many tabs."""
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.is_closed = AsyncMock(return_value=False)

    # Mock many pages
    num_tabs = 20
    mock_pages = [MagicMock() for _ in range(num_tabs)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()

    # Measure time to open many tabs
    start_time = asyncio.get_event_loop().time()

    tab_ids = []
    for i in range(num_tabs):
        tab_id = await browser.async_open_tab(f"https://example{i}.com")
        tab_ids.append(tab_id)

    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time

    # Verify all tabs were created
    assert len(tab_ids) == num_tabs
    assert len(browser.tabs) == num_tabs + 1  # +1 for original tab

    # Verify performance is reasonable (should complete in under 5 seconds)
    assert total_time < 5.0

    # Test switching performance
    switch_start_time = asyncio.get_event_loop().time()

    for tab_id in tab_ids:
        await browser.async_switch_tab(tab_id)
        assert browser.current_tab_id == tab_id

    switch_end_time = asyncio.get_event_loop().time()
    switch_total_time = switch_end_time - switch_start_time

    # Verify switching is fast
    assert switch_total_time < 2.0

    # Test closing many tabs
    close_start_time = asyncio.get_event_loop().time()

    for tab_id in reversed(tab_ids):
        await browser.async_close_tab(tab_id)

    close_end_time = asyncio.get_event_loop().time()
    close_total_time = close_end_time - close_start_time

    # Verify closing is fast
    assert close_total_time < 2.0
    assert len(browser.tabs) == 1  # Only original tab remains


@pytest.mark.asyncio
async def test_multi_tab_state_persistence(async_base_browser_fixture):
    """Test that tab state is properly maintained across operations."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock pages
    mock_pages = [MagicMock() for _ in range(3)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()

    # Open tabs
    tab_ids = []
    for i in range(3):
        tab_id = await browser.async_open_tab(f"https://example{i}.com")
        tab_ids.append(tab_id)

    # Test state persistence across operations
    for tab_id in tab_ids:
        # Switch to tab
        await browser.async_switch_tab(tab_id)
        assert browser.current_tab_id == tab_id
        assert browser.page == browser.tabs[tab_id]

        # Perform some operations
        browser.page.url = f"https://example{tab_id}.com"

        # Switch away and back
        await browser.async_switch_tab(0)
        await browser.async_switch_tab(tab_id)

        # Verify state is maintained
        assert browser.current_tab_id == tab_id
        assert browser.page == browser.tabs[tab_id]
        assert browser.page.url == f"https://example{tab_id}.com"


@pytest.mark.asyncio
async def test_multi_tab_error_recovery(async_base_browser_fixture):
    """Test error recovery in multi-tab scenarios."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock pages
    mock_pages = [MagicMock() for _ in range(3)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()

    # Open tabs
    tab_ids = []
    for i in range(3):
        tab_id = await browser.async_open_tab(f"https://example{i}.com")
        tab_ids.append(tab_id)

    # Simulate a tab becoming closed unexpectedly
    browser.tabs[tab_ids[1]].is_closed = AsyncMock(return_value=True)

    # Try to switch to the closed tab
    with pytest.raises(ValueError, match="Tab 2 has been closed"):
        await browser.async_switch_tab(tab_ids[1])

    # Verify the closed tab was removed
    assert tab_ids[1] not in browser.tabs

    # Verify we can still switch to other tabs
    await browser.async_switch_tab(tab_ids[0])
    assert browser.current_tab_id == tab_ids[0]

    await browser.async_switch_tab(tab_ids[2])
    assert browser.current_tab_id == tab_ids[2]


@pytest.mark.asyncio
async def test_multi_tab_browser_toolkit_integration(
    async_browser_toolkit_fixture,
):
    """Test integration of multi-tab functionality with browser toolkit."""
    toolkit = async_browser_toolkit_fixture

    # Initialize browser
    await toolkit.browser.async_init()

    # Mock the browser's multi-tab methods (not the toolkit's)
    toolkit.browser.async_open_tab = AsyncMock(return_value=1)
    toolkit.browser.async_switch_tab = AsyncMock()
    toolkit.browser.async_close_tab = AsyncMock()

    # Call the toolkit methods (which should delegate to browser)
    tab_id = await toolkit.open_tab("https://example.com")
    assert tab_id == 1

    await toolkit.switch_tab(tab_id)
    toolkit.browser.async_switch_tab.assert_called_once_with(tab_id)

    await toolkit.close_tab(tab_id)
    toolkit.browser.async_close_tab.assert_called_once_with(tab_id)

    # Test that toolkit methods delegate to browser
    toolkit.browser.async_open_tab.assert_called_once_with(
        "https://example.com"
    )
    toolkit.browser.async_switch_tab.assert_called_once_with(tab_id)
    toolkit.browser.async_close_tab.assert_called_once_with(tab_id)


@pytest.mark.asyncio
async def test_multi_tab_with_cookies_and_storage(async_base_browser_fixture):
    """Test multi-tab functionality with cookies and storage persistence."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock pages with cookie/storage behavior
    mock_pages = [MagicMock() for _ in range(2)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    # Set both pages' context to the same mock context
    shared_context = MagicMock()
    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_page.context = shared_context

    # Open tabs to same domain (should share cookies)
    tab1_id = await browser.async_open_tab("https://example.com/login")
    tab2_id = await browser.async_open_tab("https://example.com/dashboard")

    # Switch between tabs and verify they maintain separate state
    await browser.async_switch_tab(tab1_id)
    assert browser.current_tab_id == tab1_id

    await browser.async_switch_tab(tab2_id)
    assert browser.current_tab_id == tab2_id

    # Verify both tabs are in the same context (shared cookies)
    assert browser.tabs[tab1_id].context is browser.tabs[tab2_id].context


@pytest.mark.asyncio
async def test_multi_tab_concurrent_switching(async_base_browser_fixture):
    """Test concurrent tab switching operations."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Mock pages
    mock_pages = [MagicMock() for _ in range(5)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = AsyncMock(return_value=False)

    # Open multiple tabs
    tab_ids = []
    for i in range(5):
        tab_id = await browser.async_open_tab(f"https://example{i}.com")
        tab_ids.append(tab_id)

    # Test concurrent switching
    async def switch_to_tab(tab_id):
        await browser.async_switch_tab(tab_id)
        return browser.current_tab_id

    # Create concurrent switching tasks
    switch_tasks = [switch_to_tab(tab_id) for tab_id in tab_ids]

    # Execute all switching operations concurrently
    results = await asyncio.gather(*switch_tasks)

    # Verify all switches completed successfully
    assert len(results) == len(tab_ids)
    assert all(result in tab_ids for result in results)

    # Verify final state is consistent
    assert browser.current_tab_id in tab_ids
    assert browser.page == browser.tabs[browser.current_tab_id]
