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
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from PIL import Image

# Import the modules directly without global sys.modules mocking
from camel.toolkits.hybrid_browser_toolkit import HybridBrowserToolkit
from camel.utils.tool_result import ToolResult

TEST_URL = "https://example.com"
TEST_FILE_URL = "file:///test.html"


def create_mock_playwright_objects():
    """Create mock playwright objects for testing."""
    # Create comprehensive mock objects
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    mock_page.evaluate = AsyncMock(return_value={"elements": {}})
    mock_page.query_selector = AsyncMock(return_value=None)
    mock_page.query_selector_all = AsyncMock(return_value=[])
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.select_option = AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = AsyncMock()

    mock_context = AsyncMock()
    mock_context.pages = [mock_page]
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_context.browser = None

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_browser.contexts = [mock_context]

    mock_chromium = MagicMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)
    mock_chromium.launch_persistent_context = AsyncMock(
        return_value=mock_context
    )

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium = mock_chromium
    mock_playwright_instance.firefox = mock_chromium
    mock_playwright_instance.webkit = mock_chromium
    mock_playwright_instance.stop = AsyncMock()

    # Mock the async_playwright context manager
    mock_async_playwright_cm = AsyncMock()
    mock_async_playwright_cm.__aenter__ = AsyncMock(
        return_value=mock_playwright_instance
    )
    mock_async_playwright_cm.__aexit__ = AsyncMock(return_value=None)

    # Mock the async_playwright function
    mock_async_playwright = MagicMock(return_value=mock_async_playwright_cm)

    return (
        mock_async_playwright,
        mock_playwright_instance,
        mock_page,
        mock_context,
        mock_browser,
    )


# Create global mock objects for backward compatibility
(
    mock_async_playwright,
    mock_playwright_instance,
    mock_page,
    mock_context,
    mock_browser,
) = create_mock_playwright_objects()


@pytest.fixture(scope="function")
def mock_playwright_setup():
    """Set up playwright mocks for individual tests."""
    return create_mock_playwright_objects()


@pytest.fixture(autouse=True)
def mock_browser_dependencies():
    """Mock all browser-related dependencies for each test."""
    with (
        patch('os.makedirs'),
        patch('os.path.exists', return_value=True),
        patch(
            'playwright.async_api.async_playwright',
            return_value=mock_async_playwright(),
        ),
        patch(
            'camel.toolkits.hybrid_browser_toolkit.browser_session.async_playwright',
            return_value=mock_async_playwright(),
            create=True,
        ),
        patch(
            'builtins.open',
            mock_open(read_data="console.log('mock unified analyzer');"),
        ),
    ):
        yield


@pytest.fixture(scope="function")
def browser_toolkit_fixture():
    """Create a HybridBrowserToolkit instance for testing."""
    mock_session = AsyncMock()
    mock_session.ensure_browser = AsyncMock()
    mock_session.get_page = AsyncMock(return_value=mock_page)
    mock_session.visit = AsyncMock(return_value="Visited test URL")
    mock_session.get_snapshot = AsyncMock(
        return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
    )
    mock_session.exec_action = AsyncMock(
        return_value="Action executed successfully"
    )
    mock_session.close = AsyncMock()

    with (
        patch(
            'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
            return_value=mock_session,
        ),
        patch(
            'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
            return_value='mock_script_path',
        ),
        patch(
            'builtins.open', mock_open(read_data="console.log('mock script');")
        ),
    ):
        toolkit = HybridBrowserToolkit(headless=True)
        toolkit._session = mock_session  # Ensure the mock session is used
        yield toolkit

        # Cleanup
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.fixture(scope="function")
def mock_session():
    """Create a mock browser session."""
    session = AsyncMock()
    session.ensure_browser = AsyncMock()
    session.get_page = AsyncMock(return_value=mock_page)
    session.visit = AsyncMock(return_value="Visited test URL")
    session.get_snapshot = AsyncMock(
        return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
    )
    session.exec_action = AsyncMock(
        return_value="Action executed successfully"
    )
    session.close = AsyncMock()
    return session


@pytest.fixture(scope="function")
def mock_page_fixture():
    """Create a mock page object."""
    page = AsyncMock()
    page.url = TEST_URL
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.evaluate = AsyncMock(return_value={"elements": {}})
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.select_option = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()
    return page


