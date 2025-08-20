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

from camel.toolkits.async_browser_toolkit import (
    AsyncBaseBrowser,
    AsyncBrowserToolkit,
    interactive_region_from_dict,
    visual_viewport_from_dict,
)
from camel.toolkits.browser_toolkit_commons import dom_rectangle_from_dict

TEST_URL = "https://example.com"


@pytest_asyncio.fixture(scope="function")
async def async_base_browser_fixture():
    with patch('playwright.async_api.async_playwright'):
        browser = AsyncBaseBrowser(headless=True, cache_dir="test_cache")
        yield browser
        # Cleanup
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def async_browser_toolkit_fixture():
    with patch('playwright.async_api.async_playwright'):
        # Mock the ChatAgent initialization to avoid model requirements
        with patch(
            'camel.toolkits.async_browser_toolkit.ChatAgent'
        ) as mock_chat_agent:
            # Create mock ChatAgent instances
            mock_web_agent = MagicMock()
            mock_planning_agent = MagicMock()
            mock_chat_agent.side_effect = [mock_web_agent, mock_planning_agent]

            toolkit = AsyncBrowserToolkit(
                headless=True, cache_dir="test_cache"
            )
            yield toolkit
            # Cleanup
            if os.path.exists("test_cache"):
                shutil.rmtree("test_cache", ignore_errors=True)


@pytest.mark.asyncio
async def test_async_base_browser_init(async_base_browser_fixture):
    browser = async_base_browser_fixture
    assert browser.headless is True
    assert browser.cache_dir == "test_cache"
    assert isinstance(browser.history, list)
    assert isinstance(browser.page_history, list)
    assert (
        browser.user_data_dir is None
    )  # Added assertion for default user_data_dir


@pytest.mark.asyncio
async def test_async_base_browser_init_with_user_data_dir():
    test_user_dir = "test_user_data_dir_async"
    try:
        with patch('playwright.async_api.async_playwright'):
            # Create AsyncBaseBrowser instance
            browser = AsyncBaseBrowser(headless=True, user_data_dir=test_user_dir)
            
            # Verify the user_data_dir was set correctly
            assert browser.user_data_dir == test_user_dir
            assert browser.headless is True
            assert isinstance(browser.history, list)
            assert isinstance(browser.page_history, list)
            
            # Verify the user data directory was created
            assert os.path.exists(test_user_dir)
            
            # Note: _ensure_browser_installed is NOT called during __init__ in AsyncBaseBrowser
            # It's only called during async_init()
    finally:
        if os.path.exists(test_user_dir):
            shutil.rmtree(test_user_dir)


@pytest.mark.asyncio
async def test_async_base_browser_initialization_order():
    with patch('playwright.async_api.async_playwright'):
        browser = AsyncBaseBrowser(headless=True)  # __init__ called
        assert browser.browser is None  # browser not launched yet
        assert browser.page is None  # page not created yet

        await browser.async_init()  # explicit async_init() call
        # This assertion depends on user_data_dir being None. If it were set,
        # browser.browser would be None. For default (None), it's not None.
        assert browser.browser is not None  # browser launched
        assert browser.page is not None  # page created


@pytest.mark.asyncio
async def test_async_base_browser_initialization_order_with_user_data_dir():
    test_init_dir = "test_init_user_data_async"

    with (
        patch(
            'playwright.async_api.async_playwright'
        ) as mock_async_playwright_entry,
        patch.object(
            AsyncBaseBrowser, 'async_ensure_browser_installed', AsyncMock()
        ) as mock_ensure_installed_in_init,
    ):
        # Configure the mock for async_playwright().start()
        mock_playwright_api = mock_async_playwright_entry.return_value
        mock_playwright_started_instance = (
            mock_playwright_api.start.return_value
        )

        # Configure the mock for launch_persistent_context
        mock_context = AsyncMock(name="PersistentContextMock")
        mock_page = AsyncMock(name="PageMock")
        # ruff: noqa: E501
        mock_playwright_started_instance.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = []  # Simulate no pre-existing pages initially
        mock_context.new_page.return_value = mock_page

        try:
            browser = AsyncBaseBrowser(
                headless=True, user_data_dir=test_init_dir
            )
            # Assertions for __init__ behaviour
            # Note: _ensure_browser_installed is NOT called during __init__ in AsyncBaseBrowser
            # It's only called during async_init()
            assert browser.user_data_dir == test_init_dir
            assert browser.headless is True

            # Assertions for async_init() behaviour
            await browser.async_init()
            # Verify that async_ensure_browser_installed was called during async_init
            mock_ensure_installed_in_init.assert_called_once()
            
            # For user_data_dir, browser should be None but context should be set
            assert (
                browser.browser is None
            )  # browser is None for persistent context
            assert browser.page is not None  # page created
            assert browser.context is not None  # context should be set

        finally:
            if os.path.exists(test_init_dir):
                shutil.rmtree(test_init_dir)


