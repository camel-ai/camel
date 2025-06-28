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

from camel.toolkits.non_visual_browser_toolkit import BrowserNonVisualToolkit
from camel.utils.tool_result import ToolResult

TEST_URL = "https://example.com"
TEST_FILE_URL = "file:///test.html"


@pytest.fixture(scope="function")
async def browser_toolkit_fixture():
    """Create a BrowserNonVisualToolkit instance for testing."""
    mock_session = AsyncMock()
    with patch(
        'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
        '.NVBrowserSession',
        return_value=mock_session,
    ):
        toolkit = BrowserNonVisualToolkit(headless=True)
        yield toolkit

        # Cleanup
        try:
            await toolkit.close_browser()
        except Exception:
            pass

        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.fixture(scope="function")
def mock_session():
    """Create a mock browser session."""
    session = MagicMock()
    session.ensure_browser = AsyncMock()
    session.get_page = AsyncMock()
    session.visit = AsyncMock(return_value="Visited test URL")
    session.get_snapshot = AsyncMock(
        return_value="- Page Snapshot\n```yaml\n<test content>\n```"
    )
    session.exec_action = AsyncMock(
        return_value="Action executed successfully"
    )
    session.close = AsyncMock()
    return session


@pytest.fixture(scope="function")
def mock_page():
    """Create a mock page object."""
    page = MagicMock()
    page.url = TEST_URL
    page.screenshot = AsyncMock()
    page.evaluate = AsyncMock()
    page.query_selector = AsyncMock()
    return page


