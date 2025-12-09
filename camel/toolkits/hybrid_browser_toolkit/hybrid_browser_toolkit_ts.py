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
# =========

import contextlib
import time
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    TypedDict,
    cast,
)

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils.commons import dependencies_required

from .config_loader import ConfigLoader
from .ws_wrapper import WebSocketBrowserWrapper, high_level_action

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
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_scroll",
        "browser_enter",
        "browser_mouse_control",
        "browser_mouse_drag",
        "browser_press_key",
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
        viewport_limit: bool = False,
        connect_over_cdp: bool = False,
        cdp_url: Optional[str] = None,
        cdp_keep_current_page: bool = False,
        full_visual_mode: bool = False,
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
            won't create new pages but use the existing one. Defaults to False.
            full_visual_mode (bool): When True, browser actions like click,
            browser_open, visit_page, etc. will not return snapshots.
            Defaults to False.
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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.open_browser(self._default_start_url)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to open browser: {e}")
            return {
                "result": f"Error opening browser: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.visit_page(url)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to visit page: {e}")
            return {
                "result": f"Error visiting page: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.back()

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to navigate back: {e}")
            return {
                "result": f"Error navigating back: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.forward()

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to navigate forward: {e}")
            return {
                "result": f"Error navigating forward: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
            return await ws_wrapper.get_page_snapshot(self._viewport_limit)
        except Exception as e:
            logger.error(f"Failed to get page snapshot: {e}")
            return f"Error capturing snapshot: {e}"

    @dependencies_required('PIL')
    async def browser_get_som_screenshot(
        self,
        read_image: bool = True,
        instruction: Optional[str] = None,
    ) -> str:
        r"""Captures a screenshot with interactive elements highlighted.

        "SoM" stands for "Set of Marks". This tool takes a screenshot and
        draws
        boxes around clickable elements, overlaying a `ref` ID on each. Use
        this for a visual understanding of the page, especially when the
        textual snapshot is not enough.

        Args:
            read_image (bool, optional): If `True`, the agent will analyze
                the screenshot. Requires agent to be registered.
                (default: :obj:`True`)
            instruction (Optional[str], optional): A specific question or
                command for the agent regarding the screenshot, used only if
                `read_image` is `True`. For example: "Find the login button."

        Returns:
            str: A confirmation message indicating the screenshot was
                captured, the file path where it was saved, and optionally the
                agent's analysis if `read_image` is `True`.
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

            if read_image and file_path:
                if self.agent is None:
                    logger.error(
                        "Cannot analyze screenshot: No agent registered. "
                        "Please pass this toolkit to ChatAgent via "
                        "toolkits_to_register_agent parameter."
                    )
                    result_text += (
                        " Error: No agent registered for image analysis. "
                        "Please pass this toolkit to ChatAgent via "
                        "toolkits_to_register_agent parameter."
                    )
                else:
                    try:
                        from PIL import Image

                        img = Image.open(file_path)
                        inst = instruction if instruction is not None else ""
                        message = BaseMessage.make_user_message(
                            role_name="User",
                            content=inst,
                            image_list=[img],
                        )

                        response = await self.agent.astep(message)
                        agent_response = response.msgs[0].content
                        result_text += f". Agent analysis: {agent_response}"
                    except Exception as e:
                        logger.error(f"Error analyzing screenshot: {e}")
                        result_text += f". Error analyzing screenshot: {e}"

            return result_text
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            return f"Error capturing screenshot: {e}"

    async def browser_click(self, *, ref: str) -> Dict[str, Any]:
        r"""Performs a click on an element on the page.

        Args:
            ref (str): The `ref` ID of the element to click. This ID is
                obtained from a page snapshot (`get_page_snapshot` or
                `get_som_screenshot`).

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the page after the
                  click.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.click(ref)

            tab_info = await ws_wrapper.get_tab_info()

            response = {
                "result": result.get("result", ""),
                "snapshot": result.get("snapshot", ""),
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

            if "newTabId" in result:
                response["newTabId"] = result["newTabId"]

            if "timing" in result:
                response["timing"] = result["timing"]

            return response
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return {
                "result": f"Error clicking element: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    async def browser_type(
        self,
        *,
        ref: Optional[str] = None,
        text: Optional[str] = None,
        inputs: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        r"""Types text into one or more input elements on the page.

        This method supports two modes:
        1. Single input mode (backward compatible): Provide 'ref' and 'text'
        2. Multiple inputs mode: Provide 'inputs' as a list of dictionaries
           with 'ref' and 'text' keys

        Args:
            ref (Optional[str]): The `ref` ID of the input element, from a
                snapshot. Required when using single input mode.
            text (Optional[str]): The text to type into the element. Required
                when using single input mode.
            inputs (Optional[List[Dict[str, str]]]): List of dictionaries,
                each containing 'ref' and 'text' keys for typing into multiple
                elements. Example: [{'ref': '1', 'text': 'username'},
                {'ref': '2', 'text': 'password'}]

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the page after
                  typing.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
                - "details" (Dict[str, Any]): When using multiple inputs,
                  contains success/error status for each ref.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()

            if ref is not None and text is not None:
                result = await ws_wrapper.type(ref, text)
            elif inputs is not None:
                result = await ws_wrapper.type_multiple(inputs)
            else:
                raise ValueError(
                    "Either provide 'ref' and 'text' for single input, "
                    "or 'inputs' for multiple inputs"
                )

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to type text: {e}")
            return {
                "result": f"Error typing text: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.select(ref, value)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to select option: {e}")
            return {
                "result": f"Error selecting option: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.scroll(direction, amount)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to scroll: {e}")
            return {
                "result": f"Error scrolling: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.enter()

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to press enter: {e}")
            return {
                "result": f"Error pressing enter: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.mouse_control(control, x, y)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to control mouse: {e}")
            return {
                "result": f"Error with mouse control: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    async def browser_mouse_drag(
        self, *, from_ref: str, to_ref: str
    ) -> Dict[str, Any]:
        r"""Control the mouse to drag and drop in the browser using ref IDs.

        Args:
            from_ref (str): The `ref` ID of the source element to drag from.
            to_ref (str): The `ref` ID of the target element to drag to.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A new page snapshot.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.mouse_drag(from_ref, to_ref)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Error with mouse drag and drop: {e}")
            return {
                "result": f"Error with mouse drag and drop: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.press_key(keys)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to press key: {e}")
            return {
                "result": f"Error with press key: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.switch_tab(tab_id)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to switch tab: {e}")
            return {
                "result": f"Error switching tab: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.close_tab(tab_id)

            tab_info = await ws_wrapper.get_tab_info()
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
            logger.error(f"Failed to close tab: {e}")
            return {
                "result": f"Error closing tab: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

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
        r"""Input to sheet using batch keyboard input with relative
        positioning.

        Builds all operations and sends them in ONE command to TypeScript,
        which executes them and only waits for stability once at the end.
        """
        operations: List[Dict[str, Any]] = []

        # Go to A1 to ensure we start from a known position
        if system == "Darwin":
            operations.append({"type": "press", "keys": ["Meta", "Home"]})
        else:
            operations.append({"type": "press", "keys": ["Control", "Home"]})
        operations.append({"type": "wait", "delay": 310})

        # Start at (0, 0)
        current_row = 0
        current_col = 0

        for cell in cells:
            target_row = cell.get("row", 0)
            target_col = cell.get("col", 0)
            text = cell.get("text", "")

            # Calculate relative movement needed
            row_diff = target_row - current_row
            col_diff = target_col - current_col

            # Navigate vertically
            if row_diff > 0:
                for _ in range(row_diff):
                    operations.append({"type": "press", "keys": ["ArrowDown"]})
                    operations.append({"type": "wait", "delay": 50})
            elif row_diff < 0:
                for _ in range(abs(row_diff)):
                    operations.append({"type": "press", "keys": ["ArrowUp"]})
                    operations.append({"type": "wait", "delay": 50})

            # Navigate horizontally
            if col_diff > 0:
                for _ in range(col_diff):
                    operations.append(
                        {"type": "press", "keys": ["ArrowRight"]}
                    )
                    operations.append({"type": "wait", "delay": 50})
            elif col_diff < 0:
                for _ in range(abs(col_diff)):
                    operations.append({"type": "press", "keys": ["ArrowLeft"]})
                    operations.append({"type": "wait", "delay": 50})

            # Wait after navigation if moved
            if row_diff != 0 or col_diff != 0:
                operations.append({"type": "wait", "delay": 100})

            # Clear and input
            operations.append({"type": "press", "keys": ["Delete"]})
            operations.append({"type": "wait", "delay": 120})

            if text:
                operations.append({"type": "type", "text": text, "delay": 0})
                operations.append({"type": "wait", "delay": 120})

            # Press Enter to confirm
            operations.append({"type": "press", "keys": ["Enter"]})
            operations.append({"type": "wait", "delay": 130})

            # Update current position (after Enter, cursor moves to next row)
            current_row = target_row + 1
            current_col = target_col

        try:
            await ws_wrapper._send_command(
                'batch_keyboard_input',
                {'operations': operations, 'skipStabilityWait': True},
            )
            tab_info = await ws_wrapper.get_tab_info()

            return {
                "result": f"Successfully input to {len(cells)} cells",
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
                await ws_wrapper._send_command(
                    'batch_keyboard_input',
                    {
                        'operations': select_all_copy_ops,
                        'skipStabilityWait': True,
                    },
                )
                await asyncio.sleep(0.2)

                # Repeat to capture correct one
                await ws_wrapper._send_command(
                    'batch_keyboard_input',
                    {
                        'operations': select_all_copy_ops,
                        'skipStabilityWait': True,
                    },
                )
                await asyncio.sleep(0.2)
            else:
                select_all_copy_ops = [
                    {"type": "press", "keys": ["Control", "a"]},
                    {"type": "wait", "delay": 100},
                    {"type": "press", "keys": ["Control", "c"]},
                ]
                await ws_wrapper._send_command(
                    'batch_keyboard_input',
                    {
                        'operations': select_all_copy_ops,
                        'skipStabilityWait': True,
                    },
                )
                await asyncio.sleep(0.2)

                # Repeat to capture correct one
                await ws_wrapper._send_command(
                    'batch_keyboard_input',
                    {
                        'operations': select_all_copy_ops,
                        'skipStabilityWait': True,
                    },
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
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Get available function tools based
        on enabled_tools configuration."""
        # Map tool names to their corresponding methods
        tool_map = {
            "browser_open": self.browser_open,
            "browser_close": self.browser_close,
            "browser_visit_page": self.browser_visit_page,
            "browser_back": self.browser_back,
            "browser_forward": self.browser_forward,
            "browser_get_page_snapshot": self.browser_get_page_snapshot,
            "browser_get_som_screenshot": self.browser_get_som_screenshot,
            "browser_click": self.browser_click,
            "browser_type": self.browser_type,
            "browser_select": self.browser_select,
            "browser_scroll": self.browser_scroll,
            "browser_enter": self.browser_enter,
            "browser_mouse_control": self.browser_mouse_control,
            "browser_mouse_drag": self.browser_mouse_drag,
            "browser_press_key": self.browser_press_key,
            "browser_wait_user": self.browser_wait_user,
            "browser_switch_tab": self.browser_switch_tab,
            "browser_close_tab": self.browser_close_tab,
            "browser_get_tab_info": self.browser_get_tab_info,
            "browser_console_view": self.browser_console_view,
            "browser_console_exec": self.browser_console_exec,
            "browser_sheet_input": self.browser_sheet_input,
            "browser_sheet_read": self.browser_sheet_read,
        }

        enabled_tools = []

        for tool_name in self.enabled_tools:
            if tool_name in tool_map:
                tool = FunctionTool(
                    cast(Callable[..., Any], tool_map[tool_name])
                )
                enabled_tools.append(tool)
            else:
                logger.warning(f"Unknown tool name: {tool_name}")

        logger.info(f"Returning {len(enabled_tools)} enabled tools")
        return enabled_tools