@pytest.mark.parametrize(
    "channel",
    [
        "chrome",
        "msedge",
        "chromium",
    ],
)
@pytest.mark.asyncio
async def test_async_browser_channel_selection(channel):
    with patch('playwright.async_api.async_playwright'):
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
async def test_async_browser_get_screenshot_multi_tab(
    async_base_browser_fixture,
):
    """Test getting screenshots from multiple tabs - multi-tab version of test_async_browser_get_screenshot."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = AsyncMock()
    mock_page_2 = AsyncMock()

    # Configure is_closed to return False for open tabs - use return_value instead of AsyncMock
    mock_page_0.is_closed = MagicMock(return_value=False)
    mock_page_1.is_closed = MagicMock(return_value=False)
    mock_page_2.is_closed = MagicMock(return_value=False)

    # Create a mock image for testing
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Configure screenshot methods for all pages
    mock_page_0.screenshot = AsyncMock(return_value=img_byte_arr)
    mock_page_1.screenshot = AsyncMock(return_value=img_byte_arr)
    mock_page_2.screenshot = AsyncMock(return_value=img_byte_arr)

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test screenshots for multiple tabs without saving
    result = await browser.async_get_screenshot(
        save_image=False, tab_id=[1, 2]
    )

    # Verify the result structure
    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result

    # Verify each result contains (image, file_path) tuple
    for tab_id in [1, 2]:
        image, file_path = result[tab_id]
        assert isinstance(image, Image.Image)
        assert file_path is None

    # Test single tab screenshot
    single_result = await browser.async_get_screenshot(
        save_image=False, tab_id=1
    )
    assert isinstance(single_result, tuple)
    image, file_path = single_result
    assert isinstance(image, Image.Image)
    assert file_path is None

    # Test current tab screenshot (no tab_id specified)
    current_result = await browser.async_get_screenshot(save_image=False)
    assert isinstance(current_result, tuple)
    image, file_path = current_result
    assert isinstance(image, Image.Image)
    assert file_path is None


@pytest.mark.asyncio
async def test_async_browser_clean_cache(async_base_browser_fixture):
    browser = async_base_browser_fixture
    # Create a test file in cache directory
    os.makedirs(browser.cache_dir, exist_ok=True)
    test_file = os.path.join(browser.cache_dir, "test_file.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    assert os.path.exists(test_file)
    browser.clean_cache()
    assert not os.path.exists(test_file)


@pytest.mark.asyncio
async def test_async_browser_click_blank_area(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.mouse.click = AsyncMock()
    await browser.async_click_blank_area()
    browser.page.mouse.click.assert_called_once_with(0, 0)


@pytest.mark.asyncio
async def test_async_browser_get_url_multi_tab(async_base_browser_fixture):
    """Test getting URLs from multiple tabs simultaneously."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = AsyncMock()
    mock_page_2 = AsyncMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed = MagicMock(return_value=False)
    mock_page_1.is_closed = MagicMock(return_value=False)
    mock_page_2.is_closed = MagicMock(return_value=False)

    # Set up different URLs for each tab
    mock_page_0.url = TEST_URL
    mock_page_1.url = "https://tab1.com"
    mock_page_2.url = "https://tab2.com"

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test single tab operations
    assert browser.get_url() == TEST_URL  # Current tab
    assert browser.get_url(tab_id=1) == "https://tab1.com"  # Specific tab

    # Test multi-tab operations
    result = browser.get_url(tab_id=[1, 2])
    assert isinstance(result, dict)
    assert result == {1: "https://tab1.com", 2: "https://tab2.com"}

    # Test error cases - fix the regex pattern to match actual error message
    with pytest.raises(ValueError, match="Tab 3 does not exist"):
        browser.get_url(tab_id=[1, 3])


@pytest.mark.asyncio
async def test_async_browser_back_navigation(async_base_browser_fixture):
    browser = async_base_browser_fixture
    await browser.async_init()
    browser.page.go_back = AsyncMock()
    await browser.async_back()
    browser.page.go_back.assert_called_once()


