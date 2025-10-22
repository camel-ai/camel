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

import datetime
import io
import json
import os
import time
import urllib.parse
from functools import wraps
from typing import Any, Callable, ClassVar, Dict, List, Optional, cast

from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import sanitize_filename
from camel.utils.commons import dependencies_required

from .agent import PlaywrightLLMAgent
from .browser_session import HybridBrowserSession
from .config_loader import ConfigLoader

logger = get_logger(__name__)


class HybridBrowserToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""A hybrid browser toolkit that combines non-visual, DOM-based browser
    automation with visual, screenshot-based capabilities.

    This toolkit exposes a set of actions as CAMEL FunctionTools for agents
    to interact with web pages. It can operate in headless mode and supports
    both programmatic control of browser actions (like clicking and typing)
    and visual analysis of the page layout through screenshots with marked
    interactive elements.
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
        "browser_mouse_control",
        "browser_mouse_drag",
        "browser_press_key",
        "browser_wait_user",
        "browser_solve_task",
        "browser_switch_tab",
        "browser_close_tab",
        "browser_get_tab_info",
        "browser_console_view",
        "browser_console_exec",
    ]

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        web_agent_model: Optional[BaseModelBackend] = None,
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
    ) -> None:
        r"""Initialize the HybridBrowserToolkit.

        Args:
            headless (bool): Whether to run the browser in headless mode.
                Defaults to `True`.
            user_data_dir (Optional[str]): Path to a directory for storing
                browser data like cookies and local storage. Useful for
                maintaining sessions across runs. Defaults to `None` (a
                temporary directory is used).
            stealth (bool): Whether to run the browser in stealth mode to
            avoid
                bot detection. When enabled, hides WebDriver characteristics,
                spoofs navigator properties, and implements various
                anti-detection
                measures. Highly recommended for production use and when
                accessing sites with bot detection. Defaults to `False`.
            web_agent_model (Optional[BaseModelBackend]): The language model
                backend to use for the high-level `solve_task` agent. This is
                required only if you plan to use `solve_task`.
                Defaults to `None`.
            cache_dir (str): The directory to store cached files, such as
                screenshots. Defaults to `"tmp/"`.
            enabled_tools (Optional[List[str]]): List of tool names to
            enable.
                If None, uses DEFAULT_TOOLS. Available tools: browser_open,
                browser_close, browser_visit_page, browser_back,
                browser_forward, browser_get_page_snapshot,
                browser_get_som_screenshot, browser_get_page_links,
                browser_click, browser_type, browser_select,
                browser_scroll, browser_enter, browser_wait_user,
                browser_solve_task.
                Defaults to `None`.
            browser_log_to_file (bool): Whether to save detailed browser
            action logs to file.
                When enabled, logs action inputs/outputs, execution times,
                and page loading times.
                Logs are saved to an auto-generated timestamped file.
                Defaults to `False`.
            log_dir (Optional[str]): Custom directory path for log files.
                If None, defaults to "browser_log". Defaults to `None`.
            session_id (Optional[str]): A unique identifier for this browser
                session. When multiple HybridBrowserToolkit instances are
                used
                concurrently, different session IDs prevent them from sharing
                the same browser session and causing conflicts. If None, a
                default session will be used. Defaults to `None`.
            default_start_url (str): The default URL to navigate to when
                open_browser() is called without a start_url parameter or
                with
                None. Defaults to `"https://google.com/"`.
            default_timeout (Optional[int]): Default timeout in milliseconds
                for browser actions. If None, uses environment variable
                HYBRID_BROWSER_DEFAULT_TIMEOUT or defaults to 3000ms.
                Defaults to `None`.
            short_timeout (Optional[int]): Short timeout in milliseconds
                for quick browser actions. If None, uses environment variable
                HYBRID_BROWSER_SHORT_TIMEOUT or defaults to 1000ms.
                Defaults to `None`.
            navigation_timeout (Optional[int]): Custom navigation timeout in
            milliseconds.
                If None, uses environment variable
                HYBRID_BROWSER_NAVIGATION_TIMEOUT or defaults to 10000ms.
                Defaults to `None`.
            network_idle_timeout (Optional[int]): Custom network idle
            timeout in milliseconds.
                If None, uses environment variable
                HYBRID_BROWSER_NETWORK_IDLE_TIMEOUT or defaults to 5000ms.
                Defaults to `None`.
            screenshot_timeout (Optional[int]): Custom screenshot timeout in
            milliseconds.
                If None, uses environment variable
                HYBRID_BROWSER_SCREENSHOT_TIMEOUT or defaults to 15000ms.
                Defaults to `None`.
            page_stability_timeout (Optional[int]): Custom page stability
            timeout in milliseconds.
                If None, uses environment variable
                HYBRID_BROWSER_PAGE_STABILITY_TIMEOUT or defaults to 1500ms.
                Defaults to `None`.
            dom_content_loaded_timeout (Optional[int]): Custom DOM content
            loaded timeout in milliseconds.
                If None, uses environment variable
                HYBRID_BROWSER_DOM_CONTENT_LOADED_TIMEOUT or defaults to
                5000ms.
                Defaults to `None`.
            viewport_limit (bool): When True, only return snapshot results
                visible in the current viewport. When False, return all
                elements on the page regardless of visibility.
                Defaults to `False`.
        """
        super().__init__()
        RegisteredAgentToolkit.__init__(self)
        self._headless = headless
        self._user_data_dir = user_data_dir
        self._stealth = stealth
        self._web_agent_model = web_agent_model
        self._cache_dir = cache_dir or "tmp/"
        self._browser_log_to_file = browser_log_to_file
        self._log_dir = log_dir
        self._default_start_url = default_start_url or "https://google.com/"
        self._session_id = session_id or "default"
        self._viewport_limit = viewport_limit

        # Store timeout configuration
        self._default_timeout = default_timeout
        self._short_timeout = short_timeout
        self._navigation_timeout = ConfigLoader.get_navigation_timeout(
            navigation_timeout
        )
        self._network_idle_timeout = ConfigLoader.get_network_idle_timeout(
            network_idle_timeout
        )
        self._screenshot_timeout = ConfigLoader.get_screenshot_timeout(
            screenshot_timeout
        )
        self._page_stability_timeout = ConfigLoader.get_page_stability_timeout(
            page_stability_timeout
        )
        self._dom_content_loaded_timeout = (
            ConfigLoader.get_dom_content_loaded_timeout(
                dom_content_loaded_timeout
            )
        )

        # Logging configuration - fixed values for simplicity
        self.enable_action_logging = True
        self.enable_timing_logging = True
        self.enable_page_loading_logging = True
        self.log_to_console = False  # Always disabled for cleaner output
        self.log_to_file = browser_log_to_file
        self.max_log_length = None  # No truncation for file logs

        # Set up log file if needed
        if self.log_to_file:
            # Create log directory if it doesn't exist
            log_dir = self._log_dir if self._log_dir else "browser_log"
            os.makedirs(log_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path: Optional[str] = os.path.join(
                log_dir, f"hybrid_browser_toolkit_{timestamp}_{session_id}.log"
            )
        else:
            self.log_file_path = None

        # Initialize log buffer for in-memory storage
        self.log_buffer: List[Dict[str, Any]] = []

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

        # Log initialization if file logging is enabled
        if self.log_to_file:
            logger.info(
                "HybridBrowserToolkit initialized with file logging enabled"
            )
            logger.info(f"Log file path: {self.log_file_path}")

        # Core components
        temp_session = HybridBrowserSession(
            headless=headless,
            user_data_dir=user_data_dir,
            stealth=stealth,
            session_id=session_id,
            default_timeout=default_timeout,
            short_timeout=short_timeout,
        )
        # Use the session directly - singleton logic is handled in
        # ensure_browser
        self._session = temp_session
        self._playwright_agent: Optional[PlaywrightLLMAgent] = None
        self._unified_script = self._load_unified_analyzer()

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
                    # Try to close browser with a timeout to prevent hanging
                    try:
                        loop.run_until_complete(
                            asyncio.wait_for(self.browser_close(), timeout=2.0)
                        )
                    except asyncio.TimeoutError:
                        pass  # Skip cleanup if it takes too long
            except (RuntimeError, ImportError):
                pass  # Event loop unavailable, skip cleanup
        except Exception:
            pass  # Suppress all errors during garbage collection

    def _load_unified_analyzer(self) -> str:
        r"""Load the unified analyzer JavaScript script."""
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "unified_analyzer.js"
        )

        try:
            with open(
                script_path, "r", encoding='utf-8', errors='replace'
            ) as f:
                script_content = f.read()

            if not script_content.strip():
                raise ValueError(f"Script is empty: {script_path}")

            logger.debug(
                f"Loaded unified analyzer ({len(script_content)} chars)"
            )
            return script_content
        except FileNotFoundError:
            raise FileNotFoundError(f"Script not found: {script_path}")

    def _validate_ref(self, ref: str, method_name: str) -> None:
        r"""Validate ref parameter."""
        if not ref or not isinstance(ref, str):
            raise ValueError(
                f"{method_name}: 'ref' must be a non-empty string"
            )

    def _truncate_if_needed(self, content: Any) -> str:
        r"""Truncate content if max_log_length is set."""
        content_str = str(content)
        if (
            self.max_log_length is not None
            and len(content_str) > self.max_log_length
        ):
            return content_str[: self.max_log_length] + "... [TRUNCATED]"
        return content_str

    async def _get_current_url(self) -> Optional[str]:
        r"""Safely get the current URL of the active page."""
        try:
            page = await self._session.get_page()
            if page and not page.is_closed():
                return page.url
            return None  # Return None if page is closed
        except Exception:
            # This can happen if browser is not open.
            return None

    async def _log_action(
        self,
        action_name: str,
        inputs: Dict[str, Any],
        outputs: Any,
        execution_time: float,
        page_load_time: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        r"""Log action details with comprehensive information."""
        if not (self.enable_action_logging or self.enable_timing_logging):
            return

        current_url = await self._get_current_url()

        log_entry: Dict[str, Any] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action_name,
            "url": current_url,
            "execution_time_ms": round(execution_time * 1000, 2),
        }

        if self.enable_action_logging:
            log_entry["inputs"] = inputs
            if error:
                log_entry["error"] = str(error)
            elif isinstance(outputs, dict):
                # Unpack dictionary items into the log entry
                log_entry.update(outputs)
            else:
                # For non-dict outputs, assign to 'outputs' key
                log_entry["outputs"] = outputs

        if page_load_time is not None and self.enable_page_loading_logging:
            log_entry["page_load_time_ms"] = round(page_load_time * 1000, 2)

        # Add to buffer
        self.log_buffer.append(log_entry)

        # Console logging
        if self.log_to_console:
            log_msg = f"[BROWSER ACTION] {action_name}"
            if self.enable_timing_logging:
                log_msg += (
                    f" | Execution: " f"{log_entry['execution_time_ms']}ms"
                )
            if page_load_time is not None and self.enable_page_loading_logging:
                log_msg += (
                    f" | Page Load: " f"{log_entry['page_load_time_ms']}ms"
                )
            if error:
                log_msg += f" | ERROR: {error}"

            logger.info(log_msg)

            if self.enable_action_logging:
                logger.info(f"  Inputs: {self._truncate_if_needed(inputs)}")
                if not error:
                    if isinstance(outputs, dict):
                        for key, value in outputs.items():
                            logger.info(
                                f"  - {key}: "
                                f"{self._truncate_if_needed(value)}"
                            )
                    else:
                        logger.info(
                            f"  Outputs: {self._truncate_if_needed(outputs)}"
                        )

        # File logging
        if self.log_to_file and self.log_file_path:
            try:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    # Write full log entry to file without truncation
                    f.write(
                        json.dumps(log_entry, ensure_ascii=False, indent=2)
                        + '\n'
                    )
            except Exception as e:
                logger.error(f"Failed to write to log file: {e}")

    @staticmethod
    def action_logger(func: Callable[..., Any]) -> Callable[..., Any]:
        r"""Decorator to add logging to action methods."""

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            action_name = func.__name__
            start_time = time.time()

            # Log inputs
            inputs = {
                "args": args,  # Don't skip self since it's already handled
                "kwargs": kwargs,
            }

            try:
                # Execute the original function
                result = await func(self, *args, **kwargs)
                execution_time = time.time() - start_time

                # Log success
                await self._log_action(
                    action_name=action_name,
                    inputs=inputs,
                    outputs=result,
                    execution_time=execution_time,
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"{type(e).__name__}: {e!s}"

                # Log error
                await self._log_action(
                    action_name=action_name,
                    inputs=inputs,
                    outputs=None,
                    execution_time=execution_time,
                    error=error_msg,
                )

                raise

        return wrapper

    async def _get_session(self) -> "HybridBrowserSession":
        """Get the correct singleton session instance."""
        singleton = await HybridBrowserSession._get_or_create_instance(
            self._session
        )
        if singleton is not self._session:
            logger.debug("Updating to singleton session instance")
            self._session = singleton
        return self._session

    async def _ensure_browser(self):
        # Get singleton instance and update self._session if needed
        session = await self._get_session()
        await session.ensure_browser()

    async def _require_page(self):
        # Get singleton instance and update self._session if needed
        session = await self._get_session()
        await session.ensure_browser()
        return await session.get_page()

    async def _wait_for_page_stability(self):
        r"""Wait for page to become stable after actions that might trigger
        updates. Optimized with shorter timeouts.
        """
        page = await self._require_page()
        import asyncio

        try:
            # Wait for DOM content to be loaded (reduced timeout)
            await page.wait_for_load_state(
                'domcontentloaded', timeout=self._page_stability_timeout
            )
            logger.debug("DOM content loaded")

            # Try to wait for network idle with shorter timeout
            try:
                await page.wait_for_load_state(
                    'networkidle', timeout=self._network_idle_timeout
                )
                logger.debug("Network idle achieved")
            except Exception:
                logger.debug("Network idle timeout - continuing anyway")

            # Reduced delay for JavaScript execution
            await asyncio.sleep(0.2)  # Reduced from 0.5s
            logger.debug("Page stability wait completed")

        except Exception as e:
            logger.debug(
                f"Page stability wait failed: {e} - continuing anyway"
            )

    async def _get_unified_analysis(
        self, max_retries: int = 3, viewport_limit: Optional[bool] = None
    ) -> Dict[str, Any]:
        r"""Get unified analysis data from the page with retry mechanism for
        navigation issues."""
        page = await self._require_page()

        for attempt in range(max_retries):
            try:
                if not self._unified_script:
                    logger.error("Unified analyzer script not loaded")
                    return {"elements": {}, "metadata": {"elementCount": 0}}

                # Wait for DOM stability before each attempt (with optimized
                # timeout)
                try:
                    await page.wait_for_load_state(
                        'domcontentloaded',
                        timeout=self._dom_content_loaded_timeout,
                    )
                except Exception:
                    # Don't fail if DOM wait times out
                    pass

                # Use instance viewport_limit if parameter not provided
                use_viewport_limit = (
                    viewport_limit
                    if viewport_limit is not None
                    else self._viewport_limit
                )
                result = await page.evaluate(
                    self._unified_script, use_viewport_limit
                )

                if not isinstance(result, dict):
                    logger.warning(f"Invalid result type: {type(result)}")
                    return {"elements": {}, "metadata": {"elementCount": 0}}

                # Success - return result
                if attempt > 0:
                    logger.debug(
                        f"Unified analysis succeeded on attempt "
                        f"{attempt + 1}"
                    )
                return result

            except Exception as e:
                error_msg = str(e)

                # Check if this is a navigation-related error
                is_navigation_error = (
                    "Execution context was destroyed" in error_msg
                    or "Most likely because of a navigation" in error_msg
                    or "Target page, context or browser has been closed"
                    in error_msg
                )

                if is_navigation_error and attempt < max_retries - 1:
                    logger.debug(
                        f"Navigation error in unified analysis (attempt "
                        f"{attempt + 1}/{max_retries}): {e}. Retrying..."
                    )

                    # Wait a bit for page stability before retrying (
                    # optimized)
                    try:
                        await page.wait_for_load_state(
                            'domcontentloaded',
                            timeout=self._page_stability_timeout,
                        )
                        # Reduced delay for JS context to stabilize
                        import asyncio

                        await asyncio.sleep(0.1)  # Reduced from 0.2s
                    except Exception:
                        # Continue even if wait fails
                        pass

                    continue

                # Non-navigation error or final attempt - log and return
                # empty result
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Error in unified analysis after {max_retries} "
                        f"attempts: {e}"
                    )
                else:
                    logger.warning(
                        f"Non-retryable error in unified analysis: {e}"
                    )

                return {"elements": {}, "metadata": {"elementCount": 0}}

        # Should not reach here, but just in case
        return {"elements": {}, "metadata": {"elementCount": 0}}

    def _convert_analysis_to_rects(
        self, analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Convert analysis data to rect format for visual marking."""
        rects = {}
        elements = analysis_data.get("elements", {})

        for ref, element_data in elements.items():
            coordinates = element_data.get("coordinates", [])
            if coordinates:
                rects[ref] = {
                    "role": element_data.get("role", "generic"),
                    "aria-name": element_data.get("name", ""),
                    "rects": [coordinates[0]],
                }
        return rects

    def _add_set_of_mark(self, image, rects):
        r"""Add visual marks to the image."""
        try:
            from PIL import ImageDraw, ImageFont
        except ImportError:
            logger.warning("PIL not available, returning original image")
            return image

        marked_image = image.copy()
        draw = ImageDraw.Draw(marked_image)

        # Try to get font
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            try:
                font = ImageFont.load_default()
            except (OSError, IOError):
                font = None

        # Color scheme
        colors = {
            "button": "#FF6B6B",
            "link": "#4ECDC4",
            "textbox": "#45B7D1",
            "select": "#96CEB4",
            "checkbox": "#FECA57",
            "radio": "#FF9FF3",
            "default": "#DDA0DD",
        }

        for ref, rect_data in rects.items():
            rects_list = rect_data.get("rects", [])
            role = rect_data.get("role", "generic")
            color = colors.get(role, colors["default"])

            for rect in rects_list:
                x, y = rect.get("x", 0), rect.get("y", 0)
                width, height = rect.get("width", 0), rect.get("height", 0)

                # Draw rectangle outline
                draw.rectangle(
                    [x, y, x + width, y + height], outline=color, width=2
                )

                # Draw reference label
                label_text = ref
                if font:
                    bbox = draw.textbbox((0, 0), label_text, font=font)
                    text_width, text_height = (
                        bbox[2] - bbox[0],
                        bbox[3] - bbox[1],
                    )
                else:
                    text_width, text_height = len(label_text) * 8, 16

                label_x, label_y = max(0, x - 2), max(0, y - text_height - 2)

                # Background and text
                draw.rectangle(
                    [
                        label_x,
                        label_y,
                        label_x + text_width + 4,
                        label_y + text_height + 2,
                    ],
                    fill=color,
                )
                draw.text(
                    (label_x + 2, label_y + 1),
                    label_text,
                    fill="white",
                    font=font,
                )

        return marked_image

    def _format_snapshot_from_analysis(
        self, analysis_data: Dict[str, Any]
    ) -> str:
        r"""Format analysis data into snapshot string."""
        lines = []
        elements = analysis_data.get("elements", {})

        for ref, element_data in elements.items():
            role = element_data.get("role", "generic")
            name = element_data.get("name", "")

            line = f"- {role}"
            if name:
                line += f' "{name}"'

            # Add properties
            props = []
            for prop in ["disabled", "checked", "expanded"]:
                value = element_data.get(prop)
                if value is True:
                    props.append(prop)
                elif value is not None and prop in ["checked", "expanded"]:
                    props.append(f"{prop}={value}")

            if props:
                line += f" {' '.join(props)}"

            line += f" [ref={ref}]"
            lines.append(line)

        return "\n".join(lines)

    async def _get_tab_info_for_output(self) -> Dict[str, Any]:
        r"""Get tab information to include in action outputs."""
        try:
            # Ensure we have the correct singleton session instance first
            session = await self._get_session()

            # Add debug info for tab info retrieval
            logger.debug("Attempting to get tab info from session...")
            tab_info = await session.get_tab_info()
            current_tab_index = await session.get_current_tab_id()

            # Debug log the successful retrieval
            logger.debug(
                f"Successfully retrieved {len(tab_info)} tabs, current: "
                f"{current_tab_index}"
            )

            return {
                "tabs": tab_info,
                "current_tab": current_tab_index,
                "total_tabs": len(tab_info),
            }
        except Exception as e:
            logger.warning(
                f"Failed to get tab info from session: {type(e).__name__}: "
                f"{e}"
            )

            # Try to get actual tab count from session pages directly
            try:
                # Get the correct session instance for fallback
                fallback_session = await self._get_session()

                # Check browser session state
                session_state = {
                    "has_session": fallback_session is not None,
                    "has_pages_attr": hasattr(fallback_session, '_pages'),
                    "pages_count": len(fallback_session._pages)
                    if hasattr(fallback_session, '_pages')
                    else "unknown",
                    "has_page": hasattr(fallback_session, '_page')
                    and fallback_session._page is not None,
                    "session_id": getattr(
                        fallback_session, '_session_id', 'unknown'
                    ),
                }
                logger.debug(f"Browser session state: {session_state}")

                actual_tab_count = 0
                if (
                    hasattr(fallback_session, '_pages')
                    and fallback_session._pages
                ):
                    actual_tab_count = len(fallback_session._pages)
                    # Also try to filter out closed pages
                    try:
                        open_pages = [
                            p
                            for p in fallback_session._pages.values()
                            if not p.is_closed()
                        ]
                        actual_tab_count = len(open_pages)
                        logger.debug(
                            f"Found {actual_tab_count} open tabs out of "
                            f"{len(fallback_session._pages)} total"
                        )
                    except Exception:
                        # Keep the original count if we can't check page
                        # status
                        pass

                if actual_tab_count == 0:
                    # If no pages, check if browser is even initialized
                    if (
                        hasattr(fallback_session, '_page')
                        and fallback_session._page is not None
                    ):
                        actual_tab_count = 1
                        logger.debug(
                            "No pages in list but main page exists, "
                            "assuming "
                            "1 tab"
                        )
                    else:
                        actual_tab_count = 1
                        logger.debug("No pages found, defaulting to 1 tab")

                logger.debug(f"Using fallback tab count: {actual_tab_count}")
                return {
                    "tabs": [],
                    "current_tab": 0,
                    "total_tabs": actual_tab_count,
                }

            except Exception as fallback_error:
                logger.warning(
                    f"Fallback tab count also failed: "
                    f"{type(fallback_error).__name__}: {fallback_error}"
                )
                return {"tabs": [], "current_tab": 0, "total_tabs": 1}

    async def _exec_with_snapshot(
        self,
        action: Dict[str, Any],
        element_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        r"""Execute action and return result with snapshot comparison."""

        # Log action execution start
        action_type = action.get("type", "unknown")
        logger.info(f"Executing action: {action_type}")

        action_start_time = time.time()
        inputs: Dict[str, Any] = {"action": action}
        page_load_time = None

        try:
            # Get before snapshot
            logger.info("Capturing pre-action snapshot...")
            snapshot_start_before = time.time()
            before_snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            before_snapshot_time = time.time() - snapshot_start_before
            logger.info(
                f"Pre-action snapshot captured in "
                f"{before_snapshot_time:.2f}s"
            )

            # Execute action
            logger.info(f"Executing {action_type} action...")
            exec_start = time.time()
            exec_result = await self._session.exec_action(action)
            exec_time = time.time() - exec_start
            logger.info(f"Action {action_type} completed in {exec_time:.2f}s")

            # Parse the detailed result from ActionExecutor
            if isinstance(exec_result, dict):
                result_message = exec_result.get("message", str(exec_result))
                action_details = exec_result.get("details", {})
                success = exec_result.get("success", True)
            else:
                result_message = str(exec_result)
                action_details = {}
                success = True

            # Wait for page stability after action (especially important for
            # click)
            stability_time: float = 0.0
            if action_type in ["click", "type", "select", "enter"]:
                logger.info(
                    f"Waiting for page stability " f"after {action_type}..."
                )
                stability_start = time.time()
                await self._wait_for_page_stability()
                stability_time = time.time() - stability_start
                logger.info(
                    f"Page stability wait "
                    f"completed in "
                    f"{stability_time:.2f}s"
                )
                page_load_time = stability_time

                # Enhanced logging for page loading times
                if self.enable_page_loading_logging and self.log_to_console:
                    logger.info(
                        f"[PAGE LOADING] Page stability for {action_type}: "
                        f"{round(stability_time * 1000, 2)}ms"
                    )

            # Get after snapshot
            logger.info("Capturing post-action snapshot...")
            snapshot_start_after = time.time()
            after_snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            after_snapshot_time = time.time() - snapshot_start_after
            logger.info(
                f"Post-action snapshot "
                f"captured in {after_snapshot_time:.2f}s"
            )

            # Check for snapshot quality and log warnings
            if before_snapshot == after_snapshot:
                snapshot = "snapshot not changed"
                logger.debug("Page snapshot unchanged after action")
            else:
                snapshot = after_snapshot
                # Check if snapshot is empty or problematic
                if "<empty>" in after_snapshot:
                    logger.warning(
                        f"Action {action_type} resulted "
                        f"in empty snapshot - "
                        f"page may still be loading"
                    )
                elif len(after_snapshot.strip()) < 50:
                    logger.warning(
                        f"Action {action_type} resulted "
                        f"in very short snapshot:"
                        f" {len(after_snapshot)} chars"
                    )
                else:
                    logger.debug(
                        f"Action {action_type} resulted "
                        f"in updated snapshot: "
                        f"{len(after_snapshot)} chars"
                    )

            # Get tab information for output
            tab_info = await self._get_tab_info_for_output()

            # Create comprehensive output for logging
            execution_time = time.time() - action_start_time
            total_snapshot_time = before_snapshot_time + after_snapshot_time
            outputs = {
                "result": result_message,
                "snapshot": snapshot,
                "success": success,
                "action_details": action_details,
                "execution_stats": {
                    "exec_time_ms": round(exec_time * 1000, 2),
                    "stability_time_ms": round(stability_time * 1000, 2)
                    if stability_time > 0
                    else None,
                    "snapshot_time_ms": round(total_snapshot_time * 1000, 2),
                    "total_time_ms": round(execution_time * 1000, 2),
                },
                **tab_info,  # Include tab information
            }

            # If snapshot is unchanged after click, add element details to
            # log
            if (
                snapshot == "snapshot not changed"
                and action_type == "click"
                and element_details
            ):
                logger.debug(
                    "Snapshot unchanged after click. "
                    "Adding element details to log."
                )
                outputs["clicked_element_tag"] = element_details.get(
                    "tagName", "N/A"
                )
                outputs["clicked_element_content"] = element_details.get(
                    "name", ""
                )
                outputs["clicked_element_type"] = element_details.get(
                    "role", "generic"
                )

            # Log the action with all details
            await self._log_action(
                action_name=f"_exec_with_snapshot_{action_type}",
                inputs=inputs,
                outputs=outputs,
                execution_time=execution_time,
                page_load_time=page_load_time,
            )

            return {"result": result_message, "snapshot": snapshot}

        except Exception as e:
            execution_time = time.time() - action_start_time
            error_msg = f"{type(e).__name__}: {e!s}"

            # Log error
            await self._log_action(
                action_name=f"_exec_with_snapshot_{action_type}",
                inputs=inputs,
                outputs=None,
                execution_time=execution_time,
                page_load_time=page_load_time,
                error=error_msg,
            )

            raise

    async def _extract_links_by_refs(
        self, snapshot: str, page, refs: List[str]
    ) -> List[Dict[str, str]]:
        r"""Extract multiple links by their reference IDs."""
        import re

        found_links = []
        ref_set = set(refs)
        lines = snapshot.split('\n')

        for line in lines:
            link_match = re.search(
                r'- link\s+"([^"]+)"\s+\[ref=([^\]]+)\]', line
            )
            if link_match and link_match.group(2) in ref_set:
                text, found_ref = link_match.groups()
                try:
                    url = await self._get_link_url_by_ref(page, found_ref)
                    found_links.append(
                        {"text": text, "ref": found_ref, "url": url or ""}
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get URL for ref {found_ref}: {e}"
                    )
                    found_links.append(
                        {"text": text, "ref": found_ref, "url": ""}
                    )

        return found_links

    async def _get_link_url_by_ref(self, page, ref: str) -> str:
        r"""Get URL of a link element by reference ID."""
        try:
            element = await page.query_selector(f'[aria-ref="{ref}"]')
            if element:
                href = await element.get_attribute('href')
                if href:
                    from urllib.parse import urljoin

                    return urljoin(page.url, href)
            return ""
        except Exception as e:
            logger.warning(f"Failed to get URL for ref {ref}: {e}")
            return ""

    def _ensure_agent(self) -> PlaywrightLLMAgent:
        r"""Create PlaywrightLLMAgent on first use."""
        if self._web_agent_model is None:
            raise RuntimeError(
                "web_agent_model required for high-level task planning"
            )

        if self._playwright_agent is None:
            self._playwright_agent = PlaywrightLLMAgent(
                headless=self._headless,
                user_data_dir=self._user_data_dir,
                model_backend=self._web_agent_model,
            )
        return self._playwright_agent

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
        # Add logging if enabled
        action_start = time.time()
        inputs: Dict[str, Any] = {}  # No input parameters for agents

        logger.info("Starting browser session...")

        browser_start = time.time()
        await self._session.ensure_browser()
        browser_time = time.time() - browser_start
        logger.info(f"Browser session started in {browser_time:.2f}s")

        try:
            # Always use the configured default start URL
            start_url = self._default_start_url
            logger.info(f"Navigating to configured default page: {start_url}")

            # Use visit_page without creating a new tab
            result = await self.browser_visit_page(url=start_url)

            # Log success
            if self.enable_action_logging or self.enable_timing_logging:
                execution_time = time.time() - action_start
                await self._log_action(
                    action_name="browser_open",
                    inputs=inputs,
                    outputs={
                        "result": "Browser opened and navigated to "
                        "default page."
                    },
                    execution_time=execution_time,
                )

            return result

        except Exception as e:
            # Log error
            if self.enable_action_logging or self.enable_timing_logging:
                execution_time = time.time() - action_start
                await self._log_action(
                    action_name="browser_open",
                    inputs=inputs,
                    outputs=None,
                    execution_time=execution_time,
                    error=f"{type(e).__name__}: {e!s}",
                )
            raise

    @action_logger
    async def browser_close(self) -> str:
        r"""Closes the browser session, releasing all resources.

        This should be called at the end of a task for cleanup.

        Returns:
            str: A confirmation message.
        """
        if self._playwright_agent is not None:
            try:
                await self._playwright_agent.close()
            except Exception:
                pass
            self._playwright_agent = None

        await self._session.close()
        return "Browser session closed."

    @action_logger
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
        if not url or not isinstance(url, str):
            return {
                "result": "Error: 'url' must be a non-empty string",
                "snapshot": "",
                "tabs": [],
                "current_tab": 0,
                "total_tabs": 1,
            }

        if '://' not in url:
            url = f'https://{url}'

        await self._ensure_browser()
        session = await self._get_session()
        nav_result = ""

        # By default, we want to create a new tab.
        should_create_new_tab = True
        try:
            # If the browser has just started with a single "about:blank"
            # tab,
            # use that tab instead of creating a new one.
            tab_info_data = await self._get_tab_info_for_output()
            tabs = tab_info_data.get("tabs", [])
            if len(tabs) == 1 and tabs[0].get("url") == "about:blank":
                logger.info(
                    "Found single blank tab, navigating in current tab "
                    "instead of creating a new one."
                )
                should_create_new_tab = False
        except Exception as e:
            logger.warning(
                "Could not get tab info to check for blank tab, "
                f"proceeding with default behavior (new tab). Error: {e}"
            )

        if should_create_new_tab:
            logger.info(f"Creating new tab and navigating to URL: {url}")
            try:
                new_tab_id = await session.create_new_tab(url)
                await session.switch_to_tab(new_tab_id)
                nav_result = f"Visited {url} in new tab {new_tab_id}"
            except Exception as e:
                logger.error(f"Failed to create new tab and navigate: {e}")
                nav_result = f"Error creating new tab: {e}"
        else:
            logger.info(f"Navigating to URL in current tab: {url}")
            nav_result = await session.visit(url)

        # Get snapshot
        snapshot = ""
        try:
            snapshot = await session.get_snapshot(
                force_refresh=True, diff_only=False
            )
        except Exception as e:
            logger.warning(f"Failed to capture snapshot: {e}")

        # Get tab information
        tab_info = await self._get_tab_info_for_output()

        return {"result": nav_result, "snapshot": snapshot, **tab_info}

    @action_logger
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
        page = await self._require_page()

        try:
            logger.info("Navigating back in browser history...")
            nav_start = time.time()
            await page.go_back(
                wait_until="domcontentloaded", timeout=self._navigation_timeout
            )
            nav_time = time.time() - nav_start
            logger.info(f"Back navigation completed in {nav_time:.2f}s")

            # Minimal wait for page stability (back navigation is usually
            # fast)
            import asyncio

            await asyncio.sleep(0.2)

            # Get snapshot
            logger.info("Capturing page snapshot after back navigation...")
            snapshot_start = time.time()
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Back navigation snapshot captured in {snapshot_time:.2f}s"
            )

            # Get tab information
            tab_info = await self._get_tab_info_for_output()

            return {
                "result": "Back navigation successful.",
                "snapshot": snapshot,
                **tab_info,
            }

        except Exception as e:
            logger.warning(f"Back navigation failed: {e}")
            # Get current snapshot even if navigation failed
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": f"Back navigation failed: {e!s}",
                "snapshot": snapshot,
                **tab_info,
            }

    @action_logger
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
        page = await self._require_page()

        try:
            logger.info("Navigating forward in browser history...")
            nav_start = time.time()
            await page.go_forward(
                wait_until="domcontentloaded", timeout=self._navigation_timeout
            )
            nav_time = time.time() - nav_start
            logger.info(f"Forward navigation completed in {nav_time:.2f}s")

            # Minimal wait for page stability (forward navigation is usually
            # fast)
            import asyncio

            await asyncio.sleep(0.2)

            # Get snapshot
            logger.info("Capturing page snapshot after forward navigation...")
            snapshot_start = time.time()
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Forward navigation snapshot captured in "
                f"{snapshot_time:.2f}s"
            )

            # Get tab information
            tab_info = await self._get_tab_info_for_output()

            return {
                "result": "Forward navigation successful.",
                "snapshot": snapshot,
                **tab_info,
            }

        except Exception as e:
            logger.warning(f"Forward navigation failed: {e}")
            # Get current snapshot even if navigation failed
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": f"Forward navigation failed: {e!s}",
                "snapshot": snapshot,
                **tab_info,
            }

    @action_logger
    async def browser_get_page_snapshot(self) -> str:
        r"""Gets a textual snapshot of the page's interactive elements.

        The snapshot lists elements like buttons, links, and inputs,
        each with
        a unique `ref` ID. This ID is used by other tools (e.g., `click`,
        `type`) to interact with a specific element. This tool provides no
        visual information.

        Returns:
            str: A formatted string representing the interactive elements and
                their `ref` IDs. For example:
                '- link "Sign In" [ref=1]'
                '- textbox "Username" [ref=2]'
        """
        logger.info("Capturing page snapshot")

        analysis_start = time.time()
        analysis_data = await self._get_unified_analysis()
        analysis_time = time.time() - analysis_start
        logger.info(
            f"Page snapshot analysis " f"completed in {analysis_time:.2f}s"
        )

        snapshot_text = analysis_data.get("snapshotText", "")
        return (
            snapshot_text
            if snapshot_text
            else self._format_snapshot_from_analysis(analysis_data)
        )

    @dependencies_required('PIL')
    @action_logger
    async def browser_get_som_screenshot(
        self,
        read_image: bool = True,
        instruction: Optional[str] = None,
    ):
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
            str: A summary message including the file path of the saved
                screenshot, e.g., "Visual webpage screenshot captured with 42
                interactive elements and saved to /path/to/screenshot.png",
                and optionally the agent's analysis if `read_image` is
                `True`.
        """
        from PIL import Image

        os.makedirs(self._cache_dir, exist_ok=True)
        # Get screenshot and analysis
        page = await self._require_page()

        # Log screenshot timeout start
        logger.info(
            f"Starting screenshot capture"
            f"with timeout: {self._screenshot_timeout}ms"
        )

        start_time = time.time()
        image_data = await page.screenshot(timeout=self._screenshot_timeout)
        screenshot_time = time.time() - start_time

        logger.info(f"Screenshot capture completed in {screenshot_time:.2f}s")
        image = Image.open(io.BytesIO(image_data))

        # Log unified analysis start
        logger.info("Starting unified page analysis...")
        analysis_start_time = time.time()
        analysis_data = await self._get_unified_analysis()
        analysis_time = time.time() - analysis_start_time
        logger.info(f"Unified page analysis completed in {analysis_time:.2f}s")

        # Log image processing
        logger.info("Processing visual marks on screenshot...")
        mark_start_time = time.time()
        rects = self._convert_analysis_to_rects(analysis_data)
        marked_image = self._add_set_of_mark(image, rects)
        mark_time = time.time() - mark_start_time
        logger.info(f"Visual marks processing completed in {mark_time:.2f}s")

        # Save screenshot to cache directory
        parsed_url = urllib.parse.urlparse(page.url)
        url_name = sanitize_filename(str(parsed_url.path), max_length=241)
        timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
        file_path = os.path.join(
            self._cache_dir, f"{url_name}_{timestamp}_som.png"
        )
        marked_image.save(file_path, "PNG")

        text_result = (
            f"Visual webpage screenshot captured with {len(rects)} "
            f"interactive elements."
        )

        # Analyze image if requested and agent is registered
        if read_image and file_path:
            if self.agent is None:
                logger.error(
                    "Cannot analyze screenshot: No agent registered. "
                    "Please pass this toolkit to ChatAgent via "
                    "toolkits_to_register_agent parameter."
                )
                text_result += (
                    " Error: No agent registered for image analysis. "
                    "Please pass this toolkit to ChatAgent via "
                    "toolkits_to_register_agent parameter."
                )
            else:
                try:
                    # Load the image and create a message
                    from camel.messages import BaseMessage

                    img = Image.open(file_path)
                    inst = instruction if instruction is not None else ""
                    message = BaseMessage.make_user_message(
                        role_name="User",
                        content=inst,
                        image_list=[img],
                    )

                    # Get agent's analysis
                    await self.agent.astep(message)
                except Exception as e:
                    logger.error(f"Error analyzing screenshot: {e}")
                    text_result += f". Error analyzing screenshot: {e}"

        return text_result

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
        self._validate_ref(ref, "click")

        analysis = await self._get_unified_analysis()
        elements = analysis.get("elements", {})
        if ref not in elements:
            logger.error(f"Error: Element reference '{ref}' not found. ")
            # Added snapshot to give more context on failure
            snapshot = self._format_snapshot_from_analysis(analysis)
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": f"Error: Element reference '{ref}' not found. ",
                "snapshot": snapshot,
                **tab_info,
            }

        element_details = elements.get(ref)
        action = {"type": "click", "ref": ref}
        result = await self._exec_with_snapshot(
            action, element_details=element_details
        )

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

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
        self._validate_ref(ref, "type")
        await self._get_unified_analysis()  # Ensure aria-ref attributes

        action = {"type": "type", "ref": ref, "text": text}
        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

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
        self._validate_ref(ref, "select")
        await self._get_unified_analysis()

        action = {"type": "select", "ref": ref, "value": value}
        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    async def browser_scroll(
        self, *, direction: str, amount: int
    ) -> Dict[str, Any]:
        r"""Scrolls the current page window.

        Args:
            direction (str): The direction to scroll: 'up' or 'down'.
            amount (int): The number of pixels to scroll.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A snapshot of the page after scrolling.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        if direction not in ("up", "down"):
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": "Error: direction must be 'up' or 'down'",
                "snapshot": "",
                **tab_info,
            }

        action = {"type": "scroll", "direction": direction, "amount": amount}
        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

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
        # Always press Enter on the currently focused element
        action = {"type": "enter"}

        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    @action_logger
    async def browser_mouse_control(
        self, *, control: str, x: float, y: float
    ) -> Dict[str, Any]:
        r"""Control the mouse to interact with browser with x, y coordinates

        Args:
            control (str): The action to perform: 'click', 'right_click'
            or 'dblclick'.
            x (float): x-coordinate for the control action.
            y (float): y-coordinate for the control action.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A new page snapshot.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        if control not in ("click", "right_click", "dblclick"):
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": "Error: supported control actions are "
                "'click' or 'dblclick'",
                "snapshot": "",
                **tab_info,
            }

        action = {"type": "mouse_control", "control": control, "x": x, "y": y}

        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    @action_logger
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
        # Validate refs
        self._validate_ref(from_ref, "drag source")
        self._validate_ref(to_ref, "drag target")

        # Get element analysis to find coordinates
        analysis = await self._get_unified_analysis()
        elements = analysis.get("elements", {})

        if from_ref not in elements:
            logger.error(
                f"Error: Source element reference '{from_ref}' not found."
            )
            snapshot = self._format_snapshot_from_analysis(analysis)
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": (
                    f"Error: Source element reference '{from_ref}' not found."
                ),
                "snapshot": snapshot,
                **tab_info,
            }

        if to_ref not in elements:
            logger.error(
                f"Error: Target element reference '{to_ref}' not found."
            )
            snapshot = self._format_snapshot_from_analysis(analysis)
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": (
                    f"Error: Target element reference '{to_ref}' not found."
                ),
                "snapshot": snapshot,
                **tab_info,
            }

        action = {
            "type": "mouse_drag",
            "from_ref": from_ref,
            "to_ref": to_ref,
        }

        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    @action_logger
    async def browser_press_key(self, *, keys: List[str]) -> Dict[str, Any]:
        r"""Press key and key combinations.
        Supports single key press or combination of keys by concatenating
        them with '+' separator.

        Args:
            keys (List[str]): key or list of keys.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Confirmation of the action.
                - "snapshot" (str): A new page snapshot.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        if not isinstance(keys, list) or not all(
            isinstance(item, str) for item in keys
        ):
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": "Error: Expected keys as a list of strings.",
                "snapshot": "",
                **tab_info,
            }
        action = {"type": "press_key", "keys": keys}

        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    @action_logger
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
            await asyncio.to_thread(input, ">>> Press Enter to resume <<<\n")

        try:
            if timeout_sec is not None:
                logger.info(
                    f"Waiting for user input with timeout: {timeout_sec}s"
                )
                start_time = time.time()
                await asyncio.wait_for(_await_enter(), timeout=timeout_sec)
                wait_time = time.time() - start_time
                logger.info(f"User input received after {wait_time:.2f}s")
                result_msg = "User resumed."
            else:
                logger.info("Waiting for user " "input (no timeout)")
                start_time = time.time()
                await _await_enter()
                wait_time = time.time() - start_time
                logger.info(f"User input received " f"after {wait_time:.2f}s")
                result_msg = "User resumed."
        except asyncio.TimeoutError:
            wait_time = timeout_sec or 0.0
            logger.info(
                f"User input timeout reached "
                f"after {wait_time}s, auto-resuming"
            )
            result_msg = f"Timeout {timeout_sec}s reached, auto-resumed."

        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        tab_info = await self._get_tab_info_for_output()

        return {"result": result_msg, "snapshot": snapshot, **tab_info}

    @action_logger
    async def browser_get_page_links(
        self, *, ref: List[str]
    ) -> Dict[str, Any]:
        r"""Gets the destination URLs for a list of link elements.

        This is useful to know where a link goes before clicking it.

        Args:
            ref (List[str]): A list of `ref` IDs for link elements, obtained
                from a page snapshot.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "links" (List[Dict]): A list of found links, where each
                  link has "text", "ref", and "url" keys.
        """
        if not ref or not isinstance(ref, list):
            return {"links": []}

        for r in ref:
            if not r or not isinstance(r, str):
                return {"links": []}

        page = await self._require_page()
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        links = await self._extract_links_by_refs(snapshot, page, ref)

        return {"links": links}

    @action_logger
    async def browser_solve_task(
        self, task_prompt: str, start_url: str, max_steps: int = 15
    ) -> str:
        r"""Delegates a complex, high-level task to a specialized web agent.

        Use this for multi-step tasks that can be described in a single
        prompt
        (e.g., "log into my account and check for new messages"). The agent
        will autonomously perform the necessary browser actions.

        NOTE: This is a high-level action; for simple interactions, use tools
        like `click` and `type`. `web_agent_model` must be provided during
        toolkit initialization.

        Args:
            task_prompt (str): A natural language description of the task.
            start_url (str): The URL to start the task from. This should be a
                valid and existing URL, as agents may generate non-existent
                ones.
            max_steps (int): The maximum number of steps the agent can take.

        Returns:
            str: A summary message indicating the task has finished.
        """
        agent = self._ensure_agent()
        await agent.navigate(start_url)
        await agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

    @action_logger
    async def browser_console_view(self) -> Dict[str, Any]:
        r"""View current page console logs.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - console_messages (List[Dict]) : collection of logs from the
                browser console
        """
        try:
            logs = await self._session.get_console_logs()
            # make output JSON serializable
            return {"console_messages": list(logs)}
        except Exception as e:
            logger.warning(f"Failed to retrieve logs: {e}")
            return {"console_messages": []}

    async def browser_console_exec(self, code: str) -> Dict[str, Any]:
        r"""Execute javascript code in the console of the current page and get
        results.

        Args:
            code (str): JavaScript code for execution.

        Returns:
            Dict[str, Any]: A dictionary with the result of the action:
                - "result" (str): Result of the action.
                - "console_output" (List[str]): Console log outputs during
                  execution.
                - "snapshot" (str): A new page snapshot.
                - "tabs" (List[Dict]): Information about all open tabs.
                - "current_tab" (int): Index of the active tab.
                - "total_tabs" (int): Total number of open tabs.
        """
        page = await self._require_page()

        try:
            logger.info("Executing JavaScript code in browser console.")
            exec_start = time.time()

            # Wrap the code to capture console.log output and handle
            # expressions
            wrapped_code = (
                """
                (function() {
                    const _logs = [];
                    const originalLog = console.log;
                    console.log = function(...args) {
                        _logs.push(args.map(arg => {
                            try {
                                return typeof arg === 'object' ?
                                    JSON.stringify(arg) : String(arg);
                            } catch (e) {
                                return String(arg);
                            }
                        }).join(' '));
                        originalLog.apply(console, args);
                    };
                    
                    let result;
                    try {
                        // First try to evaluate as an expression
                        // (like browser console)
                        result = eval("""
                + repr(code)
                + """);
                    } catch (e) {
                        // If that fails, execute as statements
                        try {
                            result = (function() { """
                + code
                + """ })();
                        } catch (error) {
                            console.log = originalLog;
                            throw error;
                        }
                    }
                    
                    console.log = originalLog;
                    return { result, logs: _logs };
                })()
            """
            )

            eval_result = await page.evaluate(wrapped_code)
            result = eval_result.get('result')
            console_logs = eval_result.get('logs', [])

            exec_time = time.time() - exec_start
            logger.info(f"Code execution completed in {exec_time:.2f}s.")

            import asyncio
            import json

            await asyncio.sleep(0.2)

            # Get snapshot
            logger.info("Capturing page snapshot after code execution.")
            snapshot_start = time.time()
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Code execution snapshot captured in " f"{snapshot_time:.2f}s"
            )

            # Get tab information
            tab_info = await self._get_tab_info_for_output()

            # Properly serialize the result
            try:
                result_str = json.dumps(result, indent=2)
            except (TypeError, ValueError):
                result_str = str(result)

            return {
                "result": f"Code execution result: {result_str}",
                "console_output": console_logs,
                "snapshot": snapshot,
                **tab_info,
            }

        except Exception as e:
            logger.warning(f"Code execution failed: {e}")
            # Get tab information for error case
            try:
                tab_info = await self._get_tab_info_for_output()
            except Exception:
                tab_info = {
                    "tabs": [],
                    "current_tab": 0,
                    "total_tabs": 0,
                }

            return {
                "result": f"Code execution failed: {e}",
                "console_output": [],
                "snapshot": "",
                **tab_info,
            }

    def get_log_summary(self) -> Dict[str, Any]:
        r"""Get a summary of logged actions."""
        if not self.log_buffer:
            return {"total_actions": 0, "summary": "No actions logged"}

        total_actions = len(self.log_buffer)
        total_execution_time = sum(
            entry.get("execution_time_ms", 0) for entry in self.log_buffer
        )
        total_page_load_time = sum(
            entry.get("page_load_time_ms", 0)
            for entry in self.log_buffer
            if "page_load_time_ms" in entry
        )

        action_counts: Dict[str, int] = {}
        error_count = 0

        for entry in self.log_buffer:
            action = entry["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
            if "error" in entry:
                error_count += 1

        return {
            "total_actions": total_actions,
            "total_execution_time_ms": round(total_execution_time, 2),
            "total_page_load_time_ms": round(total_page_load_time, 2),
            "action_counts": action_counts,
            "error_count": error_count,
            "success_rate": round(
                (total_actions - error_count) / total_actions * 100, 2
            )
            if total_actions > 0
            else 0,
        }

    def clear_logs(self) -> None:
        r"""Clear the log buffer."""
        self.log_buffer.clear()
        logger.info("Log buffer cleared")

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

    @action_logger
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
        await self._ensure_browser()
        session = await self._get_session()

        success = await session.switch_to_tab(tab_id)

        if success:
            snapshot = await session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            tab_info = await self._get_tab_info_for_output()

            result = {
                "result": f"Successfully switched to tab {tab_id}",
                "snapshot": snapshot,
                **tab_info,
            }
        else:
            tab_info = await self._get_tab_info_for_output()
            result = {
                "result": f"Failed to switch to tab {tab_id}. Tab may not "
                f"exist.",
                "snapshot": "",
                **tab_info,
            }

        return result

    @action_logger
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
        await self._ensure_browser()
        session = await self._get_session()

        success = await session.close_tab(tab_id)

        if success:
            # Get current state after closing the tab
            try:
                snapshot = await session.get_snapshot(
                    force_refresh=True, diff_only=False
                )
            except Exception:
                snapshot = ""  # No active tab

            tab_info = await self._get_tab_info_for_output()

            result = {
                "result": f"Successfully closed tab {tab_id}",
                "snapshot": snapshot,
                **tab_info,
            }
        else:
            tab_info = await self._get_tab_info_for_output()
            result = {
                "result": f"Failed to close tab {tab_id}. Tab may not "
                f"exist.",
                "snapshot": "",
                **tab_info,
            }

        return result

    @action_logger
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
        await self._ensure_browser()
        return await self._get_tab_info_for_output()

    def get_tools(self) -> List[FunctionTool]:
        r"""Get available function tools
        based on enabled_tools configuration."""
        # Map tool names to their corresponding methods
        tool_map = {
            "browser_open": self.browser_open,
            "browser_close": self.browser_close,
            "browser_visit_page": self.browser_visit_page,
            "browser_back": self.browser_back,
            "browser_forward": self.browser_forward,
            "browser_get_page_snapshot": self.browser_get_page_snapshot,
            "browser_get_som_screenshot": self.browser_get_som_screenshot,
            "browser_get_page_links": self.browser_get_page_links,
            "browser_click": self.browser_click,
            "browser_type": self.browser_type,
            "browser_select": self.browser_select,
            "browser_scroll": self.browser_scroll,
            "browser_enter": self.browser_enter,
            "browser_mouse_control": self.browser_mouse_control,
            "browser_mouse_drag": self.browser_mouse_drag,
            "browser_press_key": self.browser_press_key,
            "browser_wait_user": self.browser_wait_user,
            "browser_solve_task": self.browser_solve_task,
            "browser_switch_tab": self.browser_switch_tab,
            "browser_close_tab": self.browser_close_tab,
            "browser_get_tab_info": self.browser_get_tab_info,
            "browser_console_view": self.browser_console_view,
            "browser_console_exec": self.browser_console_exec,
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
