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


def test_browser_get_screenshot(base_browser_fixture):
    browser = base_browser_fixture
    browser.init()

    # Create a mock image for testing
    mock_image = Image.new('RGB', (100, 100))
    img_byte_arr = io.BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    browser.page.screenshot = MagicMock(return_value=img_byte_arr)

    image, file_path = browser.get_screenshot(save_image=False)
    assert isinstance(image, Image.Image)
    assert file_path is None


def test_browser_toolkit_browse_url(browser_toolkit_fixture):
    toolkit = browser_toolkit_fixture

    # Mock necessary components
    toolkit.browser.visit_page = MagicMock()
    toolkit._observe = MagicMock(return_value=("obs", "reason", "stop()"))
    toolkit._get_final_answer = MagicMock(return_value="Task completed")

    result = toolkit.browse_url(
        task_prompt="Test task", start_url=TEST_URL, round_limit=1
    )

    assert result == "Task completed"
    toolkit.browser.visit_page.assert_called_once_with(TEST_URL)


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


def test_browser_get_url(base_browser_fixture):
    browser = base_browser_fixture
    browser.init()

    browser.page.url = TEST_URL

    assert browser.get_url() == TEST_URL


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


def test_visual_viewport_from_dict():
    viewport_dict = {
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
    viewport = visual_viewport_from_dict(viewport_dict)
    assert viewport["height"] == 800
    assert viewport["scrollHeight"] == 1200


# Add these tests at the end of the file, before the last test


def test_base_browser_multi_tab_initialization(base_browser_fixture):
    """Test that multi-tab support is properly initialized."""
    browser = base_browser_fixture
    browser.init()

    # Check that tabs dictionary is initialized
    assert hasattr(browser, 'tabs')
    assert isinstance(browser.tabs, dict)

    # Check that current_tab_id is initialized
    assert hasattr(browser, 'current_tab_id')
    assert browser.current_tab_id == 0

    # Check that initial page is registered as tab 0
    assert 0 in browser.tabs
    assert browser.tabs[0] == browser.page


def test_open_tab(base_browser_fixture):
    """Test opening a new tab."""
    browser = base_browser_fixture
    browser.init()

    # Mock the context and page creation
    mock_new_page = MagicMock()
    browser.context.new_page = MagicMock(return_value=mock_new_page)
    mock_new_page.goto = MagicMock()

    # Test opening a new tab
    new_tab_id = browser.open_tab("https://example.com")

    # Verify the new tab was created
    assert new_tab_id == 1  # Should be the next available ID
    assert new_tab_id in browser.tabs
    assert browser.tabs[new_tab_id] == mock_new_page

    # Verify the page navigation was called
    browser.context.new_page.assert_called_once()
    mock_new_page.goto.assert_called_once_with("https://example.com")


def test_open_multiple_tabs(base_browser_fixture):
    """Test opening multiple tabs and verify ID assignment."""
    browser = base_browser_fixture
    browser.init()

    # Mock the context and page creation
    mock_pages = [MagicMock() for _ in range(3)]
    browser.context.new_page = MagicMock(side_effect=mock_pages)

    for mock_page in mock_pages:
        mock_page.goto = MagicMock()

    # Open multiple tabs
    tab_ids = []
    urls = [
        "https://example1.com",
        "https://example2.com",
        "https://example3.com",
    ]

    for url in urls:
        tab_id = browser.open_tab(url)
        tab_ids.append(tab_id)

    # Verify tab IDs are sequential
    assert tab_ids == [1, 2, 3]

    # Verify all tabs are in the tabs dictionary
    for tab_id in tab_ids:
        assert tab_id in browser.tabs
        assert browser.tabs[tab_id] in mock_pages


def test_switch_tab(base_browser_fixture):
    """Test switching between tabs."""
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

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.current_tab_id = 0

    # Test switching to tab 1
    browser.switch_tab(1)
    assert browser.current_tab_id == 1
    assert browser.page == mock_page_1

    # Test switching to tab 2
    browser.switch_tab(2)
    assert browser.current_tab_id == 2
    assert browser.page == mock_page_2

    # Test switching back to tab 0
    browser.switch_tab(0)
    assert browser.current_tab_id == 0
    assert browser.page == mock_page_0


def test_switch_tab_invalid_id(base_browser_fixture):
    """Test that switching to an invalid tab ID raises an error."""
    browser = base_browser_fixture
    browser.init()

    # Set up tabs with only tab 0
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    # Test switching to non-existent tab
    with pytest.raises(ValueError, match="Tab 5 does not exist"):
        browser.switch_tab(5)


def test_close_tab(base_browser_fixture):
    """Test closing a tab."""
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

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}

    browser.switch_tab(1)

    # Test closing tab 2 (not the current tab)
    browser.close_tab(2)

    # Verify tab 2 is removed
    assert 2 not in browser.tabs
    assert browser.current_tab_id == 1  # Current tab unchanged
    assert browser.page == mock_page_1  # Page unchanged

    # Verify tab 2 was closed
    mock_page_2.close.assert_called_once()