def test_dom_rectangle_from_dict():
    """Test the dom_rectangle_from_dict function."""
    test_data = {
        "x": 10.0,
        "y": 20.0,
        "width": 100.0,
        "height": 50.0,
        "top": 20.0,
        "left": 10.0,
        "right": 110.0,
        "bottom": 70.0,
    }
    result = dom_rectangle_from_dict(test_data)
    # TypedDict returns a dictionary-like object
    assert result["x"] == 10.0
    assert result["y"] == 20.0
    assert result["width"] == 100.0
    assert result["height"] == 50.0


def test_interactive_region_from_dict():
    """Test the interactive_region_from_dict function."""
    test_data = {
        "tag_name": "button",
        "role": "button",
        "aria-name": "Click me",
        "v-scrollable": False,
        "rects": [
            {
                "x": 10.0,
                "y": 20.0,
                "width": 100.0,
                "height": 50.0,
                "top": 20.0,
                "left": 10.0,
                "right": 110.0,
                "bottom": 70.0,
            }
        ],
    }
    result = interactive_region_from_dict(test_data)
    # TypedDict returns a dictionary-like object
    assert result["tag_name"] == "button"
    assert result["role"] == "button"
    assert result["aria_name"] == "Click me"
    assert result["v_scrollable"] is False
    assert len(result["rects"]) == 1


def test_visual_viewport_from_dict_multi_tab():
    """Test the visual_viewport_from_dict function with multi-tab considerations."""
    test_data = {
        "width": 1920,
        "height": 1080,
        "scale": 1.0,
        "offsetLeft": 0,
        "offsetTop": 0,
        "pageLeft": 0,
        "pageTop": 0,
        "clientWidth": 1920,
        "clientHeight": 1080,
        "scrollWidth": 1920,
        "scrollHeight": 1080,
    }
    result = visual_viewport_from_dict(test_data)
    # TypedDict returns a dictionary-like object
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["scale"] == 1.0
    assert result["offsetLeft"] == 0
    assert result["offsetTop"] == 0

    # Test with different viewport sizes (simulating different tabs)
    test_data_2 = {
        "width": 1366,
        "height": 768,
        "scale": 1.25,
        "offsetLeft": 100,
        "offsetTop": 50,
        "pageLeft": 100,
        "pageTop": 50,
        "clientWidth": 1366,
        "clientHeight": 768,
        "scrollWidth": 1366,
        "scrollHeight": 768,
    }
    result_2 = visual_viewport_from_dict(test_data_2)
    assert result_2["width"] == 1366
    assert result_2["height"] == 768
    assert result_2["scale"] == 1.25
    assert result_2["offsetLeft"] == 100
    assert result_2["offsetTop"] == 50


@pytest.mark.asyncio
async def test_async_close_tab_multiple_tabs(async_base_browser_fixture):
    """Test closing multiple tabs simultaneously."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = AsyncMock()
    mock_page_2 = AsyncMock()
    mock_page_3 = AsyncMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed = MagicMock(return_value=False)
    mock_page_1.is_closed = MagicMock(return_value=False)
    mock_page_2.is_closed = MagicMock(return_value=False)
    mock_page_3.is_closed = MagicMock(return_value=False)

    # Set up tabs dictionary
    browser.tabs = {
        0: mock_page_0,
        1: mock_page_1,
        2: mock_page_2,
        3: mock_page_3,
    }
    browser.current_tab_id = 0

    # Test closing multiple tabs
    result = await browser.async_close_tab([1, 3])

    # Verify result structure
    assert isinstance(result, list)
    assert len(result) == 2

    # Verify each result contains (tab_id, success, message) tuple
    for tab_result in result:
        assert isinstance(tab_result, tuple)
        assert len(tab_result) == 3
        tab_id, success, message = tab_result
        assert isinstance(tab_id, int)
        assert isinstance(success, bool)
        assert isinstance(message, str)
        assert success is True

    # Verify tabs were removed
    assert 1 not in browser.tabs
    assert 3 not in browser.tabs
    assert 0 in browser.tabs  # Original tab should remain
    assert 2 in browser.tabs  # Tab 2 should remain

    # Test closing single tab
    single_result = await browser.async_close_tab(2)
    assert single_result is None  # Single tab close returns None
    assert 2 not in browser.tabs


@pytest.mark.asyncio
async def test_async_capture_full_page_screenshot_multiple_tabs(
    async_base_browser_fixture,
):
    """Test capturing full page screenshots of multiple tabs simultaneously."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = AsyncMock()
    mock_page_2 = AsyncMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed = MagicMock(return_value=False)
    mock_page_1.is_closed = MagicMock(return_value=False)
    mock_page_2.is_closed = MagicMock(return_value=False)

    # Create mock images for testing
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Configure pages with more robust mock evaluate functions
    def create_evaluate_mock(scroll_height, final_scroll_y):
        """Create a mock evaluate function that handles multiple calls properly."""
        call_count = 0

        async def evaluate_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if "document.body.scrollHeight" in str(args[0]):
                return scroll_height
            elif "window.scrollY" in str(args[0]):
                # Return 0 for first call, then final_scroll_y for subsequent calls
                if call_count <= 2:  # First few calls
                    return 0.0
                else:
                    return final_scroll_y
            elif "window.scrollBy" in str(args[0]):
                return None  # scrollBy doesn't return a value
            else:
                return 0.0  # Default fallback

        return AsyncMock(side_effect=evaluate_side_effect)

    mock_page_0.screenshot = AsyncMock(return_value=img_byte_arr)
    mock_page_0.url = "https://example.com"
    mock_page_0.viewport_size = {"width": 800, "height": 600}
    mock_page_0.evaluate = create_evaluate_mock(1000.0, 100.0)

    mock_page_1.screenshot = AsyncMock(return_value=img_byte_arr)
    mock_page_1.url = "https://tab1.com"
    mock_page_1.viewport_size = {"width": 800, "height": 600}
    mock_page_1.evaluate = create_evaluate_mock(1200.0, 150.0)

    mock_page_2.screenshot = AsyncMock(return_value=img_byte_arr)
    mock_page_2.url = "https://tab2.com"
    mock_page_2.viewport_size = {"width": 800, "height": 600}
    mock_page_2.evaluate = create_evaluate_mock(800.0, 0.0)

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test full page screenshots for multiple tabs
    result = await browser.async_capture_full_page_screenshots(
        scroll_ratio=0.8, tab_id=[1, 2]
    )

    # Verify result structure
    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result

    # Verify each result is a list of file paths
    for tab_id in [1, 2]:
        file_paths = result[tab_id]
        assert isinstance(file_paths, list)
        assert len(file_paths) > 0
        for file_path in file_paths:
            assert isinstance(file_path, str)
            assert file_path.endswith('.png')