@pytest.fixture(scope="function")
def sync_browser_toolkit():
    """Create a HybridBrowserToolkit instance for synchronous testing."""
    mock_session = AsyncMock()
    mock_session.ensure_browser = AsyncMock()
    mock_session.get_page = AsyncMock(return_value=mock_page)
    mock_session.visit = AsyncMock(return_value="Visited test URL")
    mock_session.get_snapshot = AsyncMock(
        return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
    )
    mock_session.exec_action = AsyncMock(
        return_value="Action executed successfully"
    )
    mock_session.close = AsyncMock()

    with (
        patch(
            'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
            return_value=mock_session,
        ),
        patch(
            'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
            return_value='mock_script_path',
        ),
        patch(
            'builtins.open', mock_open(read_data="console.log('mock script');")
        ),
    ):
        toolkit = HybridBrowserToolkit(headless=True)
        toolkit._session = mock_session  # Ensure the mock session is used
        return toolkit


class TestHybridBrowserToolkit:
    """Test cases for HybridBrowserToolkit."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_session = AsyncMock()
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session'
                '.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock unified analyzer');"),
            ),
            patch('os.path.exists', return_value=True),
            patch('os.makedirs'),
        ):
            toolkit = HybridBrowserToolkit()

            assert toolkit._headless is True
            assert toolkit._user_data_dir is None
            assert toolkit.web_agent_model is None
            assert toolkit.cache_dir == "tmp/"
            assert toolkit._agent is None
            assert toolkit._unified_script is not None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        test_cache_dir = "custom_cache"
        test_user_data_dir = "custom_user_data"

        mock_session = AsyncMock()
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session'
                '.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock unified analyzer');"),
            ),
            patch('os.path.exists', return_value=True),
            patch('os.makedirs'),
        ):
            toolkit = HybridBrowserToolkit(
                headless=False,
                user_data_dir=test_user_data_dir,
            )

            assert toolkit._headless is False
            assert toolkit._user_data_dir == test_user_data_dir
            assert toolkit.cache_dir == "tmp/"  # Default cache dir

        # Cleanup
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir, ignore_errors=True)

    def test_load_unified_analyzer_success(self):
        """Test successful loading of unified analyzer script."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.hybrid_browser_toolkit.browser_session'
            '.HybridBrowserSession',
            return_value=mock_session,
        ):
            with patch('builtins.open', create=True) as mock_file:
                # ruff:noqa:E501
                mock_file.return_value.__enter__.return_value.read.return_value = "console.log('test');"

                with (
                    patch('os.makedirs'),
                    patch('os.path.exists', return_value=True),
                ):
                    toolkit = HybridBrowserToolkit()
                    assert "console.log('test');" in toolkit._unified_script

    def test_load_unified_analyzer_file_not_found(self):
        """Test handling of missing unified analyzer script."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.hybrid_browser_toolkit.browser_session'
            '.HybridBrowserSession',
            return_value=mock_session,
        ):
            with (
                patch('builtins.open', side_effect=FileNotFoundError),
                patch('os.makedirs'),
                patch('os.path.exists', return_value=True),
            ):
                with pytest.raises(FileNotFoundError):
                    HybridBrowserToolkit()

    def test_validate_ref_valid(self):
        """Test ref validation with valid input."""
        mock_session = AsyncMock()
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session'
                '.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
            patch('os.makedirs'),
            patch('os.path.exists', return_value=True),
        ):
            toolkit = HybridBrowserToolkit()
            # Should not raise exception
            toolkit._validate_ref("e1", "test_method")

    def test_validate_ref_invalid(self):
        """Test ref validation with invalid input."""
        mock_session = AsyncMock()
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session'
                '.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
            patch('os.makedirs'),
            patch('os.path.exists', return_value=True),
        ):
            toolkit = HybridBrowserToolkit()

            # Test with empty string
            with pytest.raises(ValueError):
                toolkit._validate_ref("", "test_method")

    @pytest.mark.asyncio
    async def test_open_browser_no_start_url(self, browser_toolkit_fixture):
        """Test opening browser using the default start URL configured during initialization."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.open_browser()

        assert "Visited" in result["result"]
        assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_open_browser_with_custom_default_url(
        self, browser_toolkit_fixture
    ):
        """Test open_browser with a custom default start URL."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.open_browser()

        # Just check that the method works and returns expected structure
        assert "result" in result
        assert "snapshot" in result
        assert "Visited" in result['result']

    @pytest.mark.asyncio
    async def test_close_browser(self, browser_toolkit_fixture):
        """Test closing browser."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.close_browser()
        assert isinstance(result, str)
        assert "closed" in result.lower()

    @pytest.mark.asyncio
    async def test_visit_page_valid_url(self, browser_toolkit_fixture):
        """Test visiting a valid URL."""
        toolkit = browser_toolkit_fixture
        mock_session = toolkit._session

        # Mock create_new_tab to return a mock tab index
        mock_session.create_new_tab = AsyncMock(return_value=1)
        mock_session.visit = AsyncMock(
            return_value=f"Visited {TEST_URL} in new tab 1"
        )
        mock_session.switch_to_tab = AsyncMock()
        mock_session.get_snapshot = AsyncMock(return_value="snapshot")

        # Mock _get_tab_info_for_output
        with patch.object(
            toolkit, '_get_tab_info_for_output', new_callable=AsyncMock
        ) as mock_get_tab_info:
            mock_get_tab_info.return_value = {
                "tabs": [],
                "current_tab": 1,
                "total_tabs": 2,
            }
            result = await toolkit.visit_page(TEST_URL)
            mock_session.create_new_tab.assert_called_once_with(TEST_URL)
            mock_session.switch_to_tab.assert_called_once_with(1)
            mock_session.get_snapshot.assert_called_once()
            assert "snapshot" in result
            assert result['snapshot'] == "snapshot"
            assert TEST_URL in result['result']
            assert "new tab" in result['result']

    @pytest.mark.asyncio
    async def test_visit_page_invalid_url(self, browser_toolkit_fixture):
        """Test visiting an invalid URL (empty string)."""
        toolkit = browser_toolkit_fixture
        mock_session = toolkit._session
        mock_session.create_new_tab = AsyncMock()
        result = await toolkit.visit_page("")
        mock_session.create_new_tab.assert_not_called()
        assert "Error: 'url' must be a non-empty string" in result['result']
        assert result['snapshot'] == ""

    @pytest.mark.asyncio
    async def test_get_page_snapshot(
        self, browser_toolkit_fixture, mock_page_fixture
    ):
        """Test getting page snapshot."""
        toolkit = browser_toolkit_fixture
        mock_page = mock_page_fixture
        toolkit._session.get_page = AsyncMock(return_value=mock_page)

        # Mock unified analysis
        mock_analysis = {
            "snapshotText": "Test snapshot content",
            "elements": {"e1": {"role": "button", "name": "Test"}},
        }
        mock_page.evaluate = AsyncMock(return_value=mock_analysis)
        result = await toolkit.get_page_snapshot()
        assert result == "Test snapshot content"

    @pytest.mark.asyncio
    async def test_get_som_screenshot_success(self):
        """Test successful Set of Marks screenshot generation."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            # Create a mock image
            mock_image = Image.new('RGB', (100, 100), color='red')
            img_byte_arr = io.BytesIO()
            mock_image.save(img_byte_arr, format='PNG')
            mock_image_data = img_byte_arr.getvalue()

            # Set up the mock page with screenshot and analysis data
            mock_page.screenshot = AsyncMock(return_value=mock_image_data)
            mock_page.url = TEST_URL

            # Mock unified analysis
            mock_analysis = {
                "elements": {
                    "e1": {
                        "role": "button",
                        "name": "Test Button",
                        "coordinates": [
                            {"x": 10, "y": 10, "width": 50, "height": 20}
                        ],
                    }
                }
            }
            mock_page.evaluate = AsyncMock(return_value=mock_analysis)

            result = await toolkit.get_som_screenshot()

            assert isinstance(result, ToolResult)
            assert "Visual webpage screenshot captured" in result.text
            assert len(result.images) == 1
            assert result.images[0].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_get_som_screenshot_pil_not_available(self):
        """Test Set of Marks screenshot when PIL is not available."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            # Create a mock image for the screenshot
            mock_image = Image.new('RGB', (100, 100), color='red')
            img_byte_arr = io.BytesIO()
            mock_image.save(img_byte_arr, format='PNG')
            mock_image_data = img_byte_arr.getvalue()

            # Set up the mock page with screenshot data
            mock_page.screenshot = AsyncMock(return_value=mock_image_data)
            mock_page.url = TEST_URL

            # Mock unified analysis - provide empty elements to avoid coordinate processing
            mock_analysis = {"elements": {}}
            mock_page.evaluate = AsyncMock(return_value=mock_analysis)

            with patch('PIL.ImageDraw', side_effect=ImportError):
                result = await toolkit.get_som_screenshot()

                assert isinstance(result, ToolResult)
                assert "Visual webpage screenshot captured" in result.text

    @pytest.mark.asyncio
    async def test_click_valid_ref(self):
        """Test clicking with valid reference."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            # Mock the _get_unified_analysis method to include e1 element
            mock_analysis = {"elements": {"e1": {"role": "button"}}}
            toolkit._get_unified_analysis = AsyncMock(
                return_value=mock_analysis
            )

            result = await toolkit.click(ref="e1")

            assert result["result"] == "Action executed successfully"
            assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_click_invalid_ref(self):
        """Test clicking with invalid reference."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            with pytest.raises(ValueError):
                await toolkit.click(ref="")

    @pytest.mark.asyncio
    async def test_type_text(self, browser_toolkit_fixture):
        """Test typing text in element."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.type(ref="input_element", text="Hello World")
        assert result["result"] == "Action executed successfully"
        assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_select_option(self, browser_toolkit_fixture):
        """Test selecting option in dropdown."""
        toolkit = browser_toolkit_fixture

        result = await toolkit.select(ref="select_element", value="option1")

        assert result["result"] == "Action executed successfully"
        assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_scroll_valid_direction(self):
        """Test scrolling with valid direction."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            result = await toolkit.scroll(direction="down", amount=100)

            assert result["result"] == "Action executed successfully"
            assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self):
        """Test scrolling with invalid direction."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            result = await toolkit.scroll(
                direction="invalid_direction", amount=100
            )
            assert (
                "Error: direction must be 'up' or 'down'" in result["result"]
            )

    @pytest.mark.asyncio
    async def test_get_page_links_valid_refs(
        self, browser_toolkit_fixture, mock_page_fixture
    ):
        """Test getting page links with valid references."""
        toolkit = browser_toolkit_fixture
        mock_page = mock_page_fixture
        toolkit._session.get_page = AsyncMock(return_value=mock_page)

        # Mock page evaluate to return links
        mock_links = [
            {"href": "https://example.com/page1", "text": "Page 1"},
            {"href": "https://example.com/page2", "text": "Page 2"},
        ]
        mock_page.evaluate = AsyncMock(return_value=mock_links)

        result = await toolkit.get_page_links(ref=["e1", "e2"])

        assert "links" in result
        assert isinstance(result["links"], list)

    @pytest.mark.asyncio
    async def test_get_page_links_invalid_refs(self):
        """Test getting page links with invalid references."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            result = await toolkit.get_page_links(ref=[])
            assert result["links"] == []

    @pytest.mark.asyncio
    async def test_wait_user_no_timeout(self):
        """Test waiting for user input without timeout."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            # Mock user input
            with patch('builtins.input', return_value='continue'):
                result = await toolkit.wait_user()

                assert result["result"] == "User resumed."
                assert "snapshot" in result

    @pytest.mark.asyncio
    async def test_wait_user_with_timeout(self):
        """Test waiting for user input with timeout."""
        mock_session = AsyncMock()
        mock_session.ensure_browser = AsyncMock()
        mock_session.get_page = AsyncMock(return_value=mock_page)
        mock_session.visit = AsyncMock(return_value="Visited test URL")
        mock_session.get_snapshot = AsyncMock(
            return_value="- Page Snapshot\\n```yaml\\n<test content>\\n```"
        )
        mock_session.exec_action = AsyncMock(
            return_value="Action executed successfully"
        )
        mock_session.close = AsyncMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=mock_session,
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(headless=True)
            toolkit._session = mock_session

            # Mock asyncio.wait_for to simulate timeout
            import asyncio

            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                result = await toolkit.wait_user(timeout_sec=1.0)

                assert (
                    "Timeout 1.0s reached, auto-resumed." in result["result"]
                )
                assert "snapshot" in result

    def test_get_tools(self, sync_browser_toolkit):
        """Test getting available tools with default configuration."""
        toolkit = sync_browser_toolkit

        tools = toolkit.get_tools()

        # Default tools should be 5 tools (updated default configuration)
        assert len(tools) == 8

        tool_names = [tool.func.__name__ for tool in tools]

        expected_default_tools = [
            "open_browser",
            "close_browser",
            "visit_page",
            "back",
            "forward",
            "click",
            "type",
            "switch_tab",
        ]

        for expected_tool in expected_default_tools:
            assert expected_tool in tool_names

    def test_get_tools_with_web_agent_model(self, sync_browser_toolkit):
        """Test getting tools when web_agent_model is provided."""
        mock_model = MagicMock()
        toolkit = sync_browser_toolkit

        # Simulate having a web agent model
        toolkit.web_agent_model = mock_model

        tools = toolkit.get_tools()

        # Default tools should be 6, even with web_agent_model set
        # unless solve_task is explicitly enabled
        assert len(tools) == 8
        tool_names = [tool.func.__name__ for tool in tools]

        # Should not automatically include solve_task unless explicitly enabled
        assert 'solve_task' not in tool_names

    def test_get_tools_with_solve_task_enabled(self):
        """Test getting tools when solve_task is explicitly enabled."""
        mock_model = MagicMock()

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=AsyncMock(),
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(
                headless=True,
                web_agent_model=mock_model,
                enabled_tools=['open_browser', 'close_browser', 'solve_task'],
            )

            tools = toolkit.get_tools()
            tool_names = [tool.func.__name__ for tool in tools]

            assert len(tools) == 3
            assert 'solve_task' in tool_names
            assert 'open_browser' in tool_names
            assert 'close_browser' in tool_names

    def test_get_tools_custom_selection(self):
        """Test getting tools with custom tool selection."""
        custom_tools = [
            "open_browser",
            "close_browser",
            "visit_page",
            "back",
            "forward",
            "click",
            "type",
            "switch_tab",
        ]

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserSession',
                return_value=AsyncMock(),
            ),
            patch(
                'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.os.path.join',
                return_value='mock_script_path',
            ),
            patch(
                'builtins.open',
                mock_open(read_data="console.log('mock script');"),
            ),
        ):
            toolkit = HybridBrowserToolkit(
                headless=True, enabled_tools=custom_tools
            )

            tools = toolkit.get_tools()
            tool_names = [tool.func.__name__ for tool in tools]

            assert len(tools) == 8
            for expected_tool in custom_tools:
                assert expected_tool in tool_names

    def test_convert_analysis_to_rects(self, sync_browser_toolkit):
        """Test converting analysis data to rect format."""
        toolkit = sync_browser_toolkit

        analysis_data = {
            "elements": {
                "e1": {
                    "role": "button",
                    "name": "Submit",
                    "coordinates": [
                        {"x": 10, "y": 20, "width": 50, "height": 30}
                    ],
                }
            }
        }

        rects = toolkit._convert_analysis_to_rects(analysis_data)

        assert "e1" in rects
        assert rects["e1"]["role"] == "button"
        assert rects["e1"]["aria-name"] == "Submit"
        assert len(rects["e1"]["rects"]) == 1
        assert rects["e1"]["rects"][0]["x"] == 10

    def test_format_snapshot_from_analysis(self, sync_browser_toolkit):
        """Test formatting snapshot from analysis data."""
        toolkit = sync_browser_toolkit

        analysis_data = {
            "elements": {
                "e1": {
                    "role": "button",
                    "name": "Submit",
                    "disabled": True,
                },
                "e2": {
                    "role": "checkbox",
                    "name": "Agree",
                    "checked": True,
                },
            }
        }

        snapshot = toolkit._format_snapshot_from_analysis(analysis_data)

        assert "[ref=e1]" in snapshot
        assert "button" in snapshot
        assert "Submit" in snapshot
        assert "disabled" in snapshot
        assert "[ref=e2]" in snapshot
        assert "checkbox" in snapshot
        assert "checked" in snapshot

    def test_add_set_of_mark_with_pil(self, sync_browser_toolkit):
        """Test adding visual marks to image."""
        toolkit = sync_browser_toolkit

        # Create test image
        test_image = Image.new('RGB', (200, 200), color='white')

        # Test rects data
        rects = {
            "e1": {
                "role": "button",
                "rects": [{"x": 10, "y": 10, "width": 50, "height": 20}],
            }
        }

        marked_image = toolkit._add_set_of_mark(test_image, rects)

        assert isinstance(marked_image, Image.Image)
        assert marked_image.size == test_image.size

    def test_add_set_of_mark_without_pil(self, sync_browser_toolkit):
        """Test adding visual marks when PIL is not available."""
        toolkit = sync_browser_toolkit

        test_image = Image.new('RGB', (200, 200), color='white')

        with patch('PIL.ImageDraw', side_effect=ImportError):
            result = toolkit._add_set_of_mark(test_image, {})

            # Should return original image when PIL not available
            assert result == test_image

    @pytest.mark.asyncio
    async def test_simple_async_creation(self, browser_toolkit_fixture):
        """Simple test to verify async toolkit creation works with mocks."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.open_browser()
        assert "Visited" in result["result"]
        assert "snapshot" in result