def test_close_current_tab(base_browser_fixture):
    """Test closing the current tab and switching to another tab."""
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

    # Set up tabs dictionary
    browser.tabs = {0: mock_page_0, 1: mock_page_1, 2: mock_page_2}
    browser.switch_tab(1)  # Currently on tab 1

    # Test closing current tab (tab 1)
    browser.close_tab(1)

    # Verify tab 1 is removed
    assert 1 not in browser.tabs

    # Verify current tab switched to the first remaining tab (tab 0)
    assert browser.current_tab_id == 0
    assert browser.page == mock_page_0

    # Verify tab 1 was closed
    mock_page_1.close.assert_called_once()


def test_close_last_tab(base_browser_fixture):
    """Test closing the last remaining tab."""
    browser = base_browser_fixture
    browser.init()

    # Set up only one tab
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    page_to_close = browser.page
    # Test closing the last tab
    browser.close_tab(0)

    # Verify tab is removed
    assert 0 not in browser.tabs

    # Verify current tab is reset
    assert browser.current_tab_id is None
    assert browser.page is None

    # Verify page was closed
    page_to_close.close.assert_called_once()


def test_close_tab_invalid_id(base_browser_fixture):
    """Test that closing an invalid tab ID raises an error."""
    browser = base_browser_fixture
    browser.init()

    # Set up tabs with only tab 0
    browser.tabs = {0: browser.page}
    browser.current_tab_id = 0

    # Test closing non-existent tab
    with pytest.raises(ValueError, match="This tab does not exist"):
        browser.close_tab(3)


def test_multi_tab_integration(base_browser_fixture):
    """Test a complete multi-tab workflow."""
    browser = base_browser_fixture
    browser.init()

    # Configure the original page's is_closed method
    browser.page.is_closed.return_value = False

    # Mock context and page creation
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    browser.context.new_page = MagicMock(
        side_effect=[mock_page_1, mock_page_2]
    )

    for mock_page in [mock_page_1, mock_page_2]:
        mock_page.goto = MagicMock()
        mock_page.close = MagicMock()
        mock_page.is_closed.return_value = (
            False  # Configure is_closed to return False initially
        )

    # Step 1: Open first new tab
    tab1_id = browser.open_tab("https://example1.com")
    assert tab1_id == 1
    assert browser.tabs[1] == mock_page_1

    # Step 2: Open second new tab
    tab2_id = browser.open_tab("https://example2.com")
    assert tab2_id == 2
    assert browser.tabs[2] == mock_page_2

    # Step 3: Switch to tab 1
    browser.switch_tab(1)
    assert browser.current_tab_id == 1
    assert browser.page == mock_page_1

    # Step 4: Switch to tab 2
    browser.switch_tab(2)
    assert browser.current_tab_id == 2
    assert browser.page == mock_page_2

    # Step 5: Close tab 1
    browser.close_tab(1)
    assert 1 not in browser.tabs
    assert browser.current_tab_id == 2  # Should stay on current tab

    # Step 6: Close current tab (tab 2)
    browser.close_tab(2)
    assert 2 not in browser.tabs
    assert browser.current_tab_id == 0  # Should switch to remaining tab
    assert browser.page == browser.tabs[0]  # Should be the original page


def test_browser_toolkit_reset_multi_tab(browser_toolkit_fixture):
    """Test that _reset properly clears multi-tab state."""
    toolkit = browser_toolkit_fixture

    # Initialize browser and add some tabs
    toolkit.browser.init()
    toolkit.browser.tabs = {
        0: toolkit.browser.page,
        1: MagicMock(),
        2: MagicMock(),
    }
    toolkit.browser.current_tab_id = 2

    # Call _reset
    toolkit._reset()

    # Verify tabs are cleared
    assert toolkit.browser.tabs == {}
    assert toolkit.browser.current_tab_id is None


def test_browse_url_with_multi_tab_info(browser_toolkit_fixture):
    """Test that browse_url includes multi-tab information in trajectory."""
    toolkit = browser_toolkit_fixture

    # Mock necessary components
    toolkit.browser.visit_page = MagicMock()
    toolkit._observe = MagicMock(return_value=("obs", "reason", "stop()"))
    toolkit._get_final_answer = MagicMock(return_value="Task completed")

    # Set up some tabs
    toolkit.browser.tabs = {0: toolkit.browser.page, 1: MagicMock()}
    toolkit.browser.current_tab_id = 1

    result = toolkit.browse_url(
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
