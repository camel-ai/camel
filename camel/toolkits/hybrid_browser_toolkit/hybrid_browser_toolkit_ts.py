# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# =========

import asyncio
import contextlib
import time
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    cast,
)

from typing_extensions import TypedDict

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.output_processors import SnapshotCleaningProcessor
from camel.utils.tool_result import ToolResult

from .config_loader import ConfigLoader
from .ws_wrapper import WebSocketBrowserWrapper, high_level_action


def _add_rulers_to_image(
    image_bytes: bytes, tick_interval: int = 100
) -> bytes:
    r"""Add rulers with tick marks to an image (like a real measuring ruler).

    Adds horizontal ruler at the top and vertical ruler on the left side,
    with multi-level tick marks like a real ruler:
    - Every 100 pixels: longest tick + number label
    - Every 50 pixels: long tick (no label)
    - Every 10 pixels: medium tick
    - Every 5 pixels: short tick

    Args:
        image_bytes: The original image as bytes.
        tick_interval: Major interval for number labels (default: 100).

    Returns:
        The modified image with rulers as bytes.
    """
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    # Load the original image
    original = Image.open(BytesIO(image_bytes))
    orig_width, orig_height = original.size

    # Ruler dimensions
    ruler_thickness = 30  # Increased for better visibility
    font_size = 9

    # Create new image with space for rulers
    new_width = orig_width + ruler_thickness
    new_height = orig_height + ruler_thickness
    new_image = Image.new('RGB', (new_width, new_height), 'white')

    # Paste original image offset by ruler thickness
    new_image.paste(original, (ruler_thickness, ruler_thickness))

    draw = ImageDraw.Draw(new_image)

    # Try to load a font, fall back to default if not available
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", font_size
        )
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()

    # Colors
    ruler_bg_color = (245, 245, 245)  # Light gray background
    tick_color = (80, 80, 80)  # Dark gray for ticks
    minor_tick_color = (160, 160, 160)  # Lighter gray for minor ticks
    text_color = (40, 40, 40)  # Darker gray for text

    # Draw horizontal ruler background (top)
    draw.rectangle(
        [ruler_thickness, 0, new_width, ruler_thickness], fill=ruler_bg_color
    )

    # Draw vertical ruler background (left)
    draw.rectangle(
        [0, ruler_thickness, ruler_thickness, new_height], fill=ruler_bg_color
    )

    # Draw corner square
    draw.rectangle(
        [0, 0, ruler_thickness, ruler_thickness], fill=ruler_bg_color
    )

    # Tick heights for different intervals (from ruler bottom)
    tick_100 = 18  # Every 100px - longest, with number
    tick_50 = 14  # Every 50px - long
    tick_10 = 10  # Every 10px - medium
    tick_5 = 6  # Every 5px - short

    # Draw horizontal tick marks and labels (top ruler)
    for x in range(0, orig_width + 1):
        tick_x = x + ruler_thickness

        if x % tick_interval == 0:
            # Major tick (every 100px) - longest with label
            draw.line(
                [
                    (tick_x, ruler_thickness - tick_100),
                    (tick_x, ruler_thickness),
                ],
                fill=tick_color,
                width=1,
            )
            # Draw number label
            label = str(x)
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                (tick_x - text_width // 2, 1),
                label,
                fill=text_color,
                font=font,
            )
        elif x % 50 == 0:
            # Half tick (every 50px) - long, no label
            draw.line(
                [
                    (tick_x, ruler_thickness - tick_50),
                    (tick_x, ruler_thickness),
                ],
                fill=tick_color,
                width=1,
            )
        elif x % 10 == 0:
            # Medium tick (every 10px)
            draw.line(
                [
                    (tick_x, ruler_thickness - tick_10),
                    (tick_x, ruler_thickness),
                ],
                fill=tick_color,
                width=1,
            )
        elif x % 5 == 0:
            # Small tick (every 5px)
            draw.line(
                [
                    (tick_x, ruler_thickness - tick_5),
                    (tick_x, ruler_thickness),
                ],
                fill=minor_tick_color,
                width=1,
            )

    # Draw vertical tick marks and labels (left ruler)
    for y in range(0, orig_height + 1):
        tick_y = y + ruler_thickness

        if y % tick_interval == 0:
            # Major tick (every 100px) - longest with label
            draw.line(
                [
                    (ruler_thickness - tick_100, tick_y),
                    (ruler_thickness, tick_y),
                ],
                fill=tick_color,
                width=1,
            )
            # Draw number label
            label = str(y)
            bbox = draw.textbbox((0, 0), label, font=font)
            text_height = bbox[3] - bbox[1]
            draw.text(
                (2, tick_y - text_height // 2),
                label,
                fill=text_color,
                font=font,
            )
        elif y % 50 == 0:
            # Half tick (every 50px) - long, no label
            draw.line(
                [
                    (ruler_thickness - tick_50, tick_y),
                    (ruler_thickness, tick_y),
                ],
                fill=tick_color,
                width=1,
            )
        elif y % 10 == 0:
            # Medium tick (every 10px)
            draw.line(
                [
                    (ruler_thickness - tick_10, tick_y),
                    (ruler_thickness, tick_y),
                ],
                fill=tick_color,
                width=1,
            )
        elif y % 5 == 0:
            # Small tick (every 5px)
            draw.line(
                [
                    (ruler_thickness - tick_5, tick_y),
                    (ruler_thickness, tick_y),
                ],
                fill=minor_tick_color,
                width=1,
            )

    # Draw border lines for rulers
    draw.line(
        [(ruler_thickness, ruler_thickness), (new_width, ruler_thickness)],
        fill=tick_color,
        width=1,
    )
    draw.line(
        [(ruler_thickness, ruler_thickness), (ruler_thickness, new_height)],
        fill=tick_color,
        width=1,
    )

    # Save to bytes
    output = BytesIO()
    new_image.save(output, format='PNG')
    return output.getvalue()


logger = get_logger(__name__)


class SheetCell(TypedDict):
    """Type definition for a sheet cell input."""

    row: int
    col: int
    text: str


class HybridBrowserToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""A hybrid browser toolkit that combines non-visual, DOM-based browser
    automation with visual, screenshot-based capabilities.

    This toolkit now uses TypeScript implementation with Playwright's
    _snapshotForAI functionality for enhanced AI integration.
    """

    DEFAULT_TOOLS: ClassVar[List[str]] = [
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_back",
        "browser_forward",
        "browser_click",
        "browser_type",
        "browser_switch_tab",
    ]

    ALL_TOOLS: ClassVar[List[str]] = [
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_back",
        "browser_forward",
        "browser_get_page_snapshot",
        "browser_get_som_screenshot",
        "browser_get_screenshot",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_scroll",
        "browser_enter",
        "browser_mouse_control",
        "browser_mouse_drag",
        "browser_press_key",
        "browser_upload_file",
        "browser_download_file",
        "browser_wait_user",
        "browser_switch_tab",
        "browser_close_tab",
        "browser_get_tab_info",
        "browser_console_view",
        "browser_console_exec",
        "browser_sheet_input",
        "browser_sheet_read",
    ]

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        cache_dir: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
        browser_log_to_file: bool = False,
        log_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        default_start_url: Optional[str] = None,
        default_timeout: Optional[int] = None,
        short_timeout: Optional[int] = None,
        navigation_timeout: Optional[int] = None,
        network_idle_timeout: Optional[int] = None,
        screenshot_timeout: Optional[int] = None,
        page_stability_timeout: Optional[int] = None,
        dom_content_loaded_timeout: Optional[int] = None,
        download_timeout: Optional[int] = None,
        viewport_limit: bool = False,
        connect_over_cdp: bool = False,
        cdp_url: Optional[str] = None,
        cdp_keep_current_page: bool = False,
        full_visual_mode: bool = False,
        clean_snapshots: bool = False,
        download_dir: Optional[str] = None,
    ) -> None:
        r"""Initialize the HybridBrowserToolkit.

        Args:
            headless (bool): Whether to run browser in headless mode.
                Defaults to True.
            user_data_dir (Optional[str]): Directory for user data
                persistence. Defaults to None.
            stealth (bool): Whether to enable stealth mode. Defaults to
            False.
            cache_dir (str): Directory for caching. Defaults to "tmp/".
            enabled_tools (Optional[List[str]]): List of enabled tools.
                Defaults to None.
            browser_log_to_file (bool): Whether to log browser actions to
                file. Defaults to False.
            log_dir (Optional[str]): Custom directory path for log files.
                If None, defaults to "browser_log". Defaults to None.
            session_id (Optional[str]): Session identifier. Defaults to None.
            default_start_url (str): Default URL to start with. Defaults
                to "https://google.com/".
            default_timeout (Optional[int]): Default timeout in
                milliseconds. Defaults to None.
            short_timeout (Optional[int]): Short timeout in milliseconds.
                Defaults to None.
            navigation_timeout (Optional[int]): Navigation timeout in
                milliseconds. Defaults to None.
            network_idle_timeout (Optional[int]): Network idle timeout in
                milliseconds. Defaults to None.
            screenshot_timeout (Optional[int]): Screenshot timeout in
                milliseconds. Defaults to None.
            page_stability_timeout (Optional[int]): Page stability timeout
                in milliseconds. Defaults to None.
            dom_content_loaded_timeout (Optional[int]): DOM content loaded
                timeout in milliseconds. Defaults to None.
            download_timeout (Optional[int]): Download timeout in
                milliseconds. Defaults to None.
            viewport_limit (bool): Whether to filter page snapshot
            elements to only those visible in the current viewport.
                When True, only elements within the current viewport
                bounds will be included in snapshots.
                When False (default), all elements on the page are
                included. Defaults to False.
            connect_over_cdp (bool): Whether to connect to an existing
                browser via Chrome DevTools Protocol. Defaults to False.
            cdp_url (Optional[str]): WebSocket endpoint URL for CDP
                connection (e.g., 'ws://localhost:9222/devtools/browser/...').
                Required when connect_over_cdp is True. Defaults to None.
            cdp_keep_current_page (bool): When True and using CDP mode,
                won't create new pages but use the existing one. Defaults to
                False.
            full_visual_mode (bool): When True, browser actions like click,
                browser_open, visit_page, etc. will not return snapshots.
                Defaults to False.
            clean_snapshots (bool): When True, automatically cleans verbose
                DOM snapshots to reduce context usage while preserving
                essential information. Removes redundant markers and references
                from browser tool outputs. Defaults to False.
            download_dir (Optional[str]): Directory path where downloaded
                files will be saved when using browser_download_file tool.
                Defaults to None.
        """
        super().__init__()
        RegisteredAgentToolkit.__init__(self)

        self.config_loader = ConfigLoader.from_kwargs(
            headless=headless,
            user_data_dir=user_data_dir,
            stealth=stealth,
            default_start_url=default_start_url,
            default_timeout=default_timeout,
            short_timeout=short_timeout,
            navigation_timeout=navigation_timeout,
            network_idle_timeout=network_idle_timeout,
            screenshot_timeout=screenshot_timeout,
            page_stability_timeout=page_stability_timeout,
            dom_content_loaded_timeout=dom_content_loaded_timeout,
            download_timeout=download_timeout,
            viewport_limit=viewport_limit,
            cache_dir=cache_dir,
            browser_log_to_file=browser_log_to_file,
            log_dir=log_dir,
            session_id=session_id,
            enabled_tools=enabled_tools,
            connect_over_cdp=connect_over_cdp,
            cdp_url=cdp_url,
            cdp_keep_current_page=cdp_keep_current_page,
            full_visual_mode=full_visual_mode,
            download_dir=download_dir,
        )

        browser_config = self.config_loader.get_browser_config()
        toolkit_config = self.config_loader.get_toolkit_config()

        if (
            browser_config.cdp_keep_current_page
            and default_start_url is not None
        ):
            raise ValueError(
                "Cannot use default_start_url with "
                "cdp_keep_current_page=True. When cdp_keep_current_page "
                "is True, the browser will keep the current page and not "
                "navigate to any URL."
            )

        self._headless = browser_config.headless
        self._user_data_dir = browser_config.user_data_dir
        self._stealth = browser_config.stealth
        self._cache_dir = toolkit_config.cache_dir
        self._browser_log_to_file = toolkit_config.browser_log_to_file
        self._default_start_url = browser_config.default_start_url
        self._session_id = toolkit_config.session_id or "default"
        self._viewport_limit = browser_config.viewport_limit
        self._full_visual_mode = browser_config.full_visual_mode
        self._clean_snapshots = clean_snapshots

        self._default_timeout = browser_config.default_timeout
        self._short_timeout = browser_config.short_timeout
        self._navigation_timeout = browser_config.navigation_timeout
        self._network_idle_timeout = browser_config.network_idle_timeout
        self._screenshot_timeout = browser_config.screenshot_timeout
        self._page_stability_timeout = browser_config.page_stability_timeout
        self._dom_content_loaded_timeout = (
            browser_config.dom_content_loaded_timeout
        )

        if enabled_tools is None:
            self.enabled_tools = self.DEFAULT_TOOLS.copy()
        else:
            invalid_tools = [
                tool for tool in enabled_tools if tool not in self.ALL_TOOLS
            ]
            if invalid_tools:
                raise ValueError(
                    f"Invalid tools specified: {invalid_tools}. "
                    f"Available tools: {self.ALL_TOOLS}"
                )
            self.enabled_tools = enabled_tools.copy()

        logger.info(f"Enabled tools: {self.enabled_tools}")

        # Setup snapshot cleaning if enabled
        if self._clean_snapshots:
            snapshot_processor = SnapshotCleaningProcessor()
            self.register_output_processor(snapshot_processor)
            logger.info(
                "Snapshot cleaning enabled - DOM snapshots will "
                "be automatically cleaned"
            )

        self._ws_wrapper: Optional[WebSocketBrowserWrapper] = None
        self._ws_config = self.config_loader.to_ws_config()

    async def _ensure_ws_wrapper(self):
        """Ensure WebSocket wrapper is initialized."""
        if self._ws_wrapper is None:
            self._ws_wrapper = WebSocketBrowserWrapper(self._ws_config)
            await self._ws_wrapper.start()

    async def _get_ws_wrapper(self) -> WebSocketBrowserWrapper:
        """Get the WebSocket wrapper, initializing if needed."""
        await self._ensure_ws_wrapper()
        if self._ws_wrapper is None:
            raise RuntimeError("Failed to initialize WebSocket wrapper")
        return self._ws_wrapper

    def _clean_snapshot_if_enabled(
        self, snapshot: str, tool_name: str = "browser_ts"
    ) -> str:
        r"""Clean snapshot content if snapshot cleaning is enabled.

        Args:
            snapshot: The raw snapshot content to clean.
            tool_name: The name of the tool that generated the snapshot.

        Returns:
            The cleaned snapshot if cleaning is enabled, otherwise the
                original snapshot.
        """
        if not self._clean_snapshots or not snapshot:
            return snapshot

        try:
            # Process through the output manager
            processed_context = self.process_tool_output(
                tool_name=tool_name,
                tool_call_id="snapshot_clean",
                raw_result=snapshot,
                agent_id=getattr(self, '_session_id', 'default'),
            )

            return processed_context.raw_result
        except Exception as e:
            logger.warning(
                f"Failed to clean snapshot: {e}, returning original"
            )
            return snapshot

    def __del__(self):
        r"""Cleanup browser resources on garbage collection."""
        try:
            import sys

            if getattr(sys, "is_finalizing", lambda: False)():
                return

            import asyncio

            is_cdp = (
                self._ws_config.get('connectOverCdp', False)
                if hasattr(self, '_ws_config')
                else False
            )

            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed() and not loop.is_running():
                    try:
                        if is_cdp:
                            # CDP: disconnect only
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    self.disconnect_websocket(), timeout=2.0
                                )
                            )
                        else:
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    self.browser_close(), timeout=2.0
                                )
                            )
                    except asyncio.TimeoutError:
                        pass
            except (RuntimeError, ImportError):
                pass
        except Exception:
            pass

    @property
    def cache_dir(self) -> str:
        """Get the cache directory."""
        return self._cache_dir

    async def _build_action_response(
        self,
        result: Dict[str, Any],
        ws_wrapper: Any,
        include_note: bool = True,
    ) -> Dict[str, Any]:
        """Build a standardized action response with tab info.

        Args:
            result: The raw result from the WebSocket wrapper action.
            ws_wrapper: The WebSocket wrapper instance for getting tab info.
            include_note: Whether to include the note field in the response.

        Returns:
            A standardized response dictionary with:
                - All fields from result
                - tabs: Information about all open tabs
                - current_tab: Index of the active tab
                - total_tabs: Total number of open tabs
                - note: Loading status note (if include_note and present)
        """
        tab_info = await ws_wrapper.get_tab_info()

        response = {
            **result,
            "tabs": tab_info,
            "current_tab": next(
                (i for i, tab in enumerate(tab_info) if tab.get("is_current")),
                0,
            ),
            "total_tabs": len(tab_info),
        }

        # In full_visual_mode, clear the snapshot
        if self._full_visual_mode:
            response["snapshot"] = ""
        # Clean snapshot if cleaning is enabled
        elif self._clean_snapshots and "snapshot" in response:
            response["snapshot"] = self._clean_snapshot_if_enabled(
                response["snapshot"], "browser_action"
            )

        # Always include note field for consistency (empty if not present)
        if include_note:
            response["note"] = result.get("note", "")

        return response

    def _build_error_response(
        self,
        error_message: str,
        include_note: bool = True,
    ) -> Dict[str, Any]:
        """Build a standardized error response.

        Args:
            error_message: The error message to include.
            include_note: Whether to include the note field.

        Returns:
            A standardized error response dictionary.
        """
        response: Dict[str, Any] = {
            "result": error_message,
            "snapshot": "",
            "tabs": [],
            "current_tab": 0,
            "total_tabs": 0,
        }
        if include_note:
            response["note"] = ""
        return response

    async def browser_open(self) -> Dict[str, Any]:
        r"""Starts a new browser session. This must be the first browser
        action.

        This method initializes the browser and navigates to a default start
        page. To visit a specific URL, use `visit_page` after this.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of interactive
                elements.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.open_browser(self._default_start_url)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return self._build_error_response(f"Error opening browser: {e}")

    async def browser_close(self) -> str:
        r"""Closes the browser session, releasing all resources.

        This should be called at the end of a task for cleanup.

        Returns:
            str: A confirmation message.
        """
        try:
            if self._ws_wrapper:
                await self._ws_wrapper.stop()
                self._ws_wrapper = None
            return "Browser session closed."
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
            return f"Error closing browser: {e}"

    async def disconnect_websocket(self) -> str:
        r"""Disconnects the WebSocket connection without closing the browser.

        This is useful when using CDP mode where the browser should
        remain open.

        Returns:
            str: A confirmation message.
        """
        try:
            if self._ws_wrapper:
                is_cdp = self._ws_config.get('connectOverCdp', False)

                if is_cdp:
                    # CDP: disconnect only
                    await self._ws_wrapper.disconnect_only()
                else:
                    await self._ws_wrapper.stop()

                self._ws_wrapper = None
            return "WebSocket disconnected."
        except Exception as e:
            logger.error(f"Failed to disconnect WebSocket: {e}")
            return f"Error disconnecting WebSocket: {e}"

    async def browser_visit_page(self, url: str) -> Dict[str, Any]:
        r"""Opens a URL in a new browser tab and switches to it.

        Args:
            url (str): The web address to load. This should be a valid and
                existing URL.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the new page.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the new active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.visit_page(url)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to visit page: {e}")
            return self._build_error_response(f"Error visiting page: {e}")

    async def browser_back(self) -> Dict[str, Any]:
        r"""Goes back to the previous page in the browser history.

        This action simulates using the browser's "back" button in the
        currently active tab.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the previous page.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.back()
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to navigate back: {e}")
            return self._build_error_response(f"Error navigating back: {e}")

    async def browser_forward(self) -> Dict[str, Any]:
        r"""Goes forward to the next page in the browser history.

        This action simulates using the browser's "forward" button in the
        currently active tab.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the next page.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.forward()
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to navigate forward: {e}")
            return self._build_error_response(f"Error navigating forward: {e}")

    async def browser_get_page_snapshot(self) -> str:
        r"""Gets a textual snapshot of the page's interactive elements.

        The snapshot lists elements like buttons, links, and inputs,
        each with
        a unique `ref` ID. This ID is used by other tools (e.g., `click`,
        `type`) to interact with a specific element. This tool provides no
        visual information.

        If viewport_limit is enabled, only elements within the current
        viewport
        will be included in the snapshot.

        Returns:
            str: A formatted string representing the interactive elements and
                their `ref` IDs. For example:
                '- link "Sign In" [ref=1]'
                '- textbox "Username" [ref=2]'
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.get_page_snapshot(self._viewport_limit)
            # Clean snapshot if enabled
            return self._clean_snapshot_if_enabled(
                result, "browser_get_page_snapshot"
            )
        except Exception as e:
            logger.error(f"Failed to get page snapshot: {e}")
            return f"Error capturing snapshot: {e}"

    async def browser_get_som_screenshot(
        self,
        read_image: bool = True,
    ) -> "str | ToolResult":
        r"""Captures a screenshot with interactive elements highlighted.

        "SoM" stands for "Set of Marks". This tool takes a screenshot and
        draws
        boxes around clickable elements, overlaying a `ref` ID on each. Use
        this for a visual understanding of the page, especially when the
        textual snapshot is not enough.

        Args:
            read_image (bool, optional): If `True`, the screenshot image will
                be included in the agent's context for direct visual analysis.
                If `False`, only a text message (including the saved file
                path) will be returned.
                (default: :obj:`True`)

        Returns:
            str | ToolResult: If `read_image` is `True`, returns a ToolResult
                containing the text message and the screenshot image (which
                will be automatically added to agent's context). If `False`,
                returns a string with the file path only.
        """
        import base64
        import datetime
        import os
        import urllib.parse

        from camel.utils import sanitize_filename

        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.get_som_screenshot()

            result_text = result.text
            file_path = None

            if result.images:
                cache_dir = os.path.abspath(self._cache_dir)
                os.makedirs(cache_dir, exist_ok=True)

                try:
                    page_info = await ws_wrapper.get_tab_info()
                    current_tab = next(
                        (tab for tab in page_info if tab.get('is_current')),
                        None,
                    )
                    url = current_tab['url'] if current_tab else 'unknown'
                except Exception:
                    url = 'unknown'

                parsed_url = urllib.parse.urlparse(url)
                url_name = sanitize_filename(
                    str(parsed_url.path) or 'homepage', max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
                file_path = os.path.join(
                    cache_dir, f"{url_name}_{timestamp}_som.png"
                )

                for _, image_data in enumerate(result.images):
                    if image_data.startswith('data:image/png;base64,'):
                        base64_data = image_data.split(',', 1)[1]

                        image_bytes = base64.b64decode(base64_data)
                        with open(file_path, 'wb') as f:
                            f.write(image_bytes)

                        logger.info(f"Screenshot saved to: {file_path}")

                        result_text += f" (saved to: {file_path})"
                        break

            # Return ToolResult with image if read_image is True
            if read_image and result.images:
                logger.info(
                    f"Returning ToolResult with {len(result.images)} image(s) "
                    "for agent context"
                )
                return ToolResult(
                    text=result_text,
                    images=result.images,  # Base64 images from WebSocket
                )
            else:
                # Return plain text if read_image is False
                return result_text
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            return f"Error capturing screenshot: {e}"

    async def browser_get_screenshot(
        self,
        read_image: bool = True,
    ) -> "str | ToolResult":
        r"""Captures a plain screenshot of the current page without markers.

        This tool takes a screenshot without any visual annotations. Use this
        in full_visual_mode for visual analysis where element ref IDs are not
        needed.

        Args:
            read_image (bool, optional): If `True`, the screenshot image will
                be included in the agent's context for direct visual analysis.
                If `False`, only a text message (including the saved file
                path) will be returned.
                (default: :obj:`True`)

        Returns:
            str | ToolResult: If `read_image` is `True`, returns a ToolResult
                containing the text message and the screenshot image. If
                `False`, returns a string with the file path only.
        """
        import base64
        import datetime
        import os
        import urllib.parse

        from camel.utils import sanitize_filename

        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.get_screenshot()

            result_text = result.text
            file_path = None

            if result.images:
                cache_dir = os.path.abspath(self._cache_dir)
                os.makedirs(cache_dir, exist_ok=True)

                try:
                    page_info = await ws_wrapper.get_tab_info()
                    current_tab = next(
                        (tab for tab in page_info if tab.get('is_current')),
                        None,
                    )
                    url = current_tab['url'] if current_tab else 'unknown'
                except Exception:
                    url = 'unknown'

                parsed_url = urllib.parse.urlparse(url)
                url_name = sanitize_filename(
                    str(parsed_url.path) or 'homepage', max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
                file_path = os.path.join(
                    cache_dir, f"{url_name}_{timestamp}.png"
                )

                # Process images and optionally add rulers
                processed_images = []
                for _, image_data in enumerate(result.images):
                    if image_data.startswith('data:image/png;base64,'):
                        base64_data = image_data.split(',', 1)[1]
                        image_bytes = base64.b64decode(base64_data)

                        # Add rulers in full_visual_mode
                        if self._full_visual_mode:
                            image_bytes = _add_rulers_to_image(
                                image_bytes, tick_interval=100
                            )
                            # Re-encode to base64 for the processed image
                            processed_base64 = base64.b64encode(
                                image_bytes
                            ).decode('utf-8')
                            processed_images.append(
                                f'data:image/png;base64,{processed_base64}'
                            )
                        else:
                            processed_images.append(image_data)

                        with open(file_path, 'wb') as f:
                            f.write(image_bytes)

                        logger.info(f"Screenshot saved to: {file_path}")

                        result_text += f" (saved to: {file_path})"
                        break

            if read_image and result.images:
                logger.info(
                    f"Returning ToolResult with {len(result.images)} image(s) "
                    "for agent context"
                )
                # Use processed images (with rulers) if in full_visual_mode
                images_to_return = (
                    processed_images
                    if self._full_visual_mode and processed_images
                    else result.images
                )
                return ToolResult(
                    text=result_text,
                    images=images_to_return,
                )
            else:
                return result_text
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            return f"Error capturing screenshot: {e}"

    async def browser_click(
        self,
        *,
        ref: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Performs a click on an element on the page.

        Supports two modes:
        - Ref mode: Click by element ref ID (from snapshot)
        - Pixel mode: Click by x, y pixel coordinates

        Args:
            ref (Optional[str]): The `ref` ID of the element to click.
            x (Optional[float]): X pixel coordinate for click.
            y (Optional[float]): Y pixel coordinate for click.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            if x is not None and y is not None:
                result = await ws_wrapper.mouse_control('click', x, y)
            elif ref is not None:
                result = await ws_wrapper.click(ref)
            else:
                raise ValueError(
                    "Must provide either 'ref' or both 'x' and 'y'"
                )
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return self._build_error_response(f"Error clicking element: {e}")

    async def browser_type(
        self,
        *,
        ref: Optional[str] = None,
        text: Optional[str] = None,
        inputs: Optional[List[Dict[str, str]]] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Types text into one or more input elements on the page.

        Supports multiple modes:
        - Ref mode: Provide 'ref' and 'text'
        - Pixel mode: Provide 'x', 'y' and 'text' (clicks to focus, then types)
        - Multiple inputs mode: Provide 'inputs' list

        Args:
            ref (Optional[str]): The `ref` ID of the input element.
            text (Optional[str]): The text to type.
            inputs (Optional[List[Dict[str, str]]]): List of inputs with
                'ref' and 'text' keys.
            x (Optional[float]): X pixel coordinate of input field.
            y (Optional[float]): Y pixel coordinate of input field.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()

            if x is not None and y is not None and text is not None:
                # Pixel mode: click to focus, then type using keyboard
                await ws_wrapper.mouse_control('click', x, y)
                await asyncio.sleep(0.1)  # Wait for focus
                result = await ws_wrapper.batch_keyboard_input(
                    [{"type": "type", "text": text, "delay": 0}]
                )
            elif ref is not None and text is not None:
                result = await ws_wrapper.type(ref, text)
            elif inputs is not None:
                result = await ws_wrapper.type_multiple(inputs)
            else:
                raise ValueError(
                    "Provide 'ref' and 'text', or 'x', 'y' and 'text', "
                    "or 'inputs' list"
                )

            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return self._build_error_response(f"Error typing text: {e}")

    async def browser_select(self, *, ref: str, value: str) -> Dict[str, Any]:
        r"""Selects an option in a dropdown (`<select>`) element.

        Args:
            ref (str): The `ref` ID of the `<select>` element.
            value (str): The `value` attribute of the `<option>` to select,
                not its visible text.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after the
                  selection.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.select(ref, value)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to select option: {e}")
            return self._build_error_response(f"Error selecting option: {e}")

    async def browser_scroll(
        self, *, direction: str, amount: int = 500
    ) -> Dict[str, Any]:
        r"""Scrolls the current page window.

        Args:
            direction (str): The direction to scroll: 'up' or 'down'.
            amount (int): The number of pixels to scroll, default is 500.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after scrolling.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.scroll(direction, amount)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return self._build_error_response(f"Error scrolling: {e}")

    async def browser_enter(self) -> Dict[str, Any]:
        r"""Simulates pressing the Enter key on the currently focused
        element.

        This is useful for submitting forms or search queries after using the
        `type` tool.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A new page snapshot, as this action often
                  triggers navigation.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.enter()
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to press enter: {e}")
            return self._build_error_response(f"Error pressing enter: {e}")

    async def browser_mouse_control(
        self, *, control: str, x: float, y: float
    ) -> Dict[str, Any]:
        r"""Control the mouse to interact with browser with x, y coordinates

        Args:
            control ([str]): The action to perform: 'click', 'right_click'
            or 'dblclick'.
            x (float): x-coordinate for the control action.
            y (float): y-coordinate for the control action.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after mouse
                control action.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.mouse_control(control, x, y)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to control mouse: {e}")
            return self._build_error_response(f"Error with mouse control: {e}")

    async def browser_mouse_drag(
        self,
        *,
        from_ref: Optional[str] = None,
        to_ref: Optional[str] = None,
        from_x: Optional[float] = None,
        from_y: Optional[float] = None,
        to_x: Optional[float] = None,
        to_y: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Drag and drop in the browser using ref IDs or pixel coordinates.

        Supports two modes:
        - Ref mode: Provide from_ref and to_ref
        - Pixel mode: Provide from_x, from_y, to_x, to_y

        Args:
            from_ref (Optional[str]): The ref ID of the source element.
            to_ref (Optional[str]): The ref ID of the target element.
            from_x (Optional[float]): Source X pixel coordinate.
            from_y (Optional[float]): Source Y pixel coordinate.
            to_x (Optional[float]): Target X pixel coordinate.
            to_y (Optional[float]): Target Y pixel coordinate.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.mouse_drag(
                from_ref=from_ref,
                to_ref=to_ref,
                from_x=from_x,
                from_y=from_y,
                to_x=to_x,
                to_y=to_y,
            )
            )
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Error with mouse drag and drop: {e}")
            return self._build_error_response(
                f"Error with mouse drag and drop: {e}"
            )

    async def browser_press_key(self, *, keys: List[str]) -> Dict[str, Any]:
        r"""Press key and key combinations.
        Supports single key press or combination of keys by concatenating
        them with '+' separator.

        Args:
            keys (List[str]): key or list of keys.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after
                press key action.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.press_key(keys)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return self._build_error_response(f"Error with press key: {e}")

    async def browser_upload_file(
        self,
        *,
        file_path: str,
        ref: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Uploads a file by clicking the element or coordinates that
        triggers a file chooser.

        Supports both ref mode and pixel mode.

        Args:
            file_path (str): The absolute path to the file to upload.
            ref (Optional[str]): The `ref` ID of the clickable upload element
                (e.g., a "Choose File" button). This ID is obtained from a
                page snapshot (`get_page_snapshot` or `get_som_screenshot`).
            x (Optional[float]): X pixel coordinate for pixel mode.
            y (Optional[float]): Y pixel coordinate for pixel mode.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after the upload.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.upload_file(
                file_path=file_path, ref=ref, x=x, y=y
            )
            return await self._build_action_response(
                result, ws_wrapper, include_note=False
            )
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return self._build_error_response(
                f"Error uploading file: {e}", include_note=False
            )

    async def browser_download_file(
        self,
        *,
        ref: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Downloads a file by clicking the element or coordinates that
        triggers a download.

        Supports both ref mode and pixel mode.

        Args:
            ref (Optional[str]): The `ref` ID of the clickable download
                element (e.g., a "Download" button or link). This ID is
                obtained from a page snapshot (`get_page_snapshot` or
                `get_som_screenshot`).
            x (Optional[float]): X pixel coordinate for pixel mode.
            y (Optional[float]): Y pixel coordinate for pixel mode.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation with file name and save path.
                - "snapshot" (str): A snapshot of the page after the download.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.download_file(ref=ref, x=x, y=y)
            return await self._build_action_response(
                result, ws_wrapper, include_note=False
            )
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return self._build_error_response(
                f"Error downloading file: {e}", include_note=False
            )

    async def browser_switch_tab(self, *, tab_id: str) -> Dict[str, Any]:
        r"""Switches to a different browser tab using its ID.

        After switching, all actions will apply to the new tab. Use
        `get_tab_info` to find the ID of the tab you want to switch to.

        Args:
            tab_id (str): The ID of the tab to activate.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the newly active tab.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the new active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.switch_tab(tab_id)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to switch tab: {e}")
            return self._build_error_response(f"Error switching tab: {e}")

    async def browser_close_tab(self, *, tab_id: str) -> Dict[str, Any]:
        r"""Closes a browser tab using its ID.

        Use `get_tab_info` to find the ID of the tab to close. After
        closing, the browser will switch to another tab if available.

        Args:
            tab_id (str): The ID of the tab to close.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the active tab after
                closure.
                - "tabs" (List[Dict]): Information about remaining tabs.
                - "current_tab" (int): Index of the new active tab.
                - "total_tabs" (int): Total number of remaining tabs.
                - "note" (str): A note about the loading status of the page.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.close_tab(tab_id)
            return await self._build_action_response(result, ws_wrapper)
        except Exception as e:
            logger.error(f"Failed to close tab: {e}")
            return self._build_error_response(f"Error closing tab: {e}")

    async def browser_get_tab_info(self) -> Dict[str, Any]:
        r"""Gets a list of all open browser tabs and their information.

        This includes each tab's index, title, and URL, and indicates which
        tab is currently active. Use this to manage multiple tabs.

        Returns:
            Dict[str, Any]: A dictionary with tab information:
                - "tabs" (List[Dict]): A list of open tabs, each with:
                  - "index" (int): The tab's zero-based index.
                  - "title" (str): The page title.
                  - "url" (str): The current URL.
                  - "is_current" (bool): True if the tab is active.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            tab_info = await ws_wrapper.get_tab_info()

            return {
                "tabs": tab_info,
                "current_tab": next(
                    (
                        i
                        for i, tab in enumerate(tab_info)
                        if tab.get("is_current")
                    ),
                    0,
                ),
                "total_tabs": len(tab_info),
            }
        except Exception as e:
            logger.error(f"Failed to get tab info: {e}")
            return {
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    async def browser_console_view(self) -> Dict[str, Any]:
        r"""View current page console logs.

        Returns:
            Dict[str, Any]: A dictionary with tab information:
                - "console_messages" (List[Dict]) : List of messages logged
                in the current page

        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            console_logs = await ws_wrapper.console_view()

            return {"console_messages": console_logs}
        except Exception as e:
            logger.error(f"Failed to get console view: {e}")
            return {"console_messages": []}

    async def browser_console_exec(self, code: str) -> Dict[str, Any]:
        r"""Execute javascript code in the console of the current page and get
        results.

        Args:
            code (str): JavaScript code to execute in the browser console.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the active tab after
                console execute action.
                - "tabs" (List[Dict]): Information about remaining tabs.
                - "current_tab" (int): Index of the new active tab.
                - "total_tabs" (int): Total number of remaining tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.console_exec(code)

            tab_info = await ws_wrapper.get_tab_info()

            # Clean snapshot if enabled
            if "snapshot" in result:
                result["snapshot"] = self._clean_snapshot_if_enabled(
                    result["snapshot"], "browser_console_exec"
                )

            result.update(
                {
                    "tabs": tab_info,
                    "current_tab": next(
                        (
                            i
                            for i, tab in enumerate(tab_info)
                            if tab.get("is_current")
                        ),
                        0,
                    ),
                    "total_tabs": len(tab_info),
                }
            )

            return result
        except Exception as e:
            logger.error(f"Failed to execute javascript in console: {e}")
            return {
                "result": f"Error in code execution: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    @high_level_action
    async def browser_sheet_input(
        self, *, cells: List[SheetCell]
    ) -> Dict[str, Any]:
        r"""Input text into multiple cells in a spreadsheet (e.g., Google
        Sheets).

        Args:
            cells (List[Dict[str, Any]]): List of cells to input, each
                containing:
                - "row" (int): Row index (0-based). Row 0 = first row,
                  Row 1 = second row, etc.
                - "col" (int): Column index (0-based). Col 0 = Column A,
                  Col 1 = Column B, etc.
                - "text" (str): Text to input into the cell

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action with details.
                - "content" (str): The updated spreadsheet content (auto-read
                  after input).
                - "snapshot" (str): Always empty string (sheet tools don't
                  return snapshots).
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.

        Example:
            >>> cells = [
            ...     {"row": 0, "col": 0, "text": "Name"},
            ...     {"row": 0, "col": 1, "text": "Age"},
            ...     {"row": 1, "col": 0, "text": "Alice"},
            ...     {"row": 1, "col": 1, "text": "30"},
            ... ]
        """
        try:
            import platform

            ws_wrapper = await self._get_ws_wrapper()
            system = platform.system()

            # Normalize cells: convert column labels to indices if needed
            normalized_cells = []
            for cell in cells:
                normalized_cell = cell.copy()

                # Convert column label (A, B, C, ...) to index if it's a string
                col = cell.get("col", 0)
                if isinstance(col, str):
                    col = col.strip().upper()
                    # Convert A->0, B->1, ..., Z->25, AA->26, AB->27, etc.
                    col_index = 0
                    for char in col:
                        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
                    normalized_cell["col"] = col_index - 1
                else:
                    normalized_cell["col"] = int(col)

                # Row is always used as-is (should be 0-based integer)
                normalized_cell["row"] = int(cell.get("row", 0))
                normalized_cell["text"] = str(cell.get("text", ""))
                normalized_cells.append(normalized_cell)

            # Perform batch input
            input_result = await self._sheet_input_batch_js(
                normalized_cells, ws_wrapper, system
            )

            # Read sheet content after input
            try:
                read_result = await self.browser_sheet_read()
                return {
                    "result": input_result["result"],
                    "content": read_result.get("content", ""),
                    "snapshot": "",
                    "tabs": input_result.get("tabs", []),
                    "current_tab": input_result.get("current_tab", 0),
                    "total_tabs": input_result.get("total_tabs", 0),
                }
            except Exception as read_error:
                logger.warning(f"Failed to auto-read sheet: {read_error}")
                input_result["snapshot"] = ""
                return input_result

        except Exception as e:
            logger.error(f"Failed to input to sheet: {e}")
            return {
                "result": f"Error inputting to sheet: {e}",
                "content": "",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    async def _sheet_input_batch_js(
        self,
        cells: List[SheetCell],
        ws_wrapper: Any,
        system: str,
    ) -> Dict[str, Any]:
        r"""Input to sheet using batch keyboard input with absolute positioning
        via Name Box (Cmd+J).

        This is more robust than relative navigation (arrow keys) because it
        handles hidden rows/columns and merged cells correctly.
        """
        operations: List[Dict[str, Any]] = []

        def col_to_letter(col_idx: int) -> str:
            """Convert 0-based column index to letter (0->A, 25->Z, 26->AA)."""
            result = ""
            col_idx += 1  # Convert to 1-based for calculation
            while col_idx > 0:
                col_idx, remainder = divmod(col_idx - 1, 26)
                result = chr(65 + remainder) + result
            return result

        for cell in cells:
            target_row = cell.get("row", 0)
            target_col = cell.get("col", 0)
            text = cell.get("text", "")

            # Convert to A1 notation
            col_letter = col_to_letter(target_col)
            row_number = target_row + 1
            cell_address = f"{col_letter}{row_number}"

            # 1. Focus Name Box
            if system == "Darwin":
                operations.append({"type": "press", "keys": ["Meta", "j"]})
            else:
                # On Windows/Linux, it's usually Ctrl+J or Alt+D
                # The snapshot showed Cmd+J for Mac.
                # Standard Google Sheets shortcut for
                # "Go to range" is F5 or Ctrl+J
                operations.append({"type": "press", "keys": ["Control", "j"]})

            operations.append({"type": "wait", "delay": 500})

            # 2. Type Address
            operations.append(
                {"type": "type", "text": cell_address, "delay": 0}
            )
            operations.append({"type": "wait", "delay": 200})
            operations.append({"type": "press", "keys": ["Enter"]})
            operations.append({"type": "wait", "delay": 500})

            # 3. Clear content (Delete/Backspace)
            # Just in case, press Delete to clear existing content
            operations.append({"type": "press", "keys": ["Delete"]})
            operations.append({"type": "wait", "delay": 100})

            # 4. Type Text
            if text:
                operations.append({"type": "type", "text": text, "delay": 0})
                operations.append({"type": "wait", "delay": 200})
                # Press Enter to confirm input
                operations.append({"type": "press", "keys": ["Enter"]})
                operations.append({"type": "wait", "delay": 300})

        # Chunk operations to avoid 100-op limit in TypeScript backend
        # Each cell update takes ~10 ops, so 100 ops is only ~10 cells.
        # We split into chunks of 50 ops to be safe.
        CHUNK_SIZE = 50

        try:
            for i in range(0, len(operations), CHUNK_SIZE):
                chunk = operations[i : i + CHUNK_SIZE]
                await ws_wrapper.batch_keyboard_input(
                    chunk, skip_stability_wait=True
                )
                # Small delay between chunks
                await asyncio.sleep(0.2)

            # Wait a bit for the last input to settle
            await asyncio.sleep(1.0)

            tab_info = await ws_wrapper.get_tab_info()

            return {
                "result": (
                    f"Successfully input to {len(cells)} cells "
                    "using absolute navigation"
                ),
                "snapshot": "",
                "tabs": tab_info,
                "current_tab": next(
                    (
                        i
                        for i, tab in enumerate(tab_info)
                        if tab.get("is_current")
                    ),
                    0,
                ),
                "total_tabs": len(tab_info),
            }

        except Exception as e:
            logger.error(f"Batch keyboard execution failed: {e}")
            return {
                "result": f"Error in batch keyboard execution: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    def _trim_sheet_content(self, content: str) -> str:
        """Trim sheet content and add row/column labels.

        Remove all empty rows and columns, then add:
        - Column headers: A, B, C, D...
        - Row numbers: 0, 1, 2, 3...

        Args:
            content (str): Raw sheet content with tabs and newlines.

        Returns:
            str: Trimmed content with row/column labels.
        """
        if not content or not content.strip():
            return ""

        # Split into rows and parse into 2D array
        rows = content.split('\n')
        grid: List[List[str]] = []
        max_cols = 0
        for row_str in rows:
            cells = row_str.split('\t')
            grid.append(cells)
            max_cols = max(max_cols, len(cells))

        # Pad rows to same length
        for row_list in grid:
            while len(row_list) < max_cols:
                row_list.append('')

        if not grid:
            return ""

        # Find non-empty rows and columns (keep original indices)
        non_empty_rows = []
        for i, row_cells in enumerate(grid):
            if any(cell.strip() for cell in row_cells):
                non_empty_rows.append(i)

        non_empty_cols = []
        for j in range(max_cols):
            if any(grid[i][j].strip() for i in range(len(grid))):
                non_empty_cols.append(j)

        # If no content found
        if not non_empty_rows or not non_empty_cols:
            return ""

        # Extract non-empty rows and columns
        filtered_grid = []
        for i in non_empty_rows:
            filtered_row = [grid[i][j] for j in non_empty_cols]
            filtered_grid.append(filtered_row)

        # Generate column labels using original column indices
        def col_label(index):
            label = ""
            while True:
                label = chr(65 + (index % 26)) + label
                index = index // 26
                if index == 0:
                    break
                index -= 1
            return label

        col_headers = [col_label(j) for j in non_empty_cols]

        # Add column headers as first row
        result_rows = ['\t'.join(['', *col_headers])]

        # Add data rows with original row numbers (0-based)
        for row_idx, row_data in zip(non_empty_rows, filtered_grid):
            result_rows.append('\t'.join([str(row_idx), *row_data]))

        return '\n'.join(result_rows)

    @high_level_action
    async def browser_sheet_read(self) -> Dict[str, Any]:
        r"""Read content from a spreadsheet.

        This tool reads spreadsheet content and returns it in a structured
        format with row/column labels. Empty rows and columns are
        automatically removed.

        Output format:
        - First row: Column labels (A, B, C, ..., Z, AA, AB, ...)
        - First column: Row numbers (0, 1, 2, 3, ...) - 0-based
        - Labels show ORIGINAL positions in the spreadsheet (before removing
          empty rows/columns)

        Row/column indices match browser_sheet_input directly:
        - Row label "0" in output = row index 0 in browser_sheet_input
        - Column label "A" in output = col index 0 in browser_sheet_input
        - Column label "C" in output = col index 2 in browser_sheet_input

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation message.
                - "content" (str): Tab-separated spreadsheet content with
                  row/column labels. Format:
                  Line 1: "\tA\tB\tC" (column headers)
                  Line 2+: "0\tdata1\tdata2\tdata3" (row number + data)
                - "snapshot" (str): Always empty string (sheet tools don't
                  return snapshots).
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.

        Example output:
                A	B
            0	Name	Age
            1	Alice	30
            2	Bob	25
        """
        import platform
        import uuid

        ws_wrapper = await self._get_ws_wrapper()

        # Use unique ID to avoid conflicts in parallel execution
        request_id = str(uuid.uuid4())
        var_name = f"__sheetCopy_{request_id.replace('-', '_')}"

        try:
            # Step 1: Setup copy interception with multiple captures
            js_inject = f"""
            window.{var_name} = [];
            let copyCount = 0;
            const copyListener = function(e) {{
                try {{
                    // Intercept clipboard data before system clipboard write
                    // Capture from Google Sheets' setData call
                    const originalSetData = e.clipboardData.setData.bind(
                        e.clipboardData
                    );
                    let capturedText = '';

                    e.clipboardData.setData = function(type, data) {{
                        if (type === 'text/plain') {{
                            capturedText = data;
                        }}
                        // Prevent system clipboard write
                    }};

                    // Let Google Sheets process event (calls setData)
                    // Event propagates and Sheets tries to set clipboard
                    setTimeout(() => {{
                        copyCount++;
                        window.{var_name}.push(capturedText);
                    }}, 0);

                    // Prevent the default browser copy behavior
                    e.preventDefault();
                }} catch (err) {{
                    console.error(
                        '[SheetRead] Failed to intercept copy data:', err
                    );
                }}
            }};

            document.addEventListener('copy', copyListener, true);
            window.{var_name}_removeListener = () => {{
                document.removeEventListener('copy', copyListener, true);
            }};

            'Copy listener installed';
            """
            await ws_wrapper.console_exec(js_inject)

            system = platform.system()
            import asyncio

            if system == "Darwin":
                select_all_copy_ops: List[Dict[str, Any]] = [
                    {"type": "press", "keys": ["Meta", "a"]},
                    {"type": "wait", "delay": 100},
                    {"type": "press", "keys": ["Meta", "c"]},
                ]
                await ws_wrapper.batch_keyboard_input(
                    select_all_copy_ops, skip_stability_wait=True
                )
                await asyncio.sleep(0.2)

                # Repeat to capture correct one
                await ws_wrapper.batch_keyboard_input(
                    select_all_copy_ops, skip_stability_wait=True
                )
                await asyncio.sleep(0.2)
            else:
                select_all_copy_ops = [
                    {"type": "press", "keys": ["Control", "a"]},
                    {"type": "wait", "delay": 100},
                    {"type": "press", "keys": ["Control", "c"]},
                ]
                await ws_wrapper.batch_keyboard_input(
                    select_all_copy_ops, skip_stability_wait=True
                )
                await asyncio.sleep(0.2)

                # Repeat to capture correct one
                await ws_wrapper.batch_keyboard_input(
                    select_all_copy_ops, skip_stability_wait=True
                )
                await asyncio.sleep(0.2)

            js_check = f"window.{var_name} || []"
            content_result = await ws_wrapper.console_exec(js_check)
            result_str = content_result.get("result", "[]")

            import json

            if isinstance(result_str, list):
                captured_contents = result_str
            elif isinstance(result_str, str):
                if result_str.startswith("Console execution result: "):
                    result_str = result_str[
                        len("Console execution result: ") :
                    ]
                result_str = result_str.strip()

                try:
                    captured_contents = json.loads(result_str)
                except json.JSONDecodeError:
                    captured_contents = []
            else:
                captured_contents = []

            if not captured_contents:
                sheet_content = ""
            elif len(captured_contents) == 1:
                sheet_content = captured_contents[0]
            else:

                def count_non_empty_cells(content):
                    if not content:
                        return 0
                    count = 0
                    for line in content.split('\n'):
                        for cell in line.split('\t'):
                            if cell.strip():
                                count += 1
                    return count

                counts = [
                    count_non_empty_cells(content)
                    for content in captured_contents[:2]
                ]
                best_idx = 0 if counts[0] > counts[1] else 1
                sheet_content = captured_contents[best_idx]

            sheet_content = self._trim_sheet_content(sheet_content)

            tab_info = await ws_wrapper.get_tab_info()

            return {
                "result": "Successfully read spreadsheet content",
                "content": sheet_content,
                "snapshot": "",  # Sheet tools don't return snapshots
                "tabs": tab_info,
                "current_tab": next(
                    (
                        i
                        for i, tab in enumerate(tab_info)
                        if tab.get("is_current")
                    ),
                    0,
                ),
                "total_tabs": len(tab_info),
            }

        except Exception as e:
            logger.error(f"Failed to read sheet: {e}")
            return {
                "result": f"Error reading sheet: {e}",
                "content": "",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }
        finally:
            js_cleanup = f"""
            if (window.{var_name}_removeListener) {{
                window.{var_name}_removeListener();
            }}
            delete window.{var_name};
            delete window.{var_name}_removeListener;
            'cleaned'
            """
            with contextlib.suppress(Exception):
                await ws_wrapper.console_exec(js_cleanup)

    # Additional methods for backward compatibility
    async def browser_wait_user(
        self, timeout_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        r"""Pauses execution and waits for human input from the console.

        Use this for tasks requiring manual steps, like solving a CAPTCHA.
        The
        agent will resume after the user presses Enter in the console.

        Args:
            timeout_sec (Optional[float]): Max time to wait in seconds. If
                `None`, it will wait indefinitely.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): A message indicating how the wait ended.
                - "snapshot" (str): The page snapshot after the wait.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        import asyncio

        prompt = (
            "🕑 Agent waiting for human input. "
            "Complete action in browser, then press Enter..."
        )
        logger.info(f"\n{prompt}\n")

        async def _await_enter():
            try:
                await asyncio.to_thread(
                    input, ">>> Press Enter to resume <<<\n"
                )
            except (asyncio.CancelledError, Exception):
                # Handle cancellation gracefully
                pass

        try:
            if timeout_sec is not None:
                logger.info(
                    f"Waiting for user input with timeout: {timeout_sec}s"
                )
                start_time = time.time()
                task = asyncio.create_task(_await_enter())
                try:
                    await asyncio.wait_for(task, timeout=timeout_sec)
                    wait_time = time.time() - start_time
                    logger.info(f"User input received after {wait_time:.2f}s")
                    result_msg = "User resumed."
                except asyncio.TimeoutError:
                    task.cancel()
                    # Wait for task to be cancelled properly
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    raise
            else:
                logger.info("Waiting for user input (no timeout)")
                start_time = time.time()
                await _await_enter()
                wait_time = time.time() - start_time
                logger.info(f"User input received after {wait_time:.2f}s")
                result_msg = "User resumed."
        except asyncio.TimeoutError:
            wait_time = timeout_sec or 0.0
            logger.info(
                f"User input timeout reached after {wait_time}s, "
                f"auto-resuming"
            )
            result_msg = f"Timeout {timeout_sec}s reached, auto-resumed."

        try:
            snapshot = await self.browser_get_page_snapshot()
            tab_info = await self.browser_get_tab_info()
            return {"result": result_msg, "snapshot": snapshot, **tab_info}
        except Exception as e:
            logger.warning(f"Failed to get snapshot after wait: {e}")
            return {
                "result": result_msg,
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    def clone_for_new_session(
        self, new_session_id: Optional[str] = None
    ) -> "HybridBrowserToolkit":
        r"""Create a new instance of HybridBrowserToolkit with a unique
        session.

        Args:
            new_session_id: Optional new session ID. If None, a UUID will be
            generated.

        Returns:
            A new HybridBrowserToolkit instance with the same configuration
            but a different session.
        """
        import uuid

        if new_session_id is None:
            new_session_id = str(uuid.uuid4())[:8]

        return HybridBrowserToolkit(
            headless=self._headless,
            user_data_dir=self._user_data_dir,
            stealth=self._stealth,
            cache_dir=f"{self._cache_dir.rstrip('/')}_clone_"
            f"{new_session_id}/",
            enabled_tools=self.enabled_tools.copy(),
            browser_log_to_file=self._browser_log_to_file,
            session_id=new_session_id,
            default_start_url=self._default_start_url,
            default_timeout=self._default_timeout,
            short_timeout=self._short_timeout,
            navigation_timeout=self._navigation_timeout,
            network_idle_timeout=self._network_idle_timeout,
            screenshot_timeout=self._screenshot_timeout,
            page_stability_timeout=self._page_stability_timeout,
            dom_content_loaded_timeout=self._dom_content_loaded_timeout,
            viewport_limit=self._viewport_limit,
            full_visual_mode=self._full_visual_mode,
            clean_snapshots=self._clean_snapshots,
        )

    # Tools not available in full_visual_mode (require ref, no pixel alt)
    _TOOLS_EXCLUDED_IN_VISUAL_MODE: ClassVar[List[str]] = [
        "browser_select",
        "browser_get_page_snapshot",
        "browser_get_som_screenshot",
    ]

    def _create_mode_wrapper(
        self,
        method: Callable[..., Any],
        tool_name: str,
        pixel_mode: bool,
    ) -> Callable[..., Any]:
        """Create a wrapper with mode-specific signature and docstring.

        Args:
            method: The original method to wrap.
            tool_name: Name of the tool.
            pixel_mode: If True, create pixel-coordinate wrapper.
                        If False, create ref-based wrapper.
        """
        if tool_name == "browser_click":
            if pixel_mode:

                async def browser_click_pixel(
                    *, x: float, y: float
                ) -> Dict[str, Any]:
                    r"""Clicks at the specified pixel coordinates on the page.

                    Use browser_get_screenshot to visually identify the
                    target position, then provide the x,y coordinates.

                    Args:
                        x (float): X pixel coordinate (horizontal position from
                            left edge of viewport).
                        y (float): Y pixel coordinate (vertical position from
                            top edge of viewport).

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(x=x, y=y)

                browser_click_pixel.__name__ = "browser_click"
                return browser_click_pixel
            else:

                async def browser_click_ref(*, ref: str) -> Dict[str, Any]:
                    r"""Clicks on an element identified by its ref ID.

                    The ref ID is obtained from a page snapshot
                    (browser_get_page_snapshot or browser_get_som_screenshot).

                    Args:
                        ref (str): The ref ID of the element to click.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(ref=ref)

                browser_click_ref.__name__ = "browser_click"
                return browser_click_ref

        elif tool_name == "browser_type":
            if pixel_mode:

                async def browser_type_pixel(
                    *, x: float, y: float, text: str
                ) -> Dict[str, Any]:
                    r"""Types text at the specified pixel coordinates.

                    Clicks at the coordinates to focus the input field, then
                    types the given text.

                    Args:
                        x (float): X pixel coordinate of the input field.
                        y (float): Y pixel coordinate of the input field.
                        text (str): The text to type into the input field.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(x=x, y=y, text=text)

                browser_type_pixel.__name__ = "browser_type"
                return browser_type_pixel
            else:

                async def browser_type_ref(
                    *,
                    ref: Optional[str] = None,
                    text: Optional[str] = None,
                    inputs: Optional[List[Dict[str, str]]] = None,
                ) -> Dict[str, Any]:
                    r"""Types text into input elements identified by ref ID.

                    Supports single input (ref + text) or multiple inputs.

                    Args:
                        ref (Optional[str]): The ref ID of the input element.
                        text (Optional[str]): The text to type.
                        inputs (Optional[List[Dict[str, str]]]): List of
                            inputs, each with 'ref' and 'text' keys.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(ref=ref, text=text, inputs=inputs)

                browser_type_ref.__name__ = "browser_type"
                return browser_type_ref

        elif tool_name == "browser_mouse_drag":
            if pixel_mode:

                async def browser_mouse_drag_pixel(
                    *, from_x: float, from_y: float, to_x: float, to_y: float
                ) -> Dict[str, Any]:
                    r"""Drags from one position to another using pixels.

                    Use browser_get_screenshot to identify element positions.

                    Args:
                        from_x (float): Source X pixel coordinate.
                        from_y (float): Source Y pixel coordinate.
                        to_x (float): Target X pixel coordinate.
                        to_y (float): Target Y pixel coordinate.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(
                        from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y
                    )

                browser_mouse_drag_pixel.__name__ = "browser_mouse_drag"
                return browser_mouse_drag_pixel
            else:

                async def browser_mouse_drag_ref(
                    *, from_ref: str, to_ref: str
                ) -> Dict[str, Any]:
                    r"""Drags from one element to another using ref IDs.

                    The ref IDs are obtained from a page snapshot.

                    Args:
                        from_ref (str): The ref ID of the source element.
                        to_ref (str): The ref ID of the target element.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(from_ref=from_ref, to_ref=to_ref)

                browser_mouse_drag_ref.__name__ = "browser_mouse_drag"
                return browser_mouse_drag_ref

        elif tool_name == "browser_upload_file":
            if pixel_mode:

                async def browser_upload_file_pixel(
                    *, x: float, y: float, file_path: str
                ) -> Dict[str, Any]:
                    r"""Uploads a file by clicking at the specified pixel
                    coordinates.

                    Clicks at the coordinates to trigger the file chooser,
                    then uploads the specified file.

                    Args:
                        x (float): X pixel coordinate of the upload element.
                        y (float): Y pixel coordinate of the upload element.
                        file_path (str): The absolute path to the file to
                            upload.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(x=x, y=y, file_path=file_path)

                browser_upload_file_pixel.__name__ = "browser_upload_file"
                return browser_upload_file_pixel
            else:

                async def browser_upload_file_ref(
                    *, ref: str, file_path: str
                ) -> Dict[str, Any]:
                    r"""Uploads a file by clicking the element identified by
                    ref ID.

                    The ref ID is obtained from a page snapshot.

                    Args:
                        ref (str): The ref ID of the upload element.
                        file_path (str): The absolute path to the file to
                            upload.

                    Returns:
                        Dict[str, Any]: Result of the action.
                    """
                    return await method(ref=ref, file_path=file_path)

                browser_upload_file_ref.__name__ = "browser_upload_file"
                return browser_upload_file_ref

        elif tool_name == "browser_download_file":
            if pixel_mode:

                async def browser_download_file_pixel(
                    *, x: float, y: float
                ) -> Dict[str, Any]:
                    r"""Downloads a file by clicking at the specified pixel
                    coordinates.

                    Clicks at the coordinates to trigger the download.

                    Args:
                        x (float): X pixel coordinate of the download element.
                        y (float): Y pixel coordinate of the download element.

                    Returns:
                        Dict[str, Any]: Result of the action with file name
                            and save path.
                    """
                    return await method(x=x, y=y)

                browser_download_file_pixel.__name__ = "browser_download_file"
                return browser_download_file_pixel
            else:

                async def browser_download_file_ref(
                    *, ref: str
                ) -> Dict[str, Any]:
                    r"""Downloads a file by clicking the element identified by
                    ref ID.

                    The ref ID is obtained from a page snapshot.

                    Args:
                        ref (str): The ref ID of the download element.

                    Returns:
                        Dict[str, Any]: Result of the action with file name
                            and save path.
                    """
                    return await method(ref=ref)

                browser_download_file_ref.__name__ = "browser_download_file"
                return browser_download_file_ref

        return method

    def get_tools(self) -> List[FunctionTool]:
        r"""Get available function tools based on enabled_tools configuration.

        In full_visual_mode:
        - Tools requiring ref with no pixel alternative are excluded
        - browser_click and browser_type use pixel coordinates instead of ref
        """
        tool_map = {
            "browser_open": self.browser_open,
            "browser_close": self.browser_close,
            "browser_visit_page": self.browser_visit_page,
            "browser_back": self.browser_back,
            "browser_forward": self.browser_forward,
            "browser_get_page_snapshot": self.browser_get_page_snapshot,
            "browser_get_som_screenshot": self.browser_get_som_screenshot,
            "browser_get_screenshot": self.browser_get_screenshot,
            "browser_click": self.browser_click,
            "browser_type": self.browser_type,
            "browser_select": self.browser_select,
            "browser_scroll": self.browser_scroll,
            "browser_enter": self.browser_enter,
            "browser_mouse_control": self.browser_mouse_control,
            "browser_mouse_drag": self.browser_mouse_drag,
            "browser_press_key": self.browser_press_key,
            "browser_upload_file": self.browser_upload_file,
            "browser_download_file": self.browser_download_file,
            "browser_wait_user": self.browser_wait_user,
            "browser_switch_tab": self.browser_switch_tab,
            "browser_close_tab": self.browser_close_tab,
            "browser_get_tab_info": self.browser_get_tab_info,
            "browser_console_view": self.browser_console_view,
            "browser_console_exec": self.browser_console_exec,
            "browser_sheet_input": self.browser_sheet_input,
            "browser_sheet_read": self.browser_sheet_read,
        }

        # Tools that need mode-specific wrappers (different signatures)
        mode_specific_tools = {
            "browser_click",
            "browser_type",
            "browser_mouse_drag",
            "browser_upload_file",
            "browser_download_file",
        }

        enabled_tools = []

        for tool_name in self.enabled_tools:
            # Skip tools not available in full_visual_mode
            if (
                self._full_visual_mode
                and tool_name in self._TOOLS_EXCLUDED_IN_VISUAL_MODE
            ):
                logger.debug(f"Skipping {tool_name} in full_visual_mode")
                continue

            if tool_name not in tool_map:
                logger.warning(f"Unknown tool name: {tool_name}")
                continue

            method = tool_map[tool_name]

            # Apply mode-specific wrapper for tools with different signatures
            if tool_name in mode_specific_tools:
                method = self._create_mode_wrapper(
                    method, tool_name, pixel_mode=self._full_visual_mode
                )

            tool = FunctionTool(cast(Callable[..., Any], method))
            enabled_tools.append(tool)

        logger.info(f"Returning {len(enabled_tools)} enabled tools")
        return enabled_tools