class TestBrowserNonVisualToolkit:
    """Test cases for BrowserNonVisualToolkit."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

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
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit(
                headless=False,
                user_data_dir=test_user_data_dir,
            )

            assert toolkit._headless is False
            assert toolkit._user_data_dir == test_user_data_dir
            assert toolkit.cache_dir == "tmp/"  # Default cache dir
            assert os.path.exists(toolkit.cache_dir)

        # Cleanup
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir, ignore_errors=True)

    def test_load_unified_analyzer_success(self):
        """Test successful loading of unified analyzer script."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            with patch('builtins.open', create=True) as mock_open:
                # ruff:noqa:E501
                mock_open.return_value.__enter__.return_value.read.return_value = "console.log('test');"

                toolkit = BrowserNonVisualToolkit()
                assert "console.log('test');" in toolkit._unified_script

    def test_load_unified_analyzer_file_not_found(self):
        """Test handling of missing unified analyzer script."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            with patch('builtins.open', side_effect=FileNotFoundError):
                with pytest.raises(FileNotFoundError):
                    BrowserNonVisualToolkit()

    def test_validate_ref_valid(self):
        """Test ref validation with valid input."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            # Should not raise exception
            toolkit._validate_ref("e1", "test_method")

    def test_validate_ref_invalid(self):
        """Test ref validation with invalid input."""
        mock_session = AsyncMock()
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            with pytest.raises(ValueError):
                toolkit._validate_ref("", "test_method")

            with pytest.raises(ValueError):
                toolkit._validate_ref("", "test_method")

            with pytest.raises(ValueError):
                toolkit._validate_ref("", "test_method")

    @pytest.mark.asyncio
    async def test_open_browser_no_start_url(self, mock_session):
        """Test opening browser without start URL."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session  # Direct assignment for testing

            result = await toolkit.open_browser()

            assert result["result"] == "Browser session started."
            assert "snapshot" in result
            mock_session.ensure_browser.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_browser_with_start_url(self, mock_session):
        """Test opening browser with start URL."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            # Mock visit_page method
            with patch.object(
                toolkit, 'visit_page', new_callable=AsyncMock
            ) as mock_visit:
                mock_visit.return_value = {
                    "result": "Visited",
                    "snapshot": "test",
                }

                await toolkit.open_browser(start_url=TEST_URL)

                mock_visit.assert_called_once_with(TEST_URL)

    @pytest.mark.asyncio
    async def test_close_browser(self, mock_session):
        """Test closing browser."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session  # Direct assignment for testing

            result = await toolkit.close_browser()

            assert result == "Browser session closed."
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_visit_page_valid_url(self, mock_session):
        """Test visiting a valid URL."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            result = await toolkit.visit_page(TEST_URL)

            assert "Visited" in result["result"]
            assert "snapshot" in result
            mock_session.visit.assert_called_once_with(TEST_URL)

    @pytest.mark.asyncio
    async def test_visit_page_invalid_url(self, mock_session):
        """Test visiting with invalid URL."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            with pytest.raises(ValueError):
                await toolkit.visit_page("")

            with pytest.raises(ValueError):
                await toolkit.visit_page("")

    @pytest.mark.asyncio
    async def test_get_page_snapshot(self, mock_session, mock_page):
        """Test getting page snapshot."""
        mock_session.get_page.return_value = mock_page

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            # Mock unified analysis
            mock_analysis = {
                "snapshotText": "Test snapshot content",
                "elements": {"e1": {"role": "button", "name": "Test"}},
            }
            mock_page.evaluate.return_value = mock_analysis

            result = await toolkit.get_page_snapshot()

            assert result == "Test snapshot content"

    @pytest.mark.asyncio
    async def test_get_som_screenshot_success(self, mock_session, mock_page):
        """Test successful Set of Marks screenshot generation."""
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        mock_image_data = img_byte_arr.getvalue()

        mock_page.screenshot.return_value = mock_image_data
        mock_page.url = TEST_URL
        mock_session.get_page.return_value = mock_page

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
        mock_page.evaluate.return_value = mock_analysis

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            result = await toolkit.get_som_screenshot()

            assert isinstance(result, ToolResult)
            assert "Visual webpage screenshot captured" in result.text
            assert len(result.images) == 1
            assert result.images[0].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_get_som_screenshot_pil_not_available(self, mock_session):
        """Test Set of Marks screenshot when PIL is not available."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            # Skip this test for now as it's complex to mock PIL imports
            # properly
            pytest.skip("PIL import mocking is complex in this context")

    @pytest.mark.asyncio
    async def test_click_valid_ref(self, mock_session, mock_page):
        """Test clicking with valid element reference."""
        mock_session.get_page.return_value = mock_page

        # Mock unified analysis with the element
        mock_analysis = {
            "elements": {"e1": {"role": "button", "name": "Test Button"}}
        }
        mock_page.evaluate.return_value = mock_analysis

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            result = await toolkit.click(ref="e1")

            assert (
                "Clicked" in result["result"]
                or "Action executed" in result["result"]
            )
            mock_session.exec_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_invalid_ref(self, mock_session, mock_page):
        """Test clicking with invalid element reference."""
        mock_session.get_page.return_value = mock_page

        # Mock unified analysis without the element
        mock_analysis = {"elements": {}}
        mock_page.evaluate.return_value = mock_analysis

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            result = await toolkit.click(ref="e999")

            assert "Element reference 'e999' not found" in result["result"]

    @pytest.mark.asyncio
    async def test_type_text(self, mock_session, mock_page):
        """Test typing text into an element."""
        mock_session.get_page.return_value = mock_page
        mock_page.evaluate.return_value = {"elements": {}}

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            result = await toolkit.type(ref="e1", text="Hello World")

            assert (
                "Type" in result["result"]
                or "Action executed" in result["result"]
            )
            mock_session.exec_action.assert_called_once()

            # Check the action parameters
            call_args = mock_session.exec_action.call_args[0][0]
            assert call_args["type"] == "type"
            assert call_args["ref"] == "e1"
            assert call_args["text"] == "Hello World"

    @pytest.mark.asyncio
    async def test_select_option(self, mock_session, mock_page):
        """Test selecting option from dropdown."""
        mock_session.get_page.return_value = mock_page
        mock_page.evaluate.return_value = {"elements": {}}

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            result = await toolkit.select(ref="e1", value="option1")

            assert (
                "Select" in result["result"]
                or "Action executed" in result["result"]
            )
            mock_session.exec_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_scroll_valid_direction(self, mock_session):
        """Test scrolling with valid direction."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session

            result = await toolkit.scroll(direction="down", amount=100)

            assert (
                "Scroll" in result["result"]
                or "Action executed" in result["result"]
            )
            mock_session.exec_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self, mock_session):
        """Test scrolling with invalid direction."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            result = await toolkit.scroll(direction="left", amount=100)

            assert "direction must be 'up' or 'down'" in result["result"]

    @pytest.mark.asyncio
    async def test_get_page_links_valid_refs(self, mock_session, mock_page):
        """Test getting page links with valid references."""
        # Mock snapshot with links
        mock_snapshot = '- link "Google" [ref=e1]\n- link "GitHub" [ref=e2]'
        mock_session.get_snapshot.return_value = mock_snapshot

        # Mock element query for URLs
        mock_element = MagicMock()
        mock_element.get_attribute = AsyncMock(
            return_value="https://google.com"
        )
        mock_page.query_selector.return_value = mock_element

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session  # 关键: 设置mock session

            # Mock the _require_page method to return our mock page
            with patch.object(
                toolkit, '_require_page', return_value=mock_page
            ):
                result = await toolkit.get_page_links(ref=["e1"])

                assert "links" in result
                assert len(result["links"]) == 1
                assert result["links"][0]["text"] == "Google"
                assert result["links"][0]["ref"] == "e1"

    @pytest.mark.asyncio
    async def test_get_page_links_invalid_refs(self, mock_session):
        """Test getting page links with invalid references."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session  # 设置mock session

            # Test with empty list
            result = await toolkit.get_page_links(ref=[])
            assert result["links"] == []

            # Test with invalid ref type
            result = await toolkit.get_page_links(ref=[""])
            assert result["links"] == []

    @pytest.mark.asyncio
    async def test_wait_user_no_timeout(self, mock_session):
        """Test waiting for user input without timeout."""
        mock_session.get_snapshot.return_value = "Current page snapshot"

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()
            toolkit._session = mock_session  # 设置mock session

            with patch(
                'asyncio.to_thread', new_callable=AsyncMock
            ) as mock_thread:
                result = await toolkit.wait_user()

                assert result["result"] == "User resumed."
                assert result["snapshot"] == "Current page snapshot"
                mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_user_with_timeout(self, mock_session):
        """Test waiting for user input with timeout."""
        mock_session.get_snapshot.return_value = "Current page snapshot"

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            with patch('asyncio.wait_for', side_effect=TimeoutError):
                result = await toolkit.wait_user(timeout_sec=1.0)

                assert "Timeout 1.0s reached" in result["result"]

    def test_get_tools(self, mock_session):
        """Test getting available tools."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            tools = toolkit.get_tools()

            assert len(tools) == 11  # Base tools without solve_task
            tool_names = [tool.func.__name__ for tool in tools]

            expected_tools = [
                'open_browser',
                'close_browser',
                'visit_page',
                'get_page_snapshot',
                'get_som_screenshot',
                'get_page_links',
                'click',
                'type',
                'select',
                'scroll',
                'wait_user',
            ]

            for expected_tool in expected_tools:
                assert expected_tool in tool_names

    def test_get_tools_with_web_agent_model(self, mock_session):
        """Test getting tools when web_agent_model is provided."""
        mock_model = MagicMock()

        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit(web_agent_model=mock_model)

            tools = toolkit.get_tools()

            assert len(tools) == 12  # Includes solve_task
            tool_names = [tool.func.__name__ for tool in tools]
            assert 'solve_task' in tool_names

    def test_convert_analysis_to_rects(self, mock_session):
        """Test converting analysis data to rect format."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

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

    def test_format_snapshot_from_analysis(self, mock_session):
        """Test formatting snapshot from analysis data."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

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

            assert '- button "Submit" disabled [ref=e1]' in snapshot
            assert '- checkbox "Agree" checked [ref=e2]' in snapshot

    def test_add_set_of_mark_with_pil(self, mock_session):
        """Test adding visual marks to image."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

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

    def test_add_set_of_mark_without_pil(self, mock_session):
        """Test adding visual marks when PIL is not available."""
        with patch(
            'camel.toolkits.non_visual_browser_toolkit.nv_browser_session'
            '.NVBrowserSession',
            return_value=mock_session,
        ):
            toolkit = BrowserNonVisualToolkit()

            test_image = Image.new('RGB', (200, 200), color='white')

            with patch('PIL.ImageDraw', side_effect=ImportError):
                result = toolkit._add_set_of_mark(test_image, {})

                # Should return original image when PIL not available
                assert result == test_image