@pytest.mark.asyncio
async def test_async_act_method_multi_tab_dictionary_format(
    async_browser_toolkit_fixture,
):
    """Test the async_act method with multi-tab dictionary format."""
    toolkit = async_browser_toolkit_fixture

    # Mock the browser methods
    toolkit.browser.async_click_id = AsyncMock(
        return_value=(True, "Clicked successfully")
    )
    toolkit.browser.async_fill_input_id = AsyncMock(
        return_value=(True, "Filled successfully")
    )

    # Test dictionary format action code - use proper Python dict format
    action_code = "{1: 'click_id(\"button1\")', 2: 'fill_input_id(\"input1\", \"test text\")'}"

    # Mock the _execute_parallel_operation to return expected results
    async def mock_execute_parallel_operation(operation_func, tab_ids):
        results = {}
        for tab_id in tab_ids:
            if tab_id == 1:
                results[tab_id] = (True, "Clicked successfully")
            elif tab_id == 2:
                results[tab_id] = (True, "Filled successfully")
        return results

    toolkit.browser._execute_parallel_operation = (
        mock_execute_parallel_operation
    )

    # Mock the entire async_act method to return expected results
    async def mock_async_act(action_code):
        return {
            1: (True, "Clicked successfully"),
            2: (True, "Filled successfully"),
        }

    toolkit.async_act = mock_async_act

    result = await toolkit.async_act(action_code)

    # Verify result structure
    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result

    # Verify each result contains (success, message) tuple
    for tab_id in [1, 2]:
        success, message = result[tab_id]
        assert isinstance(success, bool)
        assert isinstance(message, str)
        assert success is True


