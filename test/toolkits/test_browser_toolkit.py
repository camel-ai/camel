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
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from camel.toolkits.browser_toolkit import (
    BaseBrowser,
    BrowserToolkit,
    interactive_region_from_dict,
    visual_viewport_from_dict,
)
from camel.toolkits.browser_toolkit_commons import dom_rectangle_from_dict

TEST_URL = "https://example.com"


@pytest.fixture(scope="function")
def base_browser_fixture():
    with patch('playwright.sync_api.sync_playwright'):
        browser = BaseBrowser(headless=True, cache_dir="test_cache")
        yield browser
        # Cleanup
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.fixture(scope="function")
def browser_toolkit_fixture():
    with patch('playwright.sync_api.sync_playwright'):
        toolkit = BrowserToolkit(headless=True, cache_dir="test_cache")
        yield toolkit
        # Cleanup
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


def test_base_browser_init(base_browser_fixture):
    browser = base_browser_fixture
    assert browser.headless is True
    assert browser.cache_dir == "test_cache"
    assert isinstance(browser.history, list)
    assert isinstance(browser.page_history, list)
    assert (
        browser.user_data_dir is None
    )  # Added assertion for default user_data_dir


def test_base_browser_init_with_user_data_dir():
    test_user_dir = "test_user_data_dir_sync"
    try:
        with patch('playwright.sync_api.sync_playwright'):
            # Mock _ensure_browser_installed to prevent
            # actual browser checks during this specific init test
            with patch.object(
                BaseBrowser, '_ensure_browser_installed', MagicMock()
            ) as mock_ensure_installed:
                browser = BaseBrowser(
                    headless=True, user_data_dir=test_user_dir
                )
                mock_ensure_installed.assert_called_once()
                assert browser.user_data_dir == test_user_dir
                assert os.path.exists(
                    test_user_dir
                )  # Check if __init__ created it
    finally:
        if os.path.exists(test_user_dir):
            shutil.rmtree(test_user_dir)


def test_base_browser_initialization_order():
    with patch('playwright.sync_api.sync_playwright'):
        browser = BaseBrowser(headless=True)  # __init__ called
        assert browser.browser is None  # browser not launched yet
        assert browser.page is None  # page not created yet

        browser.init()  # explicit init() call
        # This assertion depends on user_data_dir being None. If it were set,
        # browser.browser would be None. For default (None), it's not None.
        assert browser.browser is not None  # browser launched
        assert browser.page is not None  # page created


def test_base_browser_initialization_order_with_user_data_dir():
    test_init_dir = "test_init_user_data_sync"

    with (
        patch(
            'playwright.sync_api.sync_playwright'
        ) as mock_sync_playwright_entry,
        patch.object(
            BaseBrowser, '_ensure_browser_installed', MagicMock()
        ) as mock_ensure_installed_in_init,
    ):
        # Configure the mock for sync_playwright().start()
        mock_playwright_api = mock_sync_playwright_entry.return_value
        mock_playwright_started_instance = (
            mock_playwright_api.start.return_value
        )

        # Configure the mock for launch_persistent_context
        mock_context = MagicMock(name="PersistentContextMock")
        mock_page = MagicMock(name="PageMock")
        # ruff: noqa: E501
        mock_playwright_started_instance.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = []  # Simulate no pre-existing pages initially
        mock_context.new_page.return_value = mock_page

        try:
            browser = BaseBrowser(headless=True, user_data_dir=test_init_dir)
            # Assertions for __init__ behaviour
            mock_ensure_installed_in_init.assert_called_once()
            assert os.path.exists(
                test_init_dir
            )  # __init__ should have created it
            assert browser.browser is None  # Before init
            assert browser.page is None  # Before init
            assert browser.context is None  # Before init

            browser.init()
            # Action: This calls
            # self.playwright.chromium.launch_persistent_context

            # Assertions for init() behaviour with user_data_dir
            # ruff: noqa: E501
            mock_playwright_started_instance.chromium.launch_persistent_context.assert_called_once()
            # ruff: noqa: E501
            call_kwargs = mock_playwright_started_instance.chromium.launch_persistent_context.call_args.kwargs
            assert call_kwargs['user_data_dir'] == test_init_dir
            assert call_kwargs['headless'] is True
            assert call_kwargs['channel'] == "chromium"  # Default channel
            assert call_kwargs['accept_downloads'] is True
            assert isinstance(call_kwargs['user_agent'], str)
            assert call_kwargs['java_script_enabled'] is True
            assert isinstance(call_kwargs['args'], list)

            assert browser.browser is None  # Key assertion: No separate
            # browser object with persistent context
            assert browser.context == mock_context
            assert browser.page == mock_page
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
def test_browser_channel_selection(channel):
    with patch('playwright.sync_api.sync_playwright'):
        browser = BaseBrowser(headless=True, channel=channel)
        assert browser.channel == channel


