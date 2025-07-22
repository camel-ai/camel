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

import time
from typing import Any, Callable, ClassVar, Dict, List, Optional, cast

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils.commons import dependencies_required

from .config_loader import ConfigLoader
from .ws_wrapper import WebSocketBrowserWrapper

logger = get_logger(__name__)


class HybridBrowserToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""A hybrid browser toolkit that combines non-visual, DOM-based browser
    automation with visual, screenshot-based capabilities.

    This toolkit now uses TypeScript implementation with Playwright's
    _snapshotForAI functionality for enhanced AI integration.
    """

    # Default tool list - core browser functionality
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

    # All available tools
    ALL_TOOLS: ClassVar[List[str]] = [
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_back",
        "browser_forward",
        "browser_get_page_snapshot",
        "browser_get_som_screenshot",
        "browser_get_page_links",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_scroll",
        "browser_enter",
        "browser_wait_user",
        "browser_solve_task",
        "browser_switch_tab",
        "browser_close_tab",
        "browser_get_tab_info",
    ]

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        web_agent_model: Optional[BaseModelBackend] = None,
        cache_dir: str = "tmp/",
        enabled_tools: Optional[List[str]] = None,
        browser_log_to_file: bool = False,
        session_id: Optional[str] = None,
        default_start_url: str = "https://google.com/",
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
    ) -> None:
        r"""Initialize the HybridBrowserToolkit.

        Args:
            headless (bool): Whether to run browser in headless mode.
            Defaults to True.
            user_data_dir (Optional[str]): Directory for user data
            persistence. Defaults to None.
            stealth (bool): Whether to enable stealth mode. Defaults to
            False.
            web_agent_model (Optional[BaseModelBackend]): Model for web
            agent operations. Defaults to None.
            cache_dir (str): Directory for caching. Defaults to "tmp/".
            enabled_tools (Optional[List[str]]): List of enabled tools.
            Defaults to None.
            browser_log_to_file (bool): Whether to log browser actions to
            file. Defaults to False.
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
        """
        super().__init__()
        RegisteredAgentToolkit.__init__(self)

        # Initialize configuration loader
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
            session_id=session_id,
            enabled_tools=enabled_tools,
            connect_over_cdp=connect_over_cdp,
            cdp_url=cdp_url,
        )

        # Legacy attribute access for backward compatibility
        browser_config = self.config_loader.get_browser_config()
        toolkit_config = self.config_loader.get_toolkit_config()

        self._headless = browser_config.headless
        self._user_data_dir = browser_config.user_data_dir
        self._stealth = browser_config.stealth
        self._web_agent_model = web_agent_model
        self._cache_dir = toolkit_config.cache_dir
        self._browser_log_to_file = toolkit_config.browser_log_to_file
        self._default_start_url = browser_config.default_start_url
        self._session_id = toolkit_config.session_id or "default"
        self._viewport_limit = browser_config.viewport_limit

        # Store timeout configuration for backward compatibility
        self._default_timeout = browser_config.default_timeout
        self._short_timeout = browser_config.short_timeout
        self._navigation_timeout = browser_config.navigation_timeout
        self._network_idle_timeout = browser_config.network_idle_timeout
        self._screenshot_timeout = browser_config.screenshot_timeout
        self._page_stability_timeout = browser_config.page_stability_timeout
        self._dom_content_loaded_timeout = (
            browser_config.dom_content_loaded_timeout
        )

        # Configure enabled tools
        if enabled_tools is None:
            self.enabled_tools = self.DEFAULT_TOOLS.copy()
        else:
            # Validate enabled tools
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

        # Initialize WebSocket wrapper
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

            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed() and not loop.is_running():
                    try:
                        loop.run_until_complete(
                            asyncio.wait_for(self.browser_close(), timeout=2.0)
                        )
                    except asyncio.TimeoutError:
                        pass
            except (RuntimeError, ImportError):
                pass
        except Exception:
            pass

    @property
    def web_agent_model(self) -> Optional[BaseModelBackend]:
        """Get the web agent model."""
        return self._web_agent_model

    @web_agent_model.setter
    def web_agent_model(self, value: Optional[BaseModelBackend]) -> None:
        """Set the web agent model."""
        self._web_agent_model = value

    @property
    def cache_dir(self) -> str:
        """Get the cache directory."""
        return self._cache_dir

    # Public API Methods

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

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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

            # Initialize result text
            result_text = result.text
            file_path = None

            # Save screenshot to cache directory if images are available
            if result.images:
                # Ensure cache directory exists (use absolute path)
                cache_dir = os.path.abspath(self._cache_dir)
                os.makedirs(cache_dir, exist_ok=True)

                # Get current page URL for filename
                try:
                    # Try to get the current page URL from the wrapper
                    page_info = await ws_wrapper.get_tab_info()
                    current_tab = next(
                        (tab for tab in page_info if tab.get('is_current')),
                        None,
                    )
                    url = current_tab['url'] if current_tab else 'unknown'
                except Exception:
                    url = 'unknown'

                # Generate filename
                parsed_url = urllib.parse.urlparse(url)
                url_name = sanitize_filename(
                    str(parsed_url.path) or 'homepage', max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
                file_path = os.path.join(
                    cache_dir, f"{url_name}_{timestamp}_som.png"
                )

                # Extract base64 data and save to file
                for _, image_data in enumerate(result.images):
                    if image_data.startswith('data:image/png;base64,'):
                        # Remove data URL prefix
                        base64_data = image_data.split(',', 1)[1]

                        # Decode and save
                        image_bytes = base64.b64decode(base64_data)
                        with open(file_path, 'wb') as f:
                            f.write(image_bytes)

                        logger.info(f"Screenshot saved to: {file_path}")

                        # Update result text to include file path
                        result_text += f" (saved to: {file_path})"
                        break

            # Analyze image if requested and agent is registered
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
                        # Load the image and create a message
                        from PIL import Image

                        img = Image.open(file_path)
                        inst = instruction if instruction is not None else ""
                        message = BaseMessage.make_user_message(
                            role_name="User",
                            content=inst,
                            image_list=[img],
                        )

                        # Get agent's analysis
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

            # Add tab information
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
            logger.error(f"Failed to click element: {e}")
            return {
                "result": f"Error clicking element: {e}",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 0,
            }

    async def browser_type(self, *, ref: str, text: str) -> Dict[str, Any]:
        r"""Types text into an input element on the page.

        Args:
            ref (str): The `ref` ID of the input element, from a snapshot.
            text (str): The text to type into the element.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A textual snapshot of the page after
                  typing.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        try:
            ws_wrapper = await self._get_ws_wrapper()
            result = await ws_wrapper.type(ref, text)

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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

            # Add tab information
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
            web_agent_model=self._web_agent_model,
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
            "browser_wait_user": self.browser_wait_user,
            "browser_switch_tab": self.browser_switch_tab,
            "browser_close_tab": self.browser_close_tab,
            "browser_get_tab_info": self.browser_get_tab_info,
        }

        enabled_tools = []

        for tool_name in self.enabled_tools:
            if (
                tool_name == "browser_solve_task"
                and self._web_agent_model is None
            ):
                logger.warning(
                    f"Tool '{tool_name}' is enabled but web_agent_model "
                    f"is not provided. Skipping this tool."
                )
                continue

            if tool_name in tool_map:
                tool = FunctionTool(
                    cast(Callable[..., Any], tool_map[tool_name])
                )
                enabled_tools.append(tool)
            else:
                logger.warning(f"Unknown tool name: {tool_name}")

        logger.info(f"Returning {len(enabled_tools)} enabled tools")
        return enabled_tools