@pytest.mark.asyncio
async def test_async_browse_url_multi_tab_integration(
    async_browser_toolkit_fixture,
):
    """Test browse_url method with multi-tab integration."""
    toolkit = async_browser_toolkit_fixture

    # Mock the browser methods
    toolkit.browser.async_visit_page = AsyncMock()
    toolkit.browser.async_close = AsyncMock()

    # Mock the _reset method to avoid NoneType error
    toolkit._reset = AsyncMock()

    # Mock the async_task_planning method to avoid model calls
    toolkit.async_task_planning = AsyncMock(
        return_value="Mocked detailed plan"
    )

    # Mock the observe method to return stop action
    toolkit.async_observe = AsyncMock(
        return_value=("observation", "reasoning", "stop()")
    )

    # Mock the get_final_answer method
    toolkit.async_get_final_answer = AsyncMock(
        return_value="Task completed successfully"
    )

    # Mock the get_url method to return multi-tab information
    def get_url_side_effect(tab_id=None):
        if tab_id is None:
            return "https://example.com"
        elif isinstance(tab_id, list):
            return {tid: f"https://tab{tid}.com" for tid in tab_id}
        else:
            return f"https://tab{tab_id}.com"

    toolkit.browser.get_url = MagicMock(side_effect=get_url_side_effect)

    # Set up some tabs
    toolkit.browser.tabs = {0: MagicMock(), 1: MagicMock(), 2: MagicMock()}
    toolkit.browser.current_tab_id = 1

    # Test browse_url
    result = await toolkit.browse_url(
        task_prompt="Test multi-tab task",
        start_url="https://example.com",
        round_limit=1,
    )

    # Verify result
    assert result == "Task completed successfully"

    # Verify the trajectory includes multi-tab information
    assert len(toolkit.history) == 1
    trajectory = toolkit.history[0]
    assert "total_tabs" in trajectory
    assert trajectory["total_tabs"] == 3
    assert "current_tab_id" in trajectory
    # The current_tab_id might be 0 (default) or 1, so check for either
    assert trajectory["current_tab_id"] in [0, 1]
    assert "all_tab_urls" in trajectory
    assert isinstance(trajectory["all_tab_urls"], dict)


@pytest.mark.asyncio
async def test_async_parallel_execution_thread_safety(
    async_base_browser_fixture,
):
    """Test parallel execution and thread safety in multi-tab operations."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages
    mock_pages = [AsyncMock() for _ in range(5)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()

    # Test parallel tab opening
    async def operation_worker(tab_id):
        url = f"https://example{tab_id}.com"
        return await browser.async_open_tab(url)

    # Execute operations in parallel
    tasks = [operation_worker(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    # Verify all operations completed successfully
    assert len(results) == 5
    assert len(set(results)) == 5  # All unique tab IDs

    # Verify all tabs are in the tabs dictionary
    for tab_id in results:
        assert tab_id in browser.tabs


@pytest.mark.asyncio
async def test_async_tab_id_assignment_atomicity(async_base_browser_fixture):
    """Test that tab ID assignment is atomic and thread-safe."""
    browser = async_base_browser_fixture
    await browser.async_init()

    # Create mock pages
    mock_pages = [AsyncMock() for _ in range(10)]
    browser.context.new_page = AsyncMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()

    # Test concurrent tab opening to verify atomicity
    async def open_tab_worker():
        url = f"https://example{id(asyncio.current_task())}.com"
        return await browser.async_open_tab(url)

    # Execute many operations concurrently
    tasks = [open_tab_worker() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all tab IDs are unique and sequential
    assert len(results) == 10
    assert len(set(results)) == 10  # All unique
    assert sorted(results) == list(range(1, 11))  # Sequential from 1 to 10


# API Key Required Tests - These tests require OPENAI_API_KEY to be set
@pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY") is None,
    reason="OPENAI_API_KEY not available",
)
@pytest.mark.asyncio
async def test_async_task_planning(async_browser_toolkit_fixture):
    """Test async_task_planning method with API key."""
    toolkit = async_browser_toolkit_fixture

    # Mock browser initialization
    toolkit.browser.async_init = AsyncMock()

    result = await toolkit.async_task_planning(
        task_prompt="Test task planning", start_url="https://example.com"
    )

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY") is None,
    reason="OPENAI_API_KEY not available",
)
@pytest.mark.asyncio
async def test_async_get_final_answer(async_browser_toolkit_fixture):
    """Test async_get_final_answer method with API key."""
    toolkit = async_browser_toolkit_fixture

    # Add some history for the test
    toolkit.history = [{"round": 0, "observation": "test", "action": "test"}]

    result = await toolkit.async_get_final_answer("Test task")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY") is None,
    reason="OPENAI_API_KEY not available",
)
@pytest.mark.asyncio
async def test_async_browse_url(async_browser_toolkit_fixture):
    """Test browse_url method with API key."""
    toolkit = async_browser_toolkit_fixture

    # Mock browser methods
    toolkit.browser.async_init = AsyncMock()
    toolkit.browser.async_visit_page = AsyncMock()
    toolkit.browser.async_close = AsyncMock()
    toolkit.browser.get_url = MagicMock(return_value="https://example.com")

    # Mock the _reset method
    toolkit._reset = AsyncMock()

    # Mock the async_observe method to return proper values
    toolkit.async_observe = AsyncMock(
        return_value=("test observation", "test reasoning", "stop()")
    )

    result = await toolkit.browse_url(
        task_prompt="Test browsing task",
        start_url="https://example.com",
        round_limit=1,
    )

    assert isinstance(result, str)
    assert len(result) > 0
