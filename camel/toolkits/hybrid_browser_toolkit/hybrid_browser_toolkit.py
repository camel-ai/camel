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

import base64
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
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import sanitize_filename
from camel.utils.commons import dependencies_required
from camel.utils.tool_result import ToolResult

from .agent import PlaywrightLLMAgent
from .browser_session import HybridBrowserSession

logger = get_logger(__name__)


class HybridBrowserToolkit(BaseToolkit):
    r"""A hybrid browser toolkit that combines non-visual, DOM-based browser
    automation with visual, screenshot-based capabilities.

    This toolkit exposes a set of actions as CAMEL FunctionTools for agents
    to interact with web pages. It can operate in headless mode and supports
    both programmatic control of browser actions (like clicking and typing)
    and visual analysis of the page layout through screenshots with marked
    interactive elements.
    """

    # Configuration constants
    DEFAULT_SCREENSHOT_TIMEOUT = 60000  # 60 seconds for screenshots
    PAGE_STABILITY_TIMEOUT = 3000  # 3 seconds for DOM stability
    NETWORK_IDLE_TIMEOUT = 2000  # 2 seconds for network idle

    # Default tool list - core browser functionality
    DEFAULT_TOOLS: ClassVar[List[str]] = [
        "open_browser",
        "close_browser",
        "visit_page",
        "back",
        "forward",
        "click",
        "type",
        "switch_tab",
    ]

    # All available tools
    ALL_TOOLS: ClassVar[List[str]] = [
        "open_browser",
        "close_browser",
        "visit_page",
        "back",
        "forward",
        "get_page_snapshot",
        "get_som_screenshot",
        "get_page_links",
        "click",
        "type",
        "select",
        "scroll",
        "enter",
        "wait_user",
        "solve_task",
        "switch_tab",
        "close_tab",
        "get_tab_info",
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
    ) -> None:
        r"""Initialize the HybridBrowserToolkit.

        Args:
            headless (bool): Whether to run the browser in headless mode.
                Defaults to `True`.
            user_data_dir (Optional[str]): Path to a directory for storing
                browser data like cookies and local storage. Useful for
                maintaining sessions across runs. Defaults to `None` (a
                temporary directory is used).
            stealth (bool): Whether to run the browser in stealth mode to avoid
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
            enabled_tools (Optional[List[str]]): List of tool names to enable.
                If None, uses DEFAULT_TOOLS. Available tools: open_browser,
                close_browser, visit_page, back, forward, get_page_snapshot,
                get_som_screenshot, get_page_links, click, type, select,
                scroll, enter, wait_user, solve_task.
                Defaults to `None`.
            browser_log_to_file (bool): Whether to save detailed browser
            action logs to file.
                When enabled, logs action inputs/outputs, execution times,
                and page loading times.
                Logs are saved to an auto-generated timestamped file.
                Defaults to `False`.
            session_id (Optional[str]): A unique identifier for this browser
                session. When multiple HybridBrowserToolkit instances are used
                concurrently, different session IDs prevent them from sharing
                the same browser session and causing conflicts. If None, a
                default session will be used. Defaults to `None`.
            default_start_url (str): The default URL to navigate to when
                open_browser() is called without a start_url parameter or with
                None. Defaults to `"https://google.com/"`.
        """
        super().__init__()
        self._headless = headless
        self._user_data_dir = user_data_dir
        self.web_agent_model = web_agent_model
        self.cache_dir = cache_dir
        self.default_start_url = default_start_url
        os.makedirs(self.cache_dir, exist_ok=True)

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
            log_dir = "browser_log"
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
        )
        # Use the session directly - singleton logic is handled in
        # ensure_browser
        self._session = temp_session
        self._agent: Optional[PlaywrightLLMAgent] = None
        self._unified_script = self._load_unified_analyzer()

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
                            asyncio.wait_for(self.close_browser(), timeout=2.0)
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
            elif isinstance(outputs, ToolResult):
                log_entry["outputs"] = {
                    "text": outputs.text,
                    "images": outputs.images,
                }
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
                log_msg += f" | Execution: {log_entry['execution_time_ms']}ms"
            if page_load_time is not None and self.enable_page_loading_logging:
                log_msg += f" | Page Load: {log_entry['page_load_time_ms']}ms"
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
        updates.
        """
        page = await self._require_page()
        import asyncio

        try:
            # Wait for DOM content to be loaded
            await page.wait_for_load_state(
                'domcontentloaded', timeout=self.PAGE_STABILITY_TIMEOUT
            )
            logger.debug("DOM content loaded")

            # Try to wait for network idle (important for AJAX/SPA)
            try:
                await page.wait_for_load_state(
                    'networkidle', timeout=self.NETWORK_IDLE_TIMEOUT
                )
                logger.debug("Network idle achieved")
            except Exception:
                logger.debug("Network idle timeout - continuing anyway")

            # Additional small delay for JavaScript execution
            await asyncio.sleep(0.5)
            logger.debug("Page stability wait completed")

        except Exception as e:
            logger.debug(
                f"Page stability wait failed: {e} - continuing anyway"
            )

    async def _get_unified_analysis(self) -> Dict[str, Any]:
        r"""Get unified analysis data from the page."""
        page = await self._require_page()
        try:
            if not self._unified_script:
                logger.error("Unified analyzer script not loaded")
                return {"elements": {}, "metadata": {"elementCount": 0}}

            result = await page.evaluate(self._unified_script)

            if not isinstance(result, dict):
                logger.warning(f"Invalid result type: {type(result)}")
                return {"elements": {}, "metadata": {"elementCount": 0}}

            return result
        except Exception as e:
            logger.warning(f"Error in unified analysis: {e}")
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
            current_tab_index = await session.get_current_tab_index()

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
                f"Failed to get tab info from session: {type(e).__name__}: {e}"
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
                            for p in fallback_session._pages
                            if not p.is_closed()
                        ]
                        actual_tab_count = len(open_pages)
                        logger.debug(
                            f"Found {actual_tab_count} open tabs out of "
                            f"{len(fallback_session._pages)} total"
                        )
                    except Exception:
                        # Keep the original count if we can't check page status
                        pass

                if actual_tab_count == 0:
                    # If no pages, check if browser is even initialized
                    if (
                        hasattr(fallback_session, '_page')
                        and fallback_session._page is not None
                    ):
                        actual_tab_count = 1
                        logger.debug(
                            "No pages in list but main page exists, assuming "
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
            snapshot_start = time.time()
            before_snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Pre-action snapshot captured in {snapshot_time:.2f}s"
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
            snapshot_start = time.time()
            after_snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Post-action snapshot " f"captured in {snapshot_time:.2f}s"
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
                    "total_time_ms": round(execution_time * 1000, 2),
                },
                **tab_info,  # Include tab information
            }

            # If snapshot is unchanged after click, add element details to log
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
        if self.web_agent_model is None:
            raise RuntimeError(
                "web_agent_model required for high-level task planning"
            )

        if self._agent is None:
            self._agent = PlaywrightLLMAgent(
                headless=self._headless,
                user_data_dir=self._user_data_dir,
                model_backend=self.web_agent_model,
            )
        return self._agent

    # Public API Methods

    async def open_browser(self) -> Dict[str, Any]:
        r"""Launches a new browser session and navigates to the configured
        default page.

        This method initializes the underlying browser instance and
        automatically
        navigates to the default start URL that was configured during toolkit
        initialization. Agents cannot specify a custom URL - they must use the
        visit_page tool for navigation to other URLs.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A string confirming that the browser session has
                  started and the default page has been loaded.
                - "snapshot": A textual representation of the current page's
                  interactive elements. This snapshot is crucial for
                  identifying elements for subsequent actions.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
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
            start_url = self.default_start_url
            logger.info(f"Navigating to configured default page: {start_url}")

            result = await self.visit_page(start_url)

            # Log success
            if self.enable_action_logging or self.enable_timing_logging:
                execution_time = time.time() - action_start
                await self._log_action(
                    action_name="open_browser",
                    inputs=inputs,
                    outputs={
                        "result": "Browser opened and navigated to default "
                        "page."
                    },
                    execution_time=execution_time,
                )

            return result

        except Exception as e:
            # Log error
            if self.enable_action_logging or self.enable_timing_logging:
                execution_time = time.time() - action_start
                await self._log_action(
                    action_name="open_browser",
                    inputs=inputs,
                    outputs=None,
                    execution_time=execution_time,
                    error=f"{type(e).__name__}: {e!s}",
                )
            raise

    @action_logger
    async def close_browser(self) -> str:
        r"""Closes the current browser session and releases all associated
        resources.

        This should be called at the end of a web automation task to ensure a
        clean shutdown of the browser instance.

        Returns:
            str: A confirmation message indicating the session is closed.
        """
        if self._agent is not None:
            try:
                await self._agent.close()
            except Exception:
                pass
            self._agent = None

        await self._session.close()
        return "Browser session closed."

    @action_logger
    async def visit_page(self, url: str) -> Dict[str, Any]:
        r"""Navigates the current browser page to a specified URL.

        Args:
            url (str): The web address to load in the browser. Must be a
                valid URL.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating the outcome of the navigation,
                  e.g., "Navigation successful.".
                - "snapshot": A new textual snapshot of the page's interactive
                  elements after the new page has loaded.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
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

        logger.info(f"Navigating to URL: {url}")

        # Navigate to page
        nav_start = time.time()
        nav_result = await self._session.visit(url)
        nav_time = time.time() - nav_start
        logger.info(f"Page navigation completed in {nav_time:.2f}s")

        # Get snapshot
        logger.info("Capturing page snapshot after navigation...")
        snapshot_start = time.time()
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        snapshot_time = time.time() - snapshot_start
        logger.info(f"Navigation snapshot captured in {snapshot_time:.2f}s")

        # Get tab information
        tab_info = await self._get_tab_info_for_output()

        return {"result": nav_result, "snapshot": snapshot, **tab_info}

    @action_logger
    async def back(self) -> Dict[str, Any]:
        r"""Navigates the browser back to the previous page in history.

        This function simulates clicking the browser's back button, taking
        you to the previously visited page if one exists in the browser
        history.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating the outcome of the back
                  navigation, e.g., "Back navigation successful." or an error
                  message if no previous page exists.
                - "snapshot": A new textual snapshot of the page after
                  navigation. If the snapshot is unchanged, it will be the
                  string "snapshot not changed".
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        page = await self._require_page()

        try:
            logger.info("Navigating back in browser history...")
            nav_start = time.time()
            await page.go_back(wait_until="domcontentloaded", timeout=30000)
            nav_time = time.time() - nav_start
            logger.info(f"Back navigation completed in {nav_time:.2f}s")

            # Wait for page stability
            await self._wait_for_page_stability()

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
    async def forward(self) -> Dict[str, Any]:
        r"""Navigates the browser forward to the next page in history.

        This function simulates clicking the browser's forward button, taking
        you to the next page in the browser history if one exists (i.e.,
        if you have previously navigated back).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating the outcome of the forward
                  navigation, e.g., "Forward navigation successful." or an
                  error message if no next page exists.
                - "snapshot": A new textual snapshot of the page after
                  navigation. If the snapshot is unchanged, it will be the
                  string "snapshot not changed".
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        page = await self._require_page()

        try:
            logger.info("Navigating forward in browser history...")
            nav_start = time.time()
            await page.go_forward(wait_until="domcontentloaded", timeout=30000)
            nav_time = time.time() - nav_start
            logger.info(f"Forward navigation completed in {nav_time:.2f}s")

            # Wait for page stability
            await self._wait_for_page_stability()

            # Get snapshot
            logger.info("Capturing page snapshot after forward navigation...")
            snapshot_start = time.time()
            snapshot = await self._session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            snapshot_time = time.time() - snapshot_start
            logger.info(
                f"Forward navigation snapshot captured in {snapshot_time:.2f}s"
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
    async def get_page_snapshot(self) -> str:
        r"""Captures a textual representation of the current page's content.

        This "snapshot" provides a simplified view of the DOM, focusing on
        interactive elements like links, buttons, and input fields. Each
        element is assigned a unique reference ID (`ref`) that can be used in
        other actions like `click` or `type`.

        The snapshot is useful for understanding the page structure and
        identifying elements to interact with without needing to parse raw
        HTML. A new snapshot is generated on each call.

        Returns:
            str: A formatted string representing the interactive elements on
                the page. For example:
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
    async def get_som_screenshot(self):
        r"""Captures a screenshot of the current webpage and visually marks all
        interactive elements. "SoM" stands for "Set of Marks".

        This method is essential for tasks requiring visual understanding of
        the page layout. It works by:
        1. Taking a full-page screenshot.
        2. Identifying all interactive elements (buttons, links, inputs, etc.).
        3. Drawing colored boxes and reference IDs (`ref`) over these elements
           on the screenshot.
        4. Saving the annotated image to a cache directory.
        5. Returning the image as a base64-encoded string along with a summary.

        Use this when the textual snapshot from `get_page_snapshot` is
        insufficient and visual context is needed to decide the next action.

        Returns:
            ToolResult: An object containing:
                - `text`: A summary string, e.g., "Visual webpage screenshot
                  captured with 42 interactive elements".
                - `images`: A list containing a single base64-encoded PNG image
                  as a data URL.
        """
        from PIL import Image

        from camel.utils.tool_result import ToolResult

        # Get screenshot and analysis
        page = await self._require_page()

        # Log screenshot timeout start
        logger.info(
            f"Starting screenshot capture"
            f"with timeout: {self.DEFAULT_SCREENSHOT_TIMEOUT}ms"
        )

        start_time = time.time()
        image_data = await page.screenshot(
            timeout=self.DEFAULT_SCREENSHOT_TIMEOUT
        )
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
            self.cache_dir, f"{url_name}_{timestamp}_som.png"
        )
        marked_image.save(file_path, "PNG")

        # Convert to base64
        img_buffer = io.BytesIO()
        marked_image.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        img_data_url = f"data:image/png;base64,{img_base64}"

        text_result = (
            f"Visual webpage screenshot "
            f"captured with {len(rects)} interactive elements"
        )

        return ToolResult(text=text_result, images=[img_data_url])

    async def click(self, *, ref: str) -> Dict[str, Any]:
        r"""Clicks on an interactive element on the page.

        Args:
            ref (str): The reference ID of the element to click. This ID is
                obtained from the page snapshot (see `get_page_snapshot` or
                `get_som_screenshot`).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message confirming the click action.
                - "snapshot": A new textual snapshot of the page after the
                  click, which may have changed as a result of the action. If
                  the snapshot is unchanged, it will be the string "snapshot
                  not changed".
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        self._validate_ref(ref, "click")

        analysis = await self._get_unified_analysis()
        elements = analysis.get("elements", {})
        if ref not in elements:
            available_refs = list(elements.keys())
            logger.error(f"Error: Element reference '{ref}' not found. ")
            # Added snapshot to give more context on failure
            snapshot = self._format_snapshot_from_analysis(analysis)
            tab_info = await self._get_tab_info_for_output()
            return {
                "result": f"Error: Element reference '{ref}' not found. "
                f"Available refs: {available_refs}",
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

    async def type(self, *, ref: str, text: str) -> Dict[str, Any]:
        r"""Types text into an input field, such as a textbox or search bar.

        Args:
            ref (str): The reference ID of the input element.
            text (str): The text to be typed into the element.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message confirming the type action.
                - "snapshot": A new textual snapshot of the page after the
                  text has been entered.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        self._validate_ref(ref, "type")
        await self._get_unified_analysis()  # Ensure aria-ref attributes

        action = {"type": "type", "ref": ref, "text": text}
        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    async def select(self, *, ref: str, value: str) -> Dict[str, Any]:
        r"""Selects an option from a dropdown (`<select>`) element.

        Args:
            ref (str): The reference ID of the `<select>` element.
            value (str): The value of the `<option>` to be selected. This
                should match the `value` attribute of the option, not the
                visible text.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message confirming the select action.
                - "snapshot": A new snapshot of the page after the selection.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        self._validate_ref(ref, "select")
        await self._get_unified_analysis()

        action = {"type": "select", "ref": ref, "value": value}
        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    async def scroll(self, *, direction: str, amount: int) -> Dict[str, Any]:
        r"""Scrolls the page window up or down by a specified amount.

        Args:
            direction (str): The direction to scroll. Must be either 'up' or
                'down'.
            amount (int): The number of pixels to scroll.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A confirmation of the scroll action.
                - "snapshot": A new snapshot of the page after scrolling.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
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

    async def enter(self) -> Dict[str, Any]:
        r"""Simulates pressing the Enter key on the currently focused element.

        This tool is used to execute or confirm an action after interacting
        with
        an element, such as:
        - Submitting a search query after typing in a search box.
        - Confirming a form submission.
        - Executing a command in a text input field.

        The common usage pattern is to first use the 'type' tool to input
        text, which sets the focus, and then call 'enter' without any
        parameters to trigger the action.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A confirmation of the Enter key action.
                - "snapshot": A new page snapshot, as this action often
                  triggers navigation or page updates.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        # Always press Enter on the currently focused element
        action = {"type": "enter"}

        result = await self._exec_with_snapshot(action)

        # Add tab information to the result
        tab_info = await self._get_tab_info_for_output()
        result.update(tab_info)

        return result

    @action_logger
    async def wait_user(
        self, timeout_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        r"""Pauses the agent's execution and waits for human intervention.

        This is useful for tasks that require manual steps, like solving a
        CAPTCHA. The agent will print a message to the console and wait
        until the user presses the Enter key.

        Args:
            timeout_sec (Optional[float]): The maximum time to wait in
                seconds. If the timeout is reached, the agent will resume
                automatically. If `None`, it will wait indefinitely.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating how the wait ended (e.g.,
                  "User resumed." or "Timeout... reached, auto-resumed.").
                - "snapshot": The current page snapshot after the wait.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
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
    async def get_page_links(self, *, ref: List[str]) -> Dict[str, Any]:
        r"""Retrieves the full URLs for a given list of link reference IDs.

        This is useful when you need to know the destination of a link before
        clicking it.

        Args:
            ref (List[str]): A list of reference IDs for link elements,
                obtained from a page snapshot.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "links": A list of dictionaries, where each dictionary
                  represents a found link and has "text", "ref", and "url"
                  keys.
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
    async def solve_task(
        self, task_prompt: str, start_url: str, max_steps: int = 15
    ) -> str:
        r"""Uses a high-level LLM agent to autonomously complete a task.

        This function delegates control to another agent that can reason about
        a task, break it down into steps, and execute browser actions to
        achieve the goal. It is suitable for complex, multi-step tasks.

        Note: `web_agent_model` must be provided during the toolkit's
        initialization to use this function.

        Args:
            task_prompt (str): A natural language description of the task to
                be completed (e.g., "log into my account on example.com").
            start_url (str): The URL to start the task from.
            max_steps (int): The maximum number of steps the agent is allowed
                to take before stopping.

        Returns:
            str: A summary message indicating that the task processing has
                finished. The detailed trace of the agent's actions will be
                printed to the standard output.
        """
        agent = self._ensure_agent()
        await agent.navigate(start_url)
        await agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

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

    def get_tools(self) -> List[FunctionTool]:
        r"""Get available function tools
        based on enabled_tools configuration."""
        # Map tool names to their corresponding methods
        tool_map = {
            "open_browser": self.open_browser,
            "close_browser": self.close_browser,
            "visit_page": self.visit_page,
            "back": self.back,
            "forward": self.forward,
            "get_page_snapshot": self.get_page_snapshot,
            "get_som_screenshot": self.get_som_screenshot,
            "get_page_links": self.get_page_links,
            "click": self.click,
            "type": self.type,
            "select": self.select,
            "scroll": self.scroll,
            "enter": self.enter,
            "wait_user": self.wait_user,
            "solve_task": self.solve_task,
            "switch_tab": self.switch_tab,
            "close_tab": self.close_tab,
            "get_tab_info": self.get_tab_info,
        }

        enabled_tools = []

        for tool_name in self.enabled_tools:
            if tool_name == "solve_task" and self.web_agent_model is None:
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
            stealth=self._session._stealth if self._session else False,
            web_agent_model=self.web_agent_model,
            cache_dir=f"{self.cache_dir.rstrip('/')}_clone_{new_session_id}/",
            enabled_tools=self.enabled_tools.copy(),
            browser_log_to_file=self.log_to_file,
            session_id=new_session_id,
            default_start_url=self.default_start_url,
        )

    @action_logger
    async def switch_tab(self, *, tab_index: int) -> Dict[str, Any]:
        r"""Switches to a specific browser tab by its index.

        This allows you to control which tab is currently active. After
        switching, all subsequent browser actions will operate on the newly
        selected tab.

        Args:
            tab_index (int): The zero-based index of the tab to switch to.
                Use `get_tab_info` to see available tabs and their indices.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating success or failure of the
                  tab switch.
                - "snapshot": A textual snapshot of the newly active tab's
                  content.
                - "tabs": List of all open tabs with their information.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of open tabs.
        """
        await self._ensure_browser()
        session = await self._get_session()

        success = await session.switch_to_tab(tab_index)

        if success:
            snapshot = await session.get_snapshot(
                force_refresh=True, diff_only=False
            )
            tab_info = await self._get_tab_info_for_output()

            result = {
                "result": f"Successfully switched to tab {tab_index}",
                "snapshot": snapshot,
                **tab_info,
            }
        else:
            tab_info = await self._get_tab_info_for_output()
            result = {
                "result": f"Failed to switch to tab {tab_index}. Tab may not "
                f"exist.",
                "snapshot": "",
                **tab_info,
            }

        return result

    @action_logger
    async def close_tab(self, *, tab_index: int) -> Dict[str, Any]:
        r"""Closes a specific browser tab by its index.

        After closing a tab, the browser will automatically switch to another
        available tab. If the closed tab was the only one open, the browser
        session will remain active but without any pages.

        Args:
            tab_index (int): The zero-based index of the tab to close.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "result": A message indicating success or failure of the
                  tab closure.
                - "snapshot": A textual snapshot of the currently active tab
                  after the closure (empty if no tabs remain).
                - "tabs": List of remaining open tabs.
                - "current_tab": Index of the currently active tab.
                - "total_tabs": Total number of remaining open tabs.
        """
        await self._ensure_browser()
        session = await self._get_session()

        success = await session.close_tab(tab_index)

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
                "result": f"Successfully closed tab {tab_index}",
                "snapshot": snapshot,
                **tab_info,
            }
        else:
            tab_info = await self._get_tab_info_for_output()
            result = {
                "result": f"Failed to close tab {tab_index}. Tab may not "
                f"exist.",
                "snapshot": "",
                **tab_info,
            }

        return result

    @action_logger
    async def get_tab_info(self) -> Dict[str, Any]:
        r"""Retrieves information about all currently open browser tabs.

        This provides a comprehensive overview of the browser state, including
        all open tabs, their titles, URLs, and which one is currently active.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "tabs": A list of dictionaries, each representing a tab with:
                  - "index": The zero-based index of the tab
                  - "title": The page title
                  - "url": The current URL
                  - "is_current": Whether this is the currently active tab
                - "current_tab": Index of the currently active tab
                - "total_tabs": Total number of open tabs
        """
        await self._ensure_browser()
        return await self._get_tab_info_for_output()