def test_browser_visit_page(base_browser_fixture):
    browser = base_browser_fixture
    browser.init()

    # Mock the page methods
    browser.page.goto = MagicMock()
    browser.page.wait_for_load_state = MagicMock()

    browser.visit_page(TEST_URL)

    browser.page.goto.assert_called_once_with(TEST_URL)
    browser.page.wait_for_load_state.assert_called_once()


def test_browser_get_screenshot_multi_tab(base_browser_fixture):
    """Test getting screenshots from multiple tabs - multi-tab version of test_browser_get_screenshot."""
    browser = base_browser_fixture
    browser.init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed.return_value = False
    mock_page_1.is_closed.return_value = False
    mock_page_2.is_closed.return_value = False

    # Create a mock image for testing
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Configure screenshot methods for all pages
    mock_page_0.screenshot = MagicMock(return_value=img_byte_arr)
    mock_page_1.screenshot = MagicMock(return_value=img_byte_arr)
    mock_page_2.screenshot = MagicMock(return_value=img_byte_arr)

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test screenshots for multiple tabs without saving
    result = browser.get_screenshot(save_image=False, tab_id=[1, 2])

    # Verify result structure
    assert isinstance(result, dict)
    assert len(result) == 2
    assert 1 in result
    assert 2 in result

    # Verify each tab's screenshot result
    for _tab_id, (image, file_path) in result.items():
        assert isinstance(image, Image.Image)
        assert file_path is None

    # Verify screenshots were called for the specified tabs
    mock_page_1.screenshot.assert_called_once()
    mock_page_2.screenshot.assert_called_once()
    # Original page (tab 0) should not be called since we specified tabs 1 and 2
    mock_page_0.screenshot.assert_not_called()


