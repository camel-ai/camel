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
    dom_rectangle_from_dict,
    interactive_region_from_dict,
    visual_viewport_from_dict,
)

TEST_URL = "https://example.com"


@pytest.fixture(scope="function")
def base_browser_fixture():
    with patch('playwright.sync_api.sync_playwright') as mock_sync_playwright:
        # Mock the browser context and page for launch_persistent_context
        mock_context = MagicMock()
        mock_page = MagicMock()
        # ruff: noqa: E501
        (
            mock_sync_playwright.return_value.__enter__().chromium.launch_persistent_context.return_value
        ) = mock_context
        mock_context.new_page.return_value = mock_page

        browser = BaseBrowser(headless=True, cache_dir="test_cache")
        browser.init()  # Must call init() to launch persistent context
        yield browser
        # Clean up
        browser.close()
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache")


@pytest.fixture(scope="function")
def browser_toolkit_fixture():
    with patch('playwright.sync_api.sync_playwright') as mock_sync_playwright:
        # Mock the browser context and page for launch_persistent_context
        mock_context = MagicMock()
        mock_page = MagicMock()
        # ruff: noqa: E501
        (
            mock_sync_playwright.return_value.__enter__().chromium.launch_persistent_context.return_value
        ) = mock_context
        mock_context.new_page.return_value = mock_page
        toolkit = BrowserToolkit(headless=True, cache_dir="test_cache")
        toolkit.browser.init()
        yield toolkit
        # Clean up
        toolkit.browser.close()
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache")


def test_base_browser_init(base_browser_fixture):
    browser = base_browser_fixture
    assert browser.headless is True
    assert browser.cache_dir == "test_cache"
    assert isinstance(browser.history, list)
    assert isinstance(browser.page_history, list)


def test_base_browser_initialization_order():
    with patch('playwright.sync_api.sync_playwright') as mock_sync_playwright:
        mock_playwright = MagicMock()
        mock_chromium = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_sync_playwright.return_value.__enter__.return_value = (
            mock_playwright
        )
        mock_chromium.launch_persistent_context = MagicMock()
        browser = BaseBrowser(headless=True)
        assert browser.browser is None
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_chromium.launch_persistent_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        browser.init()
        assert browser.browser is not None
        assert browser.page is not None


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

    browser.page.goto = MagicMock()
    browser.page.wait_for_load_state = MagicMock()

    browser.visit_page(TEST_URL)

    browser.page.goto.assert_called_once_with(TEST_URL)
    browser.page.wait_for_load_state.assert_called_once()


def test_browser_get_screenshot(base_browser_fixture):
    browser = base_browser_fixture

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

    os.makedirs(browser.cache_dir, exist_ok=True)
    test_file = os.path.join(browser.cache_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    browser.clean_cache()
    assert not os.path.exists(browser.cache_dir)


def test_browser_click_blank_area(base_browser_fixture):
    browser = base_browser_fixture

    browser.page.mouse.click = MagicMock()
    browser.page.wait_for_load_state = MagicMock()

    browser.click_blank_area()

    browser.page.mouse.click.assert_called_once_with(0, 0)
    browser.page.wait_for_load_state.assert_called_once()


def test_browser_get_url(base_browser_fixture):
    browser = base_browser_fixture

    browser.page.url = TEST_URL

    assert browser.get_url() == TEST_URL


def test_browser_back_navigation(base_browser_fixture):
    browser = base_browser_fixture

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