class TestActionExecutorTimeouts:
    """Test ActionExecutor timeout configuration functionality."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock page for ActionExecutor tests."""
        page = AsyncMock()
        page.locator = MagicMock(return_value=AsyncMock())
        page.locator.return_value.count = AsyncMock(return_value=1)
        page.locator.return_value.first = AsyncMock()
        page.locator.return_value.first.click = AsyncMock()
        page.fill = AsyncMock()
        page.select_option = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.text_content = AsyncMock(return_value="test text")
        page.wait_for_load_state = AsyncMock()
        return page

    def test_action_executor_default_timeouts(self, mock_page):
        """Test that ActionExecutor uses default timeouts when none provided."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(mock_page)

        assert executor.default_timeout == 3000
        assert executor.short_timeout == 1000

    def test_action_executor_constructor_timeouts(self, mock_page):
        """Test that ActionExecutor respects constructor timeout parameters."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page, default_timeout=5000, short_timeout=2000
        )

        assert executor.default_timeout == 5000
        assert executor.short_timeout == 2000

    @patch.dict(
        'os.environ',
        {
            'HYBRID_BROWSER_DEFAULT_TIMEOUT': '7000',
            'HYBRID_BROWSER_SHORT_TIMEOUT': '3500',
        },
    )
    def test_action_executor_environment_timeouts(self, mock_page):
        """Test that ActionExecutor respects environment variable timeouts."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(mock_page)

        assert executor.default_timeout == 7000
        assert executor.short_timeout == 3500

    @patch.dict(
        'os.environ',
        {
            'HYBRID_BROWSER_DEFAULT_TIMEOUT': '7000',
            'HYBRID_BROWSER_SHORT_TIMEOUT': '3500',
        },
    )
    def test_action_executor_constructor_precedence_over_env(self, mock_page):
        """Test that constructor parameters take precedence over environment variables."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page, default_timeout=9000, short_timeout=4500
        )

        # Constructor params should override environment variables
        assert executor.default_timeout == 9000
        assert executor.short_timeout == 4500

    @patch.dict('os.environ', {'HYBRID_BROWSER_DEFAULT_TIMEOUT': '7000'})
    def test_action_executor_partial_env_override(self, mock_page):
        """Test partial environment variable override with constructor params."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page,
            short_timeout=2500,  # Only override short_timeout
        )

        # Should use env var for default_timeout, constructor for short_timeout
        assert executor.default_timeout == 7000
        assert executor.short_timeout == 2500

    @pytest.mark.asyncio
    async def test_action_executor_uses_configured_timeouts_in_fill(
        self, mock_page
    ):
        """Test that ActionExecutor uses configured timeouts in operations."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page, default_timeout=6000, short_timeout=2500
        )

        # Test that fill operation uses the configured short_timeout
        action = {"type": "type", "ref": "test", "text": "hello"}
        await executor._type(action)

        mock_page.fill.assert_called_once()
        call_args = mock_page.fill.call_args
        assert call_args[1]["timeout"] == 2500  # Should use short_timeout

    @pytest.mark.asyncio
    async def test_action_executor_uses_configured_timeouts_in_select(
        self, mock_page
    ):
        """Test that ActionExecutor uses configured timeouts in select operations."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page, default_timeout=8000, short_timeout=3000
        )

        # Test that select operation uses the configured default_timeout
        action = {"type": "select", "ref": "test", "value": "option1"}
        await executor._select(action)

        mock_page.select_option.assert_called_once()
        call_args = mock_page.select_option.call_args
        assert call_args[1]["timeout"] == 8000  # Should use default_timeout

    @pytest.mark.asyncio
    async def test_action_executor_uses_configured_timeouts_in_wait(
        self, mock_page
    ):
        """Test that ActionExecutor uses configured timeouts in wait operations."""
        from camel.toolkits.hybrid_browser_toolkit.actions import (
            ActionExecutor,
        )

        executor = ActionExecutor(
            mock_page, default_timeout=7500, short_timeout=2750
        )

        # Test that wait operation uses the configured default_timeout
        action = {"type": "wait", "selector": "test"}
        await executor._wait(action)

        mock_page.wait_for_selector.assert_called_once()
        call_args = mock_page.wait_for_selector.call_args
        assert call_args[1]["timeout"] == 7500  # Should use default_timeout