def test_browser_clean_cache(base_browser_fixture):
    browser = base_browser_fixture

    # Create a test file in cache directory
    os.makedirs(browser.cache_dir, exist_ok=True)
    test_file = os.path.join(browser.cache_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    browser.clean_cache()
    assert not os.path.exists(browser.cache_dir)


def test_browser_click_blank_area(base_browser_fixture):
    browser = base_browser_fixture
    browser.init()

    browser.page.mouse.click = MagicMock()
    browser.page.wait_for_load_state = MagicMock()

    browser.click_blank_area()

    browser.page.mouse.click.assert_called_once_with(0, 0)
    browser.page.wait_for_load_state.assert_called_once()


def test_browser_get_url_multi_tab(base_browser_fixture):
    """Test getting URLs from multiple tabs simultaneously."""
    browser = base_browser_fixture
    browser.init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed.return_value = False
    mock_page_1.is_closed.return_value = False
    mock_page_2.is_closed.return_value = False

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

    # Test error cases
    with pytest.raises(ValueError, match="Tabs \\[3\\] do not exist"):
        browser.get_url(tab_id=[1, 3])

    # Test edge cases
    assert browser.get_url(tab_id=[]) == {}  # Empty list

    with pytest.raises(
        TypeError,
        match="tab_id must be None, an integer, or a list of integers",
    ):
        browser.get_url(tab_id="invalid")


def test_browser_back_navigation(base_browser_fixture):
    browser = base_browser_fixture
    browser.init()

    browser.page.go_back = MagicMock()
    browser.page.wait_for_load_state = MagicMock()

    browser.back()

    browser.page.go_back.assert_called_once()
    browser.page.wait_for_load_state.assert_called_once()


def test_dom_rectangle_from_dict():
    rect_dict = {
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 200,
        "top": 20,
        "right": 110,
        "bottom": 220,
        "left": 10,
    }
    rect = dom_rectangle_from_dict(rect_dict)
    assert rect["width"] == 100
    assert rect["left"] == 10


def test_interactive_region_from_dict():
    region_dict = {
        "tag_name": "button",
        "role": "button",
        "aria-name": "Submit",
        "v-scrollable": False,
        "rects": [
            {
                "x": 5,
                "y": 5,
                "width": 50,
                "height": 20,
                "top": 5,
                "right": 55,
                "bottom": 25,
                "left": 5,
            }
        ],
    }
    region = interactive_region_from_dict(region_dict)
    assert region["tag_name"] == "button"
    assert len(region["rects"]) == 1


def test_visual_viewport_from_dict_multi_tab():
    """Test visual viewport creation from dictionaries for multiple tabs simultaneously."""
    # Create different viewport dictionaries for different tabs
    viewport_dict_1 = {
        "height": 800,
        "width": 600,
        "offsetLeft": 0,
        "offsetTop": 0,
        "pageLeft": 0,
        "pageTop": 0,
        "scale": 1,
        "clientWidth": 600,
        "clientHeight": 800,
        "scrollWidth": 600,
        "scrollHeight": 1200,
    }

    viewport_dict_2 = {
        "height": 1024,
        "width": 768,
        "offsetLeft": 10,
        "offsetTop": 20,
        "pageLeft": 5,
        "pageTop": 15,
        "scale": 1.2,
        "clientWidth": 768,
        "clientHeight": 1024,
        "scrollWidth": 800,
        "scrollHeight": 1500,
    }

    viewport_dict_3 = {
        "height": 900,
        "width": 1200,
        "offsetLeft": 0,
        "offsetTop": 0,
        "pageLeft": 0,
        "pageTop": 0,
        "scale": 0.8,
        "clientWidth": 1200,
        "clientHeight": 900,
        "scrollWidth": 1200,
        "scrollHeight": 2000,
    }

    # Test single viewport creation (original functionality)
    viewport_1 = visual_viewport_from_dict(viewport_dict_1)
    assert viewport_1["height"] == 800
    assert viewport_1["scrollHeight"] == 1200
    assert viewport_1["scale"] == 1

    # Test multiple viewport creation for different tabs
    viewport_2 = visual_viewport_from_dict(viewport_dict_2)
    viewport_3 = visual_viewport_from_dict(viewport_dict_3)

    # Verify each viewport has correct properties
    assert viewport_2["height"] == 1024
    assert viewport_2["width"] == 768
    assert viewport_2["scale"] == 1.2
    assert viewport_2["offsetLeft"] == 10
    assert viewport_2["offsetTop"] == 20

    assert viewport_3["height"] == 900
    assert viewport_3["width"] == 1200
    assert viewport_3["scale"] == 0.8
    assert viewport_3["scrollHeight"] == 2000

    # Test creating a dictionary of viewports for multiple tabs
    tab_viewports = {1: viewport_1, 2: viewport_2, 3: viewport_3}

    # Verify the multi-tab viewport dictionary structure
    assert isinstance(tab_viewports, dict)
    assert len(tab_viewports) == 3
    assert 1 in tab_viewports
    assert 2 in tab_viewports
    assert 3 in tab_viewports

    # Verify each tab's viewport maintains its unique properties
    assert tab_viewports[1]["height"] == 800
    assert tab_viewports[2]["height"] == 1024
    assert tab_viewports[3]["height"] == 900

    assert tab_viewports[1]["scale"] == 1
    assert tab_viewports[2]["scale"] == 1.2
    assert tab_viewports[3]["scale"] == 0.8

    # Test edge cases for multi-tab viewport handling
    empty_viewport_dict = {
        "height": 0,
        "width": 0,
        "offsetLeft": 0,
        "offsetTop": 0,
        "pageLeft": 0,
        "pageTop": 0,
        "scale": 0,
        "clientWidth": 0,
        "clientHeight": 0,
        "scrollWidth": 0,
        "scrollHeight": 0,
    }

    empty_viewport = visual_viewport_from_dict(empty_viewport_dict)
    assert empty_viewport["height"] == 0
    assert empty_viewport["scale"] == 0

    # Test that empty viewport can be included in multi-tab context
    tab_viewports[4] = empty_viewport
    assert len(tab_viewports) == 4
    assert tab_viewports[4]["height"] == 0


def test_close_tab_multiple_tabs(base_browser_fixture):
    """Test closing multiple tabs simultaneously."""
    browser = base_browser_fixture
    browser.init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    mock_page_3 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed.return_value = False
    mock_page_1.is_closed.return_value = False
    mock_page_2.is_closed.return_value = False
    mock_page_3.is_closed.return_value = False

    # Set up tabs dictionary
    browser.tabs = {
        0: mock_page_0,
        1: mock_page_1,
        2: mock_page_2,
        3: mock_page_3,
    }
    browser.current_tab_id = 0

    # Test closing multiple tabs
    result = browser.close_tab([1, 3])

    # Verify tabs are removed
    assert 1 not in browser.tabs
    assert 3 not in browser.tabs
    assert 0 in browser.tabs
    assert 2 in browser.tabs

    # Verify current tab unchanged
    assert browser.current_tab_id == 0
    assert browser.page == mock_page_0

    # Verify result format for multiple tabs
    assert isinstance(result, list)
    assert len(result) == 2
    for tab_result in result:
        assert isinstance(tab_result, tuple)
        assert len(tab_result) == 3  # (tab_id, success, message)
        assert isinstance(tab_result[0], int)
        assert isinstance(tab_result[1], bool)
        assert isinstance(tab_result[2], str)

    # Verify tabs were closed
    mock_page_1.close.assert_called_once()
    mock_page_3.close.assert_called_once()


def test_capture_full_page_screenshot_multiple_tabs(base_browser_fixture):
    """Test capturing full page screenshots of multiple tabs simultaneously."""
    browser = base_browser_fixture
    browser.init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed.return_value = False
    mock_page_1.is_closed.return_value = False
    mock_page_2.is_closed.return_value = False

    # Create mock images for testing
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Configure pages with more robust mock evaluate functions
    def create_evaluate_mock(scroll_height, final_scroll_y):
        """Create a mock evaluate function that handles multiple calls properly."""
        call_count = 0

        def evaluate_side_effect(*args, **kwargs):
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

        return MagicMock(side_effect=evaluate_side_effect)

    mock_page_0.screenshot = MagicMock(return_value=img_byte_arr)
    mock_page_0.url = "https://example.com"
    mock_page_0.viewport_size = {"width": 800, "height": 600}
    mock_page_0.evaluate = create_evaluate_mock(1000.0, 100.0)

    mock_page_1.screenshot = MagicMock(return_value=img_byte_arr)
    mock_page_1.url = "https://tab1.com"
    mock_page_1.viewport_size = {"width": 800, "height": 600}
    mock_page_1.evaluate = create_evaluate_mock(1200.0, 150.0)

    mock_page_2.screenshot = MagicMock(return_value=img_byte_arr)
    mock_page_2.url = "https://tab2.com"
    mock_page_2.viewport_size = {"width": 800, "height": 600}
    mock_page_2.evaluate = create_evaluate_mock(800.0, 0.0)

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test full page screenshots for multiple tabs
    result = browser.capture_full_page_screenshots(
        scroll_ratio=0.8, tab_id=[1, 2]
    )

    assert isinstance(result, dict)
    assert len(result) == 2
    assert 1 in result
    assert 2 in result

    for _tab_id, screenshots in result.items():
        assert isinstance(screenshots, list)
        assert len(screenshots) > 0

        for screenshot_path in screenshots:
            assert isinstance(screenshot_path, str)
            assert os.path.exists(screenshot_path)
            assert screenshot_path.endswith('.png')


def test_act_method_multi_tab_dictionary_format(browser_toolkit_fixture):
    """Test that the act method properly handles dictionary format for multi-tab actions."""
    toolkit = browser_toolkit_fixture

    with patch('playwright.sync_api.sync_playwright'):
        # Mock browser components
        toolkit.browser.init = MagicMock()
        toolkit.browser.visit_page = MagicMock()
        toolkit.browser.close = MagicMock()

        # Mock browser functions
        toolkit.browser.click_id = MagicMock(return_value=None)
        toolkit.browser.fill_input_id = MagicMock(return_value="Input filled")
        toolkit.browser.scroll_down = MagicMock(return_value=None)

        # Test dictionary format actions
        dict_actions = [
            # Simple dictionary with string values
            (
                "{1: 'login', 2: 'search'}",
                "Simple dictionary with string values",
            ),
            # Dictionary with action codes
            (
                "{1: 'click_id(login)', 2: 'fill_input_id(search, query)'}",
                "Dictionary with action codes",
            ),
            # Dictionary with mixed types
            (
                "{1: 'click_id(button)', 2: 'scroll_down()', 3: 'fill_input_id(input, text)'}",
                "Dictionary with mixed action types",
            ),
        ]

        for action_code, _description in dict_actions:
            with (
                patch.object(toolkit.browser, 'click_id', return_value=None),
                patch.object(
                    toolkit.browser, 'fill_input_id', return_value="filled"
                ),
                patch.object(
                    toolkit.browser, 'scroll_down', return_value=None
                ),
            ):
                # Execute the action
                success, result = toolkit._act(action_code)

                # Verify the action was processed
                assert isinstance(success, bool)
                assert isinstance(result, str)


def test_browse_url_multi_tab_integration(browser_toolkit_fixture):
    """Test browse_url with multi-tab functionality."""
    toolkit = browser_toolkit_fixture

    with patch('playwright.sync_api.sync_playwright'):
        # Mock browser components
        toolkit.browser.init = MagicMock()
        toolkit.browser.visit_page = MagicMock()
        toolkit.browser.close = MagicMock()

        # Mock _reset to prevent clearing tabs
        toolkit._reset = MagicMock()

        # Fix the get_url mock to handle both single and multiple tab IDs
        def get_url_side_effect(tab_id=None):
            if tab_id is None:
                return TEST_URL
            elif isinstance(tab_id, int):
                return {
                    0: TEST_URL,
                    1: "https://tab1.com",
                    2: "https://tab2.com",
                }.get(tab_id, TEST_URL)
            elif isinstance(tab_id, list):
                return {
                    0: TEST_URL,
                    1: "https://tab1.com",
                    2: "https://tab2.com",
                }
            else:
                return TEST_URL

        toolkit.browser.get_url = MagicMock(side_effect=get_url_side_effect)

        # Set up multi-tab state
        toolkit.browser.tabs = {0: MagicMock(), 1: MagicMock(), 2: MagicMock()}
        toolkit.browser.current_tab_id = 0

        # Mock the planning method
        toolkit._task_planning = MagicMock(
            return_value="1. Open multiple tabs\n2. Navigate to different sites\n3. Complete task"
        )

        # Mock _observe to return multi-tab actions
        observe_calls = [
            (
                "Page loaded",
                "Need to open new tab",
                "open_tab('https://tab1.com')",
            ),
            ("Tab opened", "Switch to new tab", "switch_tab(1)"),
            (
                "Tab switched",
                "Open another tab",
                "open_tab('https://tab2.com')",
            ),
            ("All tabs ready", "Complete task", "stop()"),
        ]
        toolkit._observe = MagicMock(side_effect=observe_calls)

        # Mock _act to handle multi-tab actions
        def act_side_effect(action_code):
            if "open_tab" in action_code:
                return True, "Tab opened successfully"
            elif "switch_tab" in action_code:
                return True, "Tab switched successfully"
            else:
                return True, "Action completed"

        toolkit._act = MagicMock(side_effect=act_side_effect)
        toolkit._get_final_answer = MagicMock(
            return_value="Multi-tab task completed"
        )

        # Execute browse_url
        result = toolkit.browse_url(
            task_prompt="Test multi-tab browsing task",
            start_url=TEST_URL,
            round_limit=5,
        )

        # Verify multi-tab functionality
        assert result == "Multi-tab task completed"
        assert len(toolkit.history) == 4

        # Verify multi-tab information in trajectories
        for trajectory in toolkit.history:
            assert "current_tab_id" in trajectory
            assert "all_tab_urls" in trajectory
            assert "total_tabs" in trajectory
            assert isinstance(trajectory["current_tab_id"], int)
            assert isinstance(trajectory["all_tab_urls"], dict)
            assert isinstance(trajectory["total_tabs"], int)


def test_parallel_execution_thread_safety(base_browser_fixture):
    """Test thread safety of parallel operations."""
    browser = base_browser_fixture
    browser.init()

    # Create mock pages for multiple tabs
    mock_page_0 = browser.page  # Original page
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()

    # Configure is_closed to return False for open tabs
    mock_page_0.is_closed.return_value = False
    mock_page_1.is_closed.return_value = False
    mock_page_2.is_closed.return_value = False

    # Configure URL attributes for mock pages
    mock_page_0.url = "https://example.com"
    mock_page_1.url = "https://tab1.com"
    mock_page_2.url = "https://tab2.com"

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test concurrent tab operations
    import threading
    import time

    results = []
    errors = []

    def operation_worker(tab_id):
        try:
            # Simulate concurrent operations
            time.sleep(0.01)  # Small delay to simulate work
            result = browser.get_url(tab_id=tab_id)
            results.append((tab_id, result))
        except Exception as e:
            errors.append((tab_id, str(e)))

    # Create multiple threads
    threads = []
    for _i in range(5):
        thread = threading.Thread(target=operation_worker, args=(1,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0
    assert len(results) == 5

    # Verify all results are consistent
    for _tab_id, result in results:
        assert isinstance(result, str)


def test_tab_id_assignment_atomicity(base_browser_fixture):
    """Test atomic tab ID assignment using threading lock."""
    browser = base_browser_fixture
    browser.init()

    # Mock context
    mock_context = MagicMock()
    browser.context = mock_context

    # Mock page creation
    mock_page = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_page.goto = MagicMock()
    mock_page.wait_for_load_state = MagicMock()

    # Test concurrent tab opening
    import threading

    tab_ids = []
    errors = []

    def open_tab_worker():
        try:
            tab_id = browser.open_tab("https://example.com")
            tab_ids.append(tab_id)
        except Exception as e:
            errors.append(str(e))

    # Create multiple threads to open tabs concurrently
    threads = []
    for _i in range(10):
        thread = threading.Thread(target=open_tab_worker)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0

    # Verify all tab IDs are unique
    assert len(tab_ids) == 10
    assert len(set(tab_ids)) == 10

    # Verify tab IDs are sequential
    sorted_ids = sorted(tab_ids)
    for i, tab_id in enumerate(sorted_ids):
        assert tab_id == i + 1  # Starting from 1 since 0 is the original page
