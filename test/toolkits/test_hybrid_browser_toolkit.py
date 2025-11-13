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

import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits.hybrid_browser_toolkit import HybridBrowserToolkit
from camel.toolkits.output_processors import SnapshotCleaningProcessor

TEST_URL = "https://example.com"
TEST_FILE_URL = "file:///test.html"


def create_mock_ws_wrapper():
    """Create mock WebSocket wrapper for testing."""
    mock_ws_wrapper = AsyncMock()
    mock_ws_wrapper.start = AsyncMock()
    mock_ws_wrapper.stop = AsyncMock()
    mock_ws_wrapper.open_browser = AsyncMock(
        return_value={
            "result": "Browser opened successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.visit_page = AsyncMock(
        return_value={
            "result": "Visited test URL in new tab",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.back = AsyncMock(
        return_value={
            "result": "Navigated back",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.forward = AsyncMock(
        return_value={
            "result": "Navigated forward",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.click = AsyncMock(
        return_value={
            "result": "Element clicked successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.type = AsyncMock(
        return_value={
            "result": "Text typed successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.select = AsyncMock(
        return_value={
            "result": "Option selected successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.scroll = AsyncMock(
        return_value={
            "result": "Scrolled successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.enter = AsyncMock(
        return_value={
            "result": "Enter key pressed",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.mouse_control = AsyncMock(
        return_value={
            "result": "Action mouse_control executed successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.mouse_drag = AsyncMock(
        return_value={
            "result": "Action mouse_drag executed successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.press_key = AsyncMock(
        return_value={
            "result": "Action press_key executed successfully",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.switch_tab = AsyncMock(
        return_value={
            "result": "Switched to tab",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.close_tab = AsyncMock(
        return_value={
            "result": "Tab closed",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )
    mock_ws_wrapper.get_page_snapshot = AsyncMock(
        return_value="- Page snapshot\n```yaml\n<test content>\n```"
    )
    mock_ws_wrapper.get_som_screenshot = AsyncMock(
        return_value="Visual webpage screenshot captured"
    )
    mock_ws_wrapper.get_tab_info = AsyncMock(
        return_value=[
            {
                "id": "tab-001",
                "title": "Test Page",
                "url": "https://example.com",
                "is_current": True,
            }
        ]
    )
    mock_ws_wrapper.console_view = AsyncMock(
        return_value=[{"type": "log", "text": "Example Log"}]
    )
    mock_ws_wrapper.console_exec = AsyncMock(
        return_value={
            "result": "Console execution result: 100",
            "snapshot": "- Page snapshot\n```yaml\n<test content>\n```",
        }
    )

    return mock_ws_wrapper


# Create global mock WebSocket wrapper
mock_ws_wrapper = create_mock_ws_wrapper()


@pytest.fixture(scope="function")
def mock_ws_wrapper_setup():
    """Set up WebSocket wrapper mocks for individual tests."""
    return create_mock_ws_wrapper()


@pytest.fixture(autouse=True)
def mock_browser_dependencies():
    """Mock all browser-related dependencies for each test."""
    with (
        patch('os.makedirs'),
        patch('os.path.exists', return_value=True),
        patch(
            'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
            return_value=mock_ws_wrapper,
        ),
    ):
        yield


@pytest.fixture(scope="function")
def browser_toolkit_fixture():
    """Create a HybridBrowserToolkit instance for testing."""
    with (
        patch(
            'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
            return_value=mock_ws_wrapper,
        ),
    ):
        toolkit = HybridBrowserToolkit(headless=True)
        toolkit._ws_wrapper = (
            mock_ws_wrapper  # Ensure the mock wrapper is used
        )
        yield toolkit

        # Cleanup
        if os.path.exists("test_cache"):
            shutil.rmtree("test_cache", ignore_errors=True)


@pytest.fixture(scope="function")
def mock_ws_wrapper_fixture():
    """Create a mock WebSocket wrapper."""
    return create_mock_ws_wrapper()


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
    with (
        patch(
            'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
            return_value=mock_ws_wrapper,
        ),
    ):
        toolkit = HybridBrowserToolkit(headless=True)
        toolkit._ws_wrapper = (
            mock_ws_wrapper  # Ensure the mock wrapper is used
        )
        return toolkit


class TestHybridBrowserToolkit:
    """Test cases for HybridBrowserToolkit."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
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

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        test_cache_dir = "custom_cache"
        test_user_data_dir = "custom_user_data"

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
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

    @pytest.mark.asyncio
    async def test_open_browser_no_start_url(self, browser_toolkit_fixture):
        """Test opening browser using the default start
        URL configured during initialization."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_open()

        assert "opened" in result["result"].lower()
        assert "snapshot" in result
        assert "tabs" in result
        assert "current_tab" in result
        assert "total_tabs" in result

    @pytest.mark.asyncio
    async def test_open_browser_with_custom_default_url(
        self, browser_toolkit_fixture
    ):
        """Test browser_open with a custom default start URL."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_open()

        # Just check that the method works and returns expected structure
        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert "current_tab" in result
        assert "total_tabs" in result

    @pytest.mark.asyncio
    async def test_close_browser(self, browser_toolkit_fixture):
        """Test closing browser."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_close()
        assert isinstance(result, str)
        assert "closed" in result.lower()

    @pytest.mark.asyncio
    async def test_visit_page_valid_url(self, browser_toolkit_fixture):
        """Test visiting a valid URL."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_visit_page(TEST_URL)

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert "current_tab" in result
        assert "total_tabs" in result
        assert (
            "test url" in result['result'].lower()
            or "visited" in result['result'].lower()
        )

    @pytest.mark.asyncio
    async def test_visit_page_invalid_url(self, browser_toolkit_fixture):
        """Test visiting an invalid URL (empty string)."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_visit_page("")
        assert "result" in result
        assert "snapshot" in result
        # The WebSocket wrapper should handle validation
        assert isinstance(result['result'], str)

    @pytest.mark.asyncio
    async def test_get_page_snapshot(self, browser_toolkit_fixture):
        """Test getting page snapshot."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_get_page_snapshot()
        assert isinstance(result, str)
        assert (
            "page snapshot" in result.lower()
            or "test content" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_get_som_screenshot_success(self, browser_toolkit_fixture):
        """Test successful Set of Marks screenshot generation."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_get_som_screenshot()

        # The result should be a string indicating success
        assert isinstance(result, str)
        assert "screenshot" in result.lower() or "captured" in result.lower()

    @pytest.mark.asyncio
    async def test_get_som_screenshot_pil_not_available(
        self, browser_toolkit_fixture
    ):
        """Test Set of Marks screenshot when PIL is not available."""
        toolkit = browser_toolkit_fixture

        with patch('PIL.ImageDraw', side_effect=ImportError):
            result = await toolkit.browser_get_som_screenshot()

            # The result should still be a string even if PIL is not available
            assert isinstance(result, str)
            assert (
                "screenshot" in result.lower() or "captured" in result.lower()
            )

    @pytest.mark.asyncio
    async def test_click_valid_ref(self, browser_toolkit_fixture):
        """Test clicking with valid reference."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_click(ref="e1")

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert "current_tab" in result
        assert "total_tabs" in result
        assert (
            "clicked" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_click_invalid_ref(self, browser_toolkit_fixture):
        """Test clicking with invalid reference."""
        toolkit = browser_toolkit_fixture
        # With WebSocket wrapper, validation should be handled gracefully
        result = await toolkit.browser_click(ref="")
        assert "result" in result
        assert isinstance(result["result"], str)

    @pytest.mark.asyncio
    async def test_type_text(self, browser_toolkit_fixture):
        """Test typing text in element."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_type(
            ref="input_element", text="Hello World"
        )
        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert (
            "typed" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_select_option(self, browser_toolkit_fixture):
        """Test selecting option in dropdown."""
        toolkit = browser_toolkit_fixture

        result = await toolkit.browser_select(
            ref="select_element", value="option1"
        )

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert (
            "selected" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_scroll_valid_direction(self, browser_toolkit_fixture):
        """Test scrolling with valid direction."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_scroll(direction="down", amount=100)

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert (
            "scrolled" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self, browser_toolkit_fixture):
        """Test scrolling with invalid direction."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_scroll(
            direction="invalid_direction", amount=100
        )
        # WebSocket wrapper should handle validation gracefully
        assert "result" in result
        assert isinstance(result["result"], str)

    @pytest.mark.asyncio
    async def test_wait_user_no_timeout(self, browser_toolkit_fixture):
        """Test waiting for user input without timeout."""
        toolkit = browser_toolkit_fixture

        # Mock user input
        with patch('builtins.input', return_value='continue'):
            result = await toolkit.browser_wait_user()

            assert "result" in result
            assert "snapshot" in result
            assert (
                "resumed" in result["result"].lower()
                or "user" in result["result"].lower()
            )

    @pytest.mark.asyncio
    async def test_wait_user_with_timeout(self, browser_toolkit_fixture):
        """Test waiting for user input with timeout."""
        toolkit = browser_toolkit_fixture

        # Mock asyncio.wait_for to simulate timeout
        import asyncio

        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            result = await toolkit.browser_wait_user(timeout_sec=1.0)

            assert "result" in result
            assert "snapshot" in result
            assert (
                "timeout" in result["result"].lower()
                or "auto-resumed" in result["result"].lower()
            )

    @pytest.mark.asyncio
    async def test_mouse_control_valid(self, browser_toolkit_fixture):
        """Test mouse_control with valid control action"""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_mouse_control(
            control="click", x=500, y=500
        )

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert (
            "mouse_control" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_mouse_control_invalid(self, browser_toolkit_fixture):
        """Test mouse_control with invalid control action"""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_mouse_control(
            control="invalid", x=500, y=500
        )
        # WebSocket wrapper should handle validation gracefully
        assert "result" in result
        assert isinstance(result["result"], str)

    @pytest.mark.asyncio
    async def test_mouse_drag(self, browser_toolkit_fixture):
        """Test mouse_drag with element references"""
        toolkit = browser_toolkit_fixture
        # Mock elements with ref IDs
        result = await toolkit.browser_mouse_drag(
            from_ref="ref1", to_ref="ref2"
        )

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        # Mock returns success message
        assert (
            "mouse_drag" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_press_key(self, browser_toolkit_fixture):
        """Test press_key with key combination"""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_press_key(keys=["Meta", "A"])

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert (
            "press_key" in result["result"].lower()
            or "successfully" in result["result"].lower()
        )

    @pytest.mark.asyncio
    async def test_console_view(self, browser_toolkit_fixture):
        """Test console_view to return format"""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_console_view()

        assert "console_messages" in result
        assert isinstance(result["console_messages"], list)
        assert all(
            isinstance(item, dict) for item in result["console_messages"]
        )

    @pytest.mark.asyncio
    async def test_console_exec(self, browser_toolkit_fixture):
        """Test console_exec to return result"""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_console_exec(code="Math.sqrt(64);")

        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert "result" in result["result"].lower()

    def test_get_tools(self, sync_browser_toolkit):
        """Test getting available tools with default configuration."""
        toolkit = sync_browser_toolkit

        tools = toolkit.get_tools()

        # Default tools should be 5 tools (updated default configuration)
        assert len(tools) == 8

        tool_names = [tool.func.__name__ for tool in tools]

        expected_default_tools = [
            "browser_open",
            "browser_close",
            "browser_visit_page",
            "browser_back",
            "browser_forward",
            "browser_click",
            "browser_type",
            "browser_switch_tab",
        ]

        for expected_tool in expected_default_tools:
            assert expected_tool in tool_names

    def test_get_tools_custom_selection(self):
        """Test getting tools with custom tool selection."""
        custom_tools = [
            "browser_open",
            "browser_close",
            "browser_visit_page",
            "browser_back",
            "browser_forward",
            "browser_click",
            "browser_type",
            "browser_switch_tab",
        ]

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
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

    @pytest.mark.asyncio
    async def test_simple_async_creation(self, browser_toolkit_fixture):
        """Simple test to verify async toolkit creation works with mocks."""
        toolkit = browser_toolkit_fixture
        result = await toolkit.browser_open()
        assert "result" in result
        assert "snapshot" in result
        assert "tabs" in result
        assert "current_tab" in result
        assert "total_tabs" in result


def add_snapshot_cleaning_to_toolkit(toolkit, enable_cleaning=True):
    """Add snapshot cleaning to an existing HybridBrowserToolkit instance.

    Args:
        toolkit: An existing HybridBrowserToolkit instance
        enable_cleaning: Whether to enable snapshot cleaning

    Returns:
        The same toolkit instance with snapshot cleaning enabled
    """
    if enable_cleaning:
        processor = SnapshotCleaningProcessor(enable_cleaning=True)
        toolkit.register_output_processor(processor)
    return toolkit


class TestHybridBrowserToolkitWithCleaning:
    """Test cases for HybridBrowserToolkit with snapshot cleaning."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the WebSocket wrapper to avoid actual browser operations
        self.mock_ws_wrapper = AsyncMock()
        self.mock_ws_wrapper.start = AsyncMock()
        self.mock_ws_wrapper.get_page_snapshot = AsyncMock()
        self.mock_ws_wrapper.click = AsyncMock()
        self.mock_ws_wrapper.visit_page = AsyncMock()
        self.mock_ws_wrapper.get_tab_info = AsyncMock()

    def test_toolkit_initialization_with_cleaning(self):
        """Test that toolkit initializes with cleaning enabled."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            # Create standard toolkit and add cleaning
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit = add_snapshot_cleaning_to_toolkit(
                toolkit, enable_cleaning=True
            )

            # Should have registered the snapshot cleaning processor
            processors = toolkit.output_manager.processors
            assert len(processors) > 0

            # Check that it's specifically a SnapshotCleaningProcessor
            has_snapshot_processor = any(
                isinstance(p, SnapshotCleaningProcessor) for p in processors
            )
            assert has_snapshot_processor

    def test_toolkit_initialization_without_cleaning(self):
        """Test that toolkit can be initialized without cleaning."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            # Create standard toolkit without adding cleaning
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)

            # Should have no processors
            processors = toolkit.output_manager.processors
            assert len(processors) == 0

    @pytest.mark.asyncio
    async def test_page_snapshot_with_cleaning(self):
        """Test page snapshot with cleaning in a realistic scenario."""
        with patch(
            'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts.WebSocketBrowserWrapper'
        ) as mock_ws_class:
            # Setup mock
            mock_ws_instance = AsyncMock()
            mock_ws_class.return_value = mock_ws_instance

            # Mock realistic snapshot data with ref markers
            mock_snapshot = """
            - button "Login" [ref=1] [class=btn primary]
            - textbox "Username" [ref=2] [placeholder=Enter username]
            - textbox "Password" [ref=3] [type=password]
            - link "Forgot Password?" [ref=4] [href=/forgot]
            - generic "Footer" [ref=5] [class=footer-content]
              - link "Privacy Policy" [ref=6] [href=/privacy]
              - link "Terms of Service" [ref=7] [href=/terms]
            """

            mock_ws_instance.get_page_snapshot.return_value = (
                mock_snapshot.strip()
            )
            mock_ws_instance.start = AsyncMock()

            # Create toolkit with cleaning enabled
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit = add_snapshot_cleaning_to_toolkit(
                toolkit, enable_cleaning=True
            )

            # Mock the _get_ws_wrapper method to return our mock
            toolkit._get_ws_wrapper = AsyncMock(return_value=mock_ws_instance)

            # Get the raw snapshot
            raw_snapshot = await toolkit.browser_get_page_snapshot()

            # Process it through the cleaning system
            cleaned_context = toolkit.process_tool_output(
                tool_name="browser_get_page_snapshot",
                tool_call_id="test_snapshot_001",
                raw_result=raw_snapshot,
                agent_id="test_agent",
            )

            cleaned_snapshot = cleaned_context.raw_result

            # Verify cleaning worked
            assert '[ref=' not in cleaned_snapshot
            assert '[class=' not in cleaned_snapshot
            assert '[href=' not in cleaned_snapshot
            assert '[placeholder=' not in cleaned_snapshot
            assert '[type=' not in cleaned_snapshot

            # Verify content is preserved
            assert '"Login"' in cleaned_snapshot
            assert '"Username"' in cleaned_snapshot
            assert '"Password"' in cleaned_snapshot
            assert '"Forgot Password?"' in cleaned_snapshot
            assert '"Privacy Policy"' in cleaned_snapshot

    @pytest.mark.asyncio
    async def test_browser_click_with_cleaning(self):
        """Test browser click with snapshot cleaning."""
        with patch(
            'camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts.WebSocketBrowserWrapper'
        ) as mock_ws_class:
            # Setup mock
            mock_ws_instance = AsyncMock()
            mock_ws_class.return_value = mock_ws_instance

            # Mock click response with snapshot
            mock_click_response = {
                "result": "Clicked successfully",
                "snapshot": """
                - button "Submit" [ref=10] [disabled]
                - generic "Success message: Form submitted!" [ref=11] 
                [class=alert success]
                - link "Continue" [ref=12] [href=/dashboard]
                """,
            }

            mock_tab_info = [
                {
                    "id": "tab1",
                    "title": "Test Page",
                    "url": "https://example.com",
                    "is_current": True,
                }
            ]

            mock_ws_instance.click.return_value = mock_click_response
            mock_ws_instance.get_tab_info.return_value = mock_tab_info
            mock_ws_instance.start = AsyncMock()

            # Create toolkit
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit = add_snapshot_cleaning_to_toolkit(
                toolkit, enable_cleaning=True
            )
            toolkit._get_ws_wrapper = AsyncMock(return_value=mock_ws_instance)

            # Perform click
            raw_result = await toolkit.browser_click(ref="1")

            # Process through cleaning
            cleaned_context = toolkit.process_tool_output(
                tool_name="browser_click",
                tool_call_id="test_click_001",
                raw_result=raw_result,
                agent_id="test_agent",
            )

            cleaned_result = cleaned_context.raw_result

            # Check that snapshot field in the result was cleaned
            if (
                isinstance(cleaned_result, dict)
                and 'snapshot' in cleaned_result
            ):
                cleaned_snapshot = cleaned_result['snapshot']
                assert '[ref=' not in cleaned_snapshot
                assert '[disabled]' not in cleaned_snapshot
                assert '[class=' not in cleaned_snapshot
                assert '[href=' not in cleaned_snapshot

                # Content should be preserved
                assert '"Submit"' in cleaned_snapshot
                assert '"Success message: Form submitted!"' in cleaned_snapshot
                assert '"Continue"' in cleaned_snapshot

    def test_tool_registration(self):
        """Test that the toolkit's tools are properly registered."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit = add_snapshot_cleaning_to_toolkit(
                toolkit, enable_cleaning=True
            )

            tools = toolkit.get_tools()

            # Should have default tools
            assert len(tools) > 0

            # Check for essential browser tools
            tool_names = [tool.get_function_name() for tool in tools]
            essential_tools = [
                'browser_open',
                'browser_click',
                'browser_type',
                'browser_visit_page',
            ]

            for essential_tool in essential_tools:
                assert essential_tool in tool_names

    @pytest.mark.asyncio
    async def test_performance_with_large_snapshot(self):
        """Test performance with large snapshot data."""
        import time

        # Create a large snapshot for testing
        large_snapshot_parts = []
        for i in range(500):  # 500 elements
            large_snapshot_parts.append(
                f'- button "Button {i}" [ref={i}] [class=btn-{i}] '
                f'[data-id={i}]'
            )

        large_snapshot = '\n'.join(large_snapshot_parts)

        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            toolkit = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit = add_snapshot_cleaning_to_toolkit(
                toolkit, enable_cleaning=True
            )

            # Time the processing
            start_time = time.time()

            cleaned_context = toolkit.process_tool_output(
                tool_name="browser_get_page_snapshot",
                tool_call_id="performance_test",
                raw_result=large_snapshot,
                agent_id="test_agent",
            )

            processing_time = time.time() - start_time

            # Should complete in reasonable time (< 1 second for 500 elements)
            assert processing_time < 1.0

            # Check that cleaning worked
            cleaned_result = cleaned_context.raw_result
            assert '[ref=' not in cleaned_result
            assert '[class=' not in cleaned_result
            assert '[data-id=' not in cleaned_result

            # Content should still be there
            assert '"Button 0"' in cleaned_result
            assert '"Button 499"' in cleaned_result

            # Size should be significantly reduced
            original_size = len(large_snapshot)
            cleaned_size = len(cleaned_result)
            reduction_ratio = (original_size - cleaned_size) / original_size

            # Should have at least 30% size reduction
            assert reduction_ratio > 0.3

    def test_backward_compatibility(self):
        """Test that existing HybridBrowserToolkit works unchanged."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            # Standard HybridBrowserToolkit should work without any issues
            standard_toolkit = HybridBrowserToolkit(
                mode="typescript", headless=True
            )

            # Should have the output manager (from BaseToolkit)
            assert hasattr(standard_toolkit, 'output_manager')

            # But no processors registered by default
            assert len(standard_toolkit.output_manager.processors) == 0

            # Should be able to manually add processor
            processor = SnapshotCleaningProcessor(enable_cleaning=True)
            standard_toolkit.register_output_processor(processor)

            # Now should have one processor
            assert len(standard_toolkit.output_manager.processors) == 1


class TestIntegrationExample:
    """Integration test showing how to use in real scenarios."""

    def test_usage_example_documentation(self):
        """Document the proper usage pattern."""
        with (
            patch(
                'camel.toolkits.hybrid_browser_toolkit.ws_wrapper.WebSocketBrowserWrapper',
                return_value=mock_ws_wrapper,
            ),
        ):
            # Example 1: Add cleaning to existing toolkit instance
            toolkit1 = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit1 = add_snapshot_cleaning_to_toolkit(
                toolkit1, enable_cleaning=True
            )

            assert len(toolkit1.output_manager.processors) == 1

            # Example 2: Create toolkit and add cleaning in one step
            toolkit2 = add_snapshot_cleaning_to_toolkit(
                HybridBrowserToolkit(mode="typescript", headless=True),
                enable_cleaning=True,
            )

            assert len(toolkit2.output_manager.processors) == 1

            # Example 3: Manual processor registration
            toolkit3 = HybridBrowserToolkit(mode="typescript", headless=True)
            toolkit3.register_output_processor(
                SnapshotCleaningProcessor(enable_cleaning=True)
            )

            assert len(toolkit3.output_manager.processors) == 1
