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

# Enables postponed evaluation of annotations (for string-based type hints)
from __future__ import annotations

import datetime
import io
import os
import re
import shutil
import threading
import time
import urllib.parse
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

from PIL import Image

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.video_analysis_toolkit import VideoAnalysisToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import (
    dependencies_required,
    retry_on_error,
    sanitize_filename,
)

# Import shared components from browser_toolkit_commons
from .browser_toolkit_commons import (
    ACTION_WITH_FEEDBACK_LIST,
    AVAILABLE_ACTIONS_PROMPT,
    GET_FINAL_ANSWER_PROMPT_TEMPLATE,
    OBSERVE_PROMPT_TEMPLATE,
    PLANNING_AGENT_SYSTEM_PROMPT,
    TASK_PLANNING_PROMPT_TEMPLATE,
    TASK_REPLANNING_PROMPT_TEMPLATE,
    WEB_AGENT_SYSTEM_PROMPT,
    InteractiveRegion,
    VisualViewport,
    _add_set_of_mark,
    _parse_json_output,
    _reload_image,
    interactive_region_from_dict,
    visual_viewport_from_dict,
)

if TYPE_CHECKING:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        FloatRect,
        Page,
        Playwright,
    )

    from camel.agents import ChatAgent

logger = get_logger(__name__)

TOP_NO_LABEL_ZONE = 20


def _get_str(d: Any, k: str) -> str:
    r"""Safely retrieve a string value from a dictionary."""
    if k not in d:
        raise KeyError(f"Missing required key: '{k}'")
    val = d[k]
    if isinstance(val, str):
        return val
    raise TypeError(
        f"Expected a string for key '{k}', but got {type(val).__name__}"
    )


def _get_number(d: Any, k: str) -> Union[int, float]:
    r"""Safely retrieve a number (int or float) from a dictionary"""
    val = d[k]
    if isinstance(val, (int, float)):
        return val
    raise TypeError(
        f"Expected a number (int/float) for key "
        f"'{k}', but got {type(val).__name__}"
    )


def _get_bool(d: Any, k: str) -> bool:
    r"""Safely retrieve a boolean value from a dictionary."""
    val = d[k]
    if isinstance(val, bool):
        return val
    raise TypeError(
        f"Expected a boolean for key '{k}', but got {type(val).__name__}"
    )


class BaseBrowser:
    def __init__(
        self,
        headless=True,
        cache_dir: Optional[str] = None,
        channel: Literal["chrome", "msedge", "chromium"] = "chromium",
        cookie_json_path: Optional[str] = None,
        user_data_dir: Optional[str] = None,
    ):
        r"""Initialize the WebBrowser instance.

        Args:
            headless (bool): Whether to run the browser in headless mode.
            cache_dir (Union[str, None]): The directory to store cache files.
            channel (Literal["chrome", "msedge", "chromium"]): The browser
                channel to use. Must be one of "chrome", "msedge", or
                "chromium".
            cookie_json_path (Optional[str]): Path to a JSON file containing
                authentication cookies and browser storage state. If provided
                and the file exists, the browser will load this state to
                maintain authenticated sessions. This is primarily used when
                `user_data_dir` is not set.
            user_data_dir (Optional[str]): The directory to store user data
                for persistent context. If None, a fresh browser instance
                is used without saving data. (default: :obj:`None`)

        Returns:
            None
        """
        from playwright.sync_api import (
            sync_playwright,
        )

        self.history: List[Any] = []
        self.headless = headless
        self.channel = channel
        self._ensure_browser_installed()
        self.playwright: Playwright = sync_playwright().start()
        self.page_history: List[
            str
        ] = []  # stores the history of visited pages
        self.cookie_json_path = cookie_json_path
        self.user_data_dir = user_data_dir

        # Set the cache directory
        self.cache_dir = "tmp/" if cache_dir is None else cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # Create user data directory only if specified
        if self.user_data_dir:
            os.makedirs(self.user_data_dir, exist_ok=True)

        # Load the page script
        abs_dir_path = os.path.dirname(os.path.abspath(__file__))
        page_script_path = os.path.join(abs_dir_path, "page_script.js")

        try:
            with open(page_script_path, "r", encoding='utf-8') as f:
                self.page_script = f.read()
            f.close()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Page script file not found at path: {page_script_path}"
            )
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.page_url: Optional[str] = None
        self.web_agent_model: Optional[BaseModelBackend] = (
            None  # Added for type hinting
        )
        self.tabs: Dict[int, Page] = {}
        self.current_tab_id: Optional[int] = 0

        # Add threading lock for thread-safe tab ID generation
        self._tab_id_lock = threading.Lock()

    def init(self) -> None:
        r"""Initialize the browser."""
        assert self.playwright is not None

        browser_launch_args = [
            "--disable-blink-features=AutomationControlled",  # Basic stealth
        ]

        user_agent_string = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        if self.user_data_dir:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                channel=self.channel,
                accept_downloads=True,
                user_agent=user_agent_string,
                java_script_enabled=True,
                args=browser_launch_args,
            )
            self.browser = None  # Not using a separate browser instance
            if (
                len(self.context.pages) > 0
            ):  # Persistent context might reopen pages
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()
                self.tabs[0] = self.page
                self.current_tab_id = 0
        else:
            # Launch a fresh browser instance
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                channel=self.channel,
                args=browser_launch_args,
            )

            new_context_kwargs: Dict[str, Any] = {
                "accept_downloads": True,
                "user_agent": user_agent_string,
                "java_script_enabled": True,
            }
            if self.cookie_json_path and os.path.exists(self.cookie_json_path):
                new_context_kwargs["storage_state"] = self.cookie_json_path

            self.context = self.browser.new_context(**new_context_kwargs)
            self.page = self.context.new_page()

            self.tabs[0] = self.page
            self.current_tab_id = 0

        assert self.context is not None
        assert self.page is not None

    def clean_cache(self) -> None:
        r"""Delete the cache directory and its contents."""
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    def open_tab(self, url: Union[str, List[str]]) -> Union[int, List[int]]:
        r"""Open one or multiple tabs and navigate to URL(s); return tab_id(s).

        Args:
            url (Union[str, List[str]]): Single URL or list of URLs to navigate to.

        Returns:
            Union[int, List[int]]: Single tab ID or list of tab IDs.
        """
        assert self.context, "Context not initialized"

        # Handle single URL case
        if isinstance(url, str):
            page = self.context.new_page()
            try:
                page.goto(url)
                page.wait_for_load_state("load", timeout=20000)
            except Exception as e:
                page.close()
                raise ValueError(f"Failed to navigate to {url}: {e}")

            # Atomic tab ID assignment using threading lock
            with self._tab_id_lock:
                new_id = max(self.tabs.keys()) + 1 if self.tabs else 0
                self.tabs[new_id] = page

            return new_id

        # Handle multiple URLs case
        elif isinstance(url, list):
            if not url:
                return []

            # Create all pages first
            pages = []
            for _ in url:
                pages.append(self.context.new_page())

            # Prepare results list
            tab_ids = []

            # Atomic tab ID assignment using threading lock
            with self._tab_id_lock:
                base_id = max(self.tabs.keys()) + 1 if self.tabs else 0

                # Assign IDs and add to tabs dict
                for i, page in enumerate(pages):
                    tab_id = base_id + i
                    self.tabs[tab_id] = page
                    tab_ids.append(tab_id)

            # Navigate to URLs in parallel using threads
            def navigate_page(
                page: Any, url: str, tab_id: int
            ) -> Tuple[int, bool, str]:
                """Navigate a single page to its URL."""
                try:
                    page.goto(url)
                    page.wait_for_load_state("load", timeout=20000)
                    return tab_id, True, ""
                except Exception as e:
                    page.close()
                    # Remove from tabs dict if navigation failed
                    with self._tab_id_lock:
                        if tab_id in self.tabs:
                            del self.tabs[tab_id]
                    return tab_id, False, str(e)

            # Create and start threads for parallel navigation
            threads = []
            results = {}

            for i, (page, single_url) in enumerate(zip(pages, url)):
                thread = threading.Thread(
                    target=lambda p=page,
                    u=single_url,
                    tid=tab_ids[i]: results.update(
                        {tid: navigate_page(p, u, tid)}
                    )
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Check results and handle any failures
            successful_tab_ids = []
            failed_urls = []

            for tab_id in tab_ids:
                if tab_id in results:
                    success, error_msg = results[tab_id][1], results[tab_id][2]
                    if success:
                        successful_tab_ids.append(tab_id)
                    else:
                        failed_urls.append(f"Tab {tab_id}: {error_msg}")

            # Log any failures
            if failed_urls:
                logger.warning(f"Failed to navigate some tabs: {failed_urls}")

            return successful_tab_ids

        else:
            raise TypeError("URL must be a string or list of strings")

    def switch_tab(self, tab_id: int) -> None:
        r"""Switch active page to the designated tab.

        Args:
            tab_id (int): The ID of the tab to activate.

        Raises:
            ValueError: If the tab ID does not exist or refers to a closed tab.
        """
        target_page, _ = self._get_target_page(tab_id)
        self.page = target_page
        self.current_tab_id = tab_id

    def close_tab(
        self, tab_id: Union[int, List[int]]
    ) -> Union[str, List[Tuple[int, bool, str]]]:
        r"""Close one or multiple tabs and adjust active tab.

        Args:
            tab_id (Union[int, List[int]]): Single tab ID or list of tab IDs to close.

        Returns:
            Union[str, List[Tuple[int, bool, str]]]: String result for single tab, or list of
            (tab_id, success, message) tuples for multiple tabs.

        Raises:
            ValueError: If any of the specified tabs do not exist.
        """
        # Handle single tab case
        if isinstance(tab_id, int):
            # Use _get_target_page for validation and getting the page
            target_page, _ = self._get_target_page(tab_id)
            target_page.close()
            del self.tabs[tab_id]

            # Adjust current tab if the closed tab was active
            if (
                self.current_tab_id is not None
                and tab_id == self.current_tab_id
            ):
                remaining = sorted(self.tabs.keys())
                if remaining:
                    self.switch_tab(remaining[0])
                else:
                    self.page = None
                    self.current_tab_id = None

            return f"Successfully closed tab {tab_id}."

        # Handle multiple tabs case
        elif isinstance(tab_id, list):
            if not tab_id:
                return []

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Check if current tab is in the list to be closed
            current_tab_closed = (
                self.current_tab_id is not None
                and self.current_tab_id in tab_id
            )

            # Define inline function for parallel execution
            def close_single_tab_operation(tid: int) -> Tuple[int, bool, str]:
                """Close a single tab and return result."""
                try:
                    if tid in self.tabs:
                        self.tabs[tid].close()
                        # Note: We don't delete from self.tabs here to avoid race conditions
                        return tid, True, f"Successfully closed tab {tid}"
                    else:
                        return tid, False, f"Tab {tid} was already closed"
                except Exception as e:
                    return tid, False, f"Error closing tab {tid}: {e!s}"

            # Use _execute_parallel_operation for parallel closing
            results_dict = self._execute_parallel_operation(
                close_single_tab_operation, valid_tabs
            )

            # Process results and clean up tabs dict
            results = []
            for tid in tab_id:
                if tid in results_dict:
                    success, message = (
                        results_dict[tid][1],
                        results_dict[tid][2],
                    )
                    if success:
                        # Remove from tabs dict only after successful closure
                        if tid in self.tabs:
                            del self.tabs[tid]
                    results.append((tid, success, message))

            # Adjust current tab if it was closed
            if current_tab_closed:
                remaining = sorted(self.tabs.keys())
                if remaining:
                    self.switch_tab(remaining[0])
                else:
                    self.page = None
                    self.current_tab_id = None

            return results

        else:
            raise TypeError("tab_id must be an integer or list of integers")

    def _wait_for_load(self, timeout: int = 20) -> None:
        r"""Wait for a certain amount of time for the page to load."""
        timeout_ms = timeout * 1000
        assert self.page is not None
        self.page.wait_for_load_state("load", timeout=timeout_ms)

        # TODO: check if this is needed
        time.sleep(2)

    def click_blank_area(self) -> None:
        r"""Click a blank area of the page to unfocus the current element."""
        assert self.page is not None
        self.page.mouse.click(0, 0)
        self._wait_for_load()

    @retry_on_error()
    def visit_page(self, url: str) -> None:
        r"""Visit a page with the given URL."""
        assert self.page is not None
        self.page.goto(url)
        self._wait_for_load()
        self.page_url = url

    def ask_question_about_video(self, question: str) -> str:
        r"""Ask a question about the video on the current page,
        such as YouTube video.

        Args:
            question (str): The question to ask.

        Returns:
            str: The answer to the question.
        """
        current_url = self.get_url()

        # Ensure current_url is a string
        if isinstance(current_url, dict):
            # Add null check before using as dictionary key
            if self.current_tab_id is not None:
                current_url = current_url.get(self.current_tab_id, "")
            else:
                current_url = ""
        elif not isinstance(current_url, str):
            current_url = str(current_url)

        # Confirm with user before proceeding due to potential slow
        # processing time
        confirmation_message = (
            f"Do you want to analyze the video on the current "
            f"page({current_url})? This operation may take a long time.(y/n): "
        )
        user_confirmation = input(confirmation_message)

        if user_confirmation.lower() not in ['y', 'yes']:
            return "User cancelled the video analysis."

        model = None
        if (
            hasattr(self, 'web_agent_model')
            and self.web_agent_model is not None
        ):
            model = self.web_agent_model

        video_analyzer = VideoAnalysisToolkit(model=model)
        result = video_analyzer.ask_question_about_video(current_url, question)
        return result

    @retry_on_error()
    def get_screenshot(
        self,
        save_image: bool = False,
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[
        Tuple[Image.Image, Union[str, None]],
        Dict[int, Tuple[Image.Image, Union[str, None]]],
    ]:
        r"""Get a screenshot of the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            save_image (bool): Whether to save the image(s) to the cache directory.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to screenshot.
                If None, uses the current active page. If int, screenshots single tab.
                If List[int], screenshots multiple tabs simultaneously.

        Returns:
            Union[Tuple[Image.Image, Union[str, None]], Dict[int, Tuple[Image.Image, Union[str, None]]]]:
            For single tab: tuple containing (screenshot_image, file_path_or_none).
            For multiple tabs: dictionary mapping tab IDs to (screenshot_image, file_path_or_none) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page screenshot
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Take screenshot
            image_data = target_page.screenshot(timeout=60000)
            image = Image.open(io.BytesIO(image_data))

            file_path = None
            if save_image:
                target_url = target_page.url
                parsed_url = urllib.parse.urlparse(target_url)
                url_name = sanitize_filename(
                    str(parsed_url.path), max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")

                if single_tab_id is not None:
                    file_path = os.path.join(
                        self.cache_dir,
                        f"tab_{single_tab_id}_{url_name}_{timestamp}.png",
                    )
                else:
                    file_path = os.path.join(
                        self.cache_dir, f"{url_name}_{timestamp}.png"
                    )

                with open(file_path, "wb") as f:
                    image.save(f, "PNG")

            return image, file_path

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the screenshot operation function
            def capture_single_tab_screenshot(
                tid: int,
            ) -> Tuple[int, Tuple[Image.Image, Union[str, None]]]:
                """Capture screenshot for a single tab."""
                try:
                    page = self.tabs[tid]
                    image_data = page.screenshot(timeout=60000)
                    image = Image.open(io.BytesIO(image_data))

                    file_path = None
                    if save_image:
                        target_url = page.url
                        parsed_url = urllib.parse.urlparse(target_url)
                        url_name = sanitize_filename(
                            str(parsed_url.path), max_length=241
                        )
                        timestamp = datetime.datetime.now().strftime(
                            "%m%d%H%M%S"
                        )
                        file_path = os.path.join(
                            self.cache_dir,
                            f"tab_{tid}_{url_name}_{timestamp}.png",
                        )
                        with open(file_path, "wb") as f:
                            image.save(f, "PNG")

                    return tid, (image, file_path)
                except Exception as e:
                    logger.error(
                        f"Error capturing screenshot for tab {tid}: {e}"
                    )
                    # Create a default image instead of returning None
                    default_image = Image.new('RGB', (100, 100), color='white')
                    return tid, (default_image, None)

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                capture_single_tab_screenshot, valid_tabs
            )

            # Process results and filter out failed captures
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if (
                        result[1][0] is not None
                    ):  # Check if image was captured successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to capture screenshot for tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def capture_full_page_screenshots(
        self,
        scroll_ratio: float = 0.8,
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[List[str], Dict[int, List[str]]]:
        r"""Capture full page screenshots by scrolling the page with a buffer
        zone for one or multiple tabs.

        Args:
            scroll_ratio (float): The ratio of viewport height to scroll each
                step. (default: :obj:`0.8`)
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to capture.
                If None, uses the current active page. If int, captures single tab.
                If List[int], captures multiple tabs simultaneously.

        Returns:
            Union[List[str], Dict[int, List[str]]]: For single tab: list of screenshot file paths.
                For multiple tabs: dictionary mapping tab IDs to lists of screenshot file paths.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page capture
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)
            assert target_page.viewport_size is not None

            screenshots: List[str] = []
            scroll_height_eval = target_page.evaluate(
                "document.body.scrollHeight"
            )
            scroll_height = cast(float, scroll_height_eval)

            viewport_height = target_page.viewport_size["height"]
            current_scroll_eval = target_page.evaluate("window.scrollY")
            current_scroll = cast(float, current_scroll_eval)

            max_height = scroll_height - viewport_height
            scroll_step = int(viewport_height * scroll_ratio)

            last_height = 0.0

            while True:
                logger.debug(
                    f"Current scroll: {current_scroll}, max_height: "
                    f"{max_height}, step: {scroll_step}"
                )

                # Take screenshot of current viewport
                image_data = target_page.screenshot(timeout=60000)
                image = Image.open(io.BytesIO(image_data))

                # Save screenshot with appropriate naming
                parsed_url = urllib.parse.urlparse(target_page.url)
                url_name = sanitize_filename(
                    str(parsed_url.path), max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")

                # Include tab_id in filename if capture is from specific tab
                if single_tab_id is not None:
                    file_path = os.path.join(
                        self.cache_dir,
                        f"fullpage_tab_{single_tab_id}_{url_name}_{timestamp}.png",
                    )
                else:
                    file_path = os.path.join(
                        self.cache_dir, f"fullpage_{url_name}_{timestamp}.png"
                    )

                with open(file_path, "wb") as f:
                    image.save(f, "PNG")

                screenshots.append(file_path)

                target_page.evaluate(f"window.scrollBy(0, {scroll_step})")
                # Allow time for content to load
                time.sleep(0.5)

                current_scroll_eval = target_page.evaluate("window.scrollY")
                current_scroll = cast(float, current_scroll_eval)
                # Break if there is no significant scroll
                if abs(current_scroll - last_height) < viewport_height * 0.1:
                    break

                last_height = current_scroll

            return screenshots

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the screenshot operation function
            def capture_single_tab_full_page_screenshots(
                tid: int,
            ) -> Tuple[int, List[str]]:
                """Capture full page screenshots for a single tab."""
                try:
                    page = self.tabs[tid]

                    assert page.viewport_size is not None

                    screenshots: List[str] = []
                    scroll_height_eval = page.evaluate(
                        "document.body.scrollHeight"
                    )
                    scroll_height = cast(float, scroll_height_eval)

                    viewport_height = page.viewport_size["height"]
                    current_scroll_eval = page.evaluate("window.scrollY")
                    current_scroll = cast(float, current_scroll_eval)

                    max_height = scroll_height - viewport_height
                    scroll_step = int(viewport_height * scroll_ratio)

                    last_height = 0.0

                    while True:
                        logger.debug(
                            f"Tab {tid} - Current scroll: {current_scroll}, max_height: "
                            f"{max_height}, step: {scroll_step}"
                        )

                        # Take screenshot of current viewport
                        image_data = page.screenshot(timeout=60000)
                        image = Image.open(io.BytesIO(image_data))

                        # Save screenshot with tab-specific naming
                        parsed_url = urllib.parse.urlparse(page.url)
                        url_name = sanitize_filename(
                            str(parsed_url.path), max_length=241
                        )
                        timestamp = datetime.datetime.now().strftime(
                            "%m%d%H%M%S"
                        )
                        file_path = os.path.join(
                            self.cache_dir,
                            f"fullpage_tab_{tid}_{url_name}_{timestamp}.png",
                        )

                        with open(file_path, "wb") as f:
                            image.save(f, "PNG")

                        screenshots.append(file_path)

                        page.evaluate(f"window.scrollBy(0, {scroll_step})")
                        # Allow time for content to load
                        time.sleep(0.5)

                        current_scroll_eval = page.evaluate("window.scrollY")
                        current_scroll = cast(float, current_scroll_eval)
                        # Break if there is no significant scroll
                        if (
                            abs(current_scroll - last_height)
                            < viewport_height * 0.1
                        ):
                            break

                        last_height = current_scroll

                    return tid, screenshots
                except Exception as e:
                    logger.error(
                        f"Error capturing full page screenshots for tab {tid}: {e}"
                    )
                    return tid, []

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                capture_single_tab_full_page_screenshots, valid_tabs
            )

            # Process results and filter out failed captures
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[
                        1
                    ]:  # Check if screenshots were captured successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to capture full page screenshots for tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def get_visual_viewport(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[VisualViewport, Dict[int, VisualViewport]]:
        r"""Get the visual viewport of the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to get viewport for.
                If None, uses the current active page. If int, gets viewport for single tab.
                If List[int], gets viewport for multiple tabs simultaneously.

        Returns:
            Union[VisualViewport, Dict[int, VisualViewport]]: For single tab: VisualViewport object.
                For multiple tabs: dictionary mapping tab IDs to VisualViewport objects.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page viewport
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            try:
                target_page.evaluate(self.page_script)
            except Exception as e:
                logger.warning(f"Error evaluating page script: {e}")

            visual_viewport_eval = target_page.evaluate(
                "MultimodalWebSurfer.getVisualViewport();"
            )
            return visual_viewport_from_dict(
                cast(Dict[str, Any], visual_viewport_eval)
            )

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the viewport operation function
            def get_single_tab_viewport(
                tid: int,
            ) -> Tuple[int, VisualViewport]:
                """Get viewport for a single tab."""
                try:
                    page = self.tabs[tid]
                    visual_viewport_eval = page.evaluate(
                        "MultimodalWebSurfer.getVisualViewport();"
                    )
                    return tid, visual_viewport_from_dict(
                        cast(Dict[str, Any], visual_viewport_eval)
                    )
                except Exception as e:
                    logger.error(f"Error getting viewport for tab {tid}: {e}")
                    # Return a default VisualViewport instead of None
                    default_viewport = VisualViewport(
                        height=600,
                        width=800,
                        offsetLeft=0,
                        offsetTop=0,
                        pageLeft=0,
                        pageTop=0,
                        scale=1,
                        clientWidth=800,
                        clientHeight=600,
                        scrollWidth=800,
                        scrollHeight=600,
                    )

                    logger.info(
                        f"Using fallback viewport values for tab {tid} due to error: {e}"
                    )
                    return tid, default_viewport

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                get_single_tab_viewport, valid_tabs
            )

            # Process results and filter out failed captures
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if (
                        result[1] is not None
                    ):  # Check if viewport was captured successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to get viewport for tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def get_interactive_elements(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[
        Dict[str, InteractiveRegion], Dict[int, Dict[str, InteractiveRegion]]
    ]:
        r"""Get the interactive elements of the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to get interactive elements for.
                If None, uses the current active page. If int, gets elements for single tab.
                If List[int], gets elements for multiple tabs simultaneously.

        Returns:
            Union[Dict[str, InteractiveRegion], Dict[int, Dict[str, InteractiveRegion]]]: For single tab: dictionary of interactive elements.
                For multiple tabs: dictionary mapping tab IDs to dictionaries of interactive elements.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page interactive elements
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            try:
                target_page.evaluate(self.page_script)
            except Exception as e:
                logger.warning(f"Error evaluating page script: {e}")

            result = cast(
                Dict[str, Dict[str, Any]],
                target_page.evaluate(
                    "MultimodalWebSurfer.getInteractiveRects();"
                ),
            )

            typed_results: Dict[str, InteractiveRegion] = {}
            for k in result:
                typed_results[k] = interactive_region_from_dict(result[k])

            return typed_results

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the interactive elements operation function
            def get_single_tab_interactive_elements(
                tid: int,
            ) -> Tuple[int, Dict[str, InteractiveRegion]]:
                """Get interactive elements for a single tab."""
                try:
                    page = self.tabs[tid]
                    page.evaluate(self.page_script)
                    result = cast(
                        Dict[str, Dict[str, Any]],
                        page.evaluate(
                            "MultimodalWebSurfer.getInteractiveRects();"
                        ),
                    )

                    typed_results: Dict[str, InteractiveRegion] = {}
                    for k in result:
                        typed_results[k] = interactive_region_from_dict(
                            result[k]
                        )

                    return tid, typed_results
                except Exception as e:
                    logger.error(
                        f"Error getting interactive elements for tab {tid}: {e}"
                    )
                    return tid, {}

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                get_single_tab_interactive_elements, valid_tabs
            )

            # Process results and filter out failed captures
            final_results: Dict[int, Dict[str, InteractiveRegion]] = {}
            for tid in tab_id:
                if tid in results_dict:
                    result_tuple = results_dict[
                        tid
                    ]  # This is Tuple[int, Dict[str, InteractiveRegion]]
                    if (
                        isinstance(result_tuple, tuple)
                        and len(result_tuple) >= 2
                    ):
                        interactive_elements = result_tuple[
                            1
                        ]  # Extract the Dict[str, InteractiveRegion]
                        if interactive_elements:  # Check if interactive elements were captured successfully
                            # Ensure proper type casting and validation
                            if isinstance(interactive_elements, dict):
                                final_results[tid] = interactive_elements
                            else:
                                logger.warning(
                                    f"Invalid result type for tab {tid}: {type(interactive_elements)}"
                                )
                        else:
                            logger.warning(
                                f"Failed to get interactive elements for tab {tid}"
                            )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def get_som_screenshot(
        self,
        save_image: bool = False,
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[
        Tuple[Image.Image, Union[str, None]],
        Dict[int, Tuple[Image.Image, Union[str, None]]],
    ]:
        r"""Get a screenshot of the current viewport with interactive elements
        marked for one or multiple tabs.

        Args:
            save_image (bool): Whether to save the image(s) to the cache directory.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to screenshot.
                If None, uses the current active page. If int, screenshots single tab.
                If List[int], screenshots multiple tabs simultaneously.

        Returns:
            Union[Tuple[Image.Image, Union[str, None]], Dict[int, Tuple[Image.Image, Union[str, None]]]]:
            For single tab: tuple containing (screenshot_image, file_path_or_none).
            For multiple tabs: dictionary mapping tab IDs to (screenshot_image, file_path_or_none) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page screenshot
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Remove the problematic _wait_for_load call
            # target_page._wait_for_load()  # This line should be removed

            # Use the browser's wait_for_load method instead
            self._wait_for_load()

            screenshot, _ = self.get_screenshot(
                save_image=False, tab_id=single_tab_id
            )
            rects = self.get_interactive_elements(tab_id=single_tab_id)

            # Ensure rects is the correct type for _add_set_of_mark
            if isinstance(rects, dict):
                # Check if all values are dictionaries with InteractiveRegion structure
                all_valid = True
                for v in rects.values():
                    if not isinstance(v, dict) or not all(
                        key in v
                        for key in [
                            "tag_name",
                            "role",
                            "aria_name",
                            "v_scrollable",
                            "rects",
                        ]
                    ):
                        all_valid = False
                        break

                if all_valid:
                    # Type cast to ensure compatibility with _add_set_of_mark
                    rects_dict: Dict[str, InteractiveRegion] = {}
                    for k, v in rects.items():
                        if isinstance(v, dict):
                            rects_dict[str(k)] = v  # type: ignore[assignment]
                    comp, _, _, _ = _add_set_of_mark(screenshot, rects_dict)
                else:
                    logger.warning("Invalid interactive elements format")
                    comp = screenshot
            else:
                logger.warning("Invalid interactive elements format")
                comp = screenshot

            file_path: str | None = None
            if save_image:
                target_url = target_page.url
                parsed_url = urllib.parse.urlparse(target_url)
                url_name = sanitize_filename(
                    str(parsed_url.path), max_length=241
                )
                timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")

                # Include tab_id in filename if screenshot is from specific tab
                if single_tab_id is not None:
                    file_path = os.path.join(
                        self.cache_dir,
                        f"som_tab_{single_tab_id}_{url_name}_{timestamp}.png",
                    )
                else:
                    file_path = os.path.join(
                        self.cache_dir, f"som_{url_name}_{timestamp}.png"
                    )

                with open(file_path, "wb") as f:
                    comp.save(f, "PNG")

            return comp, file_path

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the SOM screenshot operation function
            def capture_single_tab_som_screenshot(
                tid: int,
            ) -> Tuple[int, Tuple[Image.Image, Union[str, None]]]:
                """Capture SOM screenshot for a single tab."""
                try:
                    page = self.tabs[tid]
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability

                    screenshot, _ = self.get_screenshot(
                        save_image=False, tab_id=tid
                    )
                    rects = self.get_interactive_elements(tab_id=tid)

                    # Ensure rects is the correct type for _add_set_of_mark
                    if isinstance(rects, dict):
                        # Check if all values are dictionaries with InteractiveRegion structure
                        all_valid = True
                        for v in rects.values():
                            if not isinstance(v, dict) or not all(
                                key in v
                                for key in [
                                    "tag_name",
                                    "role",
                                    "aria_name",
                                    "v_scrollable",
                                    "rects",
                                ]
                            ):
                                all_valid = False
                                break

                        if all_valid:
                            # Type cast to ensure compatibility with _add_set_of_mark
                            rects_dict: Dict[str, InteractiveRegion] = {}
                            for k, v in rects.items():
                                if isinstance(v, dict):
                                    rects_dict[str(k)] = v  # type: ignore[assignment]
                            comp, _, _, _ = _add_set_of_mark(
                                screenshot, rects_dict
                            )
                        else:
                            logger.warning(
                                "Invalid interactive elements format"
                            )
                            comp = screenshot
                    else:
                        logger.warning("Invalid interactive elements format")
                        comp = screenshot

                    file_path = None
                    if save_image:
                        target_url = page.url
                        parsed_url = urllib.parse.urlparse(target_url)
                        url_name = sanitize_filename(
                            str(parsed_url.path), max_length=241
                        )
                        timestamp = datetime.datetime.now().strftime(
                            "%m%d%H%M%S"
                        )
                        file_path = os.path.join(
                            self.cache_dir,
                            f"som_tab_{tid}_{url_name}_{timestamp}.png",
                        )
                        with open(file_path, "wb") as f:
                            comp.save(f, "PNG")

                    # Ensure we return the correct type
                    if comp is not None and file_path is not None:
                        return tid, (comp, file_path)
                    elif comp is not None:
                        return tid, (comp, None)
                    else:
                        # Return a default image if screenshot failed
                        default_image = Image.new(
                            'RGB', (800, 600), color='white'
                        )
                        return tid, (default_image, None)
                except Exception as e:
                    logger.error(
                        f"Error capturing SOM screenshot for tab {tid}: {e}"
                    )
                    # Return a default image on error
                    default_image = Image.new('RGB', (800, 600), color='white')
                    return tid, (default_image, None)

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                capture_single_tab_som_screenshot, valid_tabs
            )

            # Process results and filter out failed captures
            final_results: Dict[int, Tuple[Image.Image, Optional[str]]] = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if (
                        result[1][0] is not None
                    ):  # Check if image was captured successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to capture SOM screenshot for tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def scroll_up(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Scroll up the page for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to scroll up.
                If None, uses the current active page. If int, scrolls up single tab.
                If List[int], scrolls up multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the scroll action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page scroll
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            target_page.keyboard.press("PageUp")
            return "Successfully scrolled up the page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the scroll up operation function
            def scroll_single_tab_up(tid: int) -> Tuple[int, Tuple[bool, str]]:
                """Scroll up a single tab."""
                try:
                    page = self.tabs[tid]
                    page.keyboard.press("PageUp")
                    return tid, (True, f"Successfully scrolled up tab {tid}")
                except Exception as e:
                    logger.error(f"Error scrolling up tab {tid}: {e}")
                    return tid, (False, f"Error scrolling up tab {tid}: {e!s}")

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                scroll_single_tab_up, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if scroll was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to scroll up tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def scroll_down(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Scroll down the page for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to scroll down.
                If None, uses the current active page. If int, scrolls down single tab.
                If List[int], scrolls down multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the scroll action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page scroll
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            target_page.keyboard.press("PageDown")
            return "Successfully scrolled down the page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the scroll down operation function
            def scroll_single_tab_down(
                tid: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Scroll down a single tab."""
                try:
                    page = self.tabs[tid]
                    page.keyboard.press("PageDown")
                    return tid, (True, f"Successfully scrolled down tab {tid}")
                except Exception as e:
                    logger.error(f"Error scrolling down tab {tid}: {e}")
                    return tid, (
                        False,
                        f"Error scrolling down tab {tid}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                scroll_single_tab_down, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if scroll was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to scroll down tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def get_url(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, str]]:
        r"""Get the URL of the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to get URL from.
                If None, uses the current active page. If int, gets URL for single tab.
                If List[int], gets URL for multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, str]]: For single tab: string URL of the page.
                For multiple tabs: dictionary mapping tab IDs to string URLs.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page URL
        if tab_id is None or isinstance(tab_id, int):
            try:
                single_tab_id = tab_id
                target_page, _ = self._get_target_page(single_tab_id)
                return target_page.url
            except ValueError as e:
                # Don't wrap the error message - pass it through as-is
                raise e

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            try:
                # Use _validate_tab_ids for validation
                valid_tabs, closed_tabs = self._validate_tab_ids(tab_id)

                # Define the URL operation function
                def get_single_tab_url(tid: int) -> Tuple[int, str]:
                    """Get URL for a single tab."""
                    try:
                        page = self.tabs[tid]
                        return tid, page.url
                    except Exception as e:
                        logger.error(f"Error getting URL for tab {tid}: {e}")
                        return tid, f"Error getting URL: {e!s}"

                # Use _execute_parallel_operation for parallel execution
                results_dict = self._execute_parallel_operation(
                    get_single_tab_url, valid_tabs
                )

                # Process results and filter out failed captures
                final_results = {}
                for tid in valid_tabs:
                    if tid in results_dict:
                        result = results_dict[tid]
                        if not result[1].startswith("Error getting URL"):
                            final_results[tid] = result[1]
                        else:
                            logger.warning(f"Failed to get URL for tab {tid}")

                return final_results

            except ValueError as e:
                # Don't wrap the error message - pass it through as-is
                raise e

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def click_id(
        self,
        identifier: Union[str, int, Dict[int, Union[str, int]]],
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Click an element with the given identifier on the current page, a specific tab, or multiple tabs simultaneously.

        Supports clicking on different elements on different tabs by providing a dictionary mapping tab IDs to identifiers.

        Args:
            identifier (Union[str, int, Dict[int, Union[str, int]]]): The identifier of the element to click.
                Can be a single identifier (str/int) for all tabs, or a dictionary mapping tab IDs to specific identifiers.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to click on.
                If None, uses the current active page. If int, clicks on single tab.
                If List[int], clicks on multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the click action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
            ValueError: If identifier is a dict but tab_id is not provided or doesn't match dict keys.
        """
        # Handle single tab or current page click
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Get the identifier for this specific tab
            if isinstance(identifier, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "When identifier is a dictionary, tab_id must be specified"
                    )
                if single_tab_id not in identifier:
                    raise ValueError(
                        f"Tab {single_tab_id} not found in identifier dictionary"
                    )
                element_id = identifier[single_tab_id]
            else:
                element_id = identifier

            # Convert identifier to string if it's an integer
            if isinstance(element_id, int):
                element_id = str(element_id)

            target = target_page.locator(f"[__elementId='{element_id}']")

            try:
                target.wait_for(timeout=5000)
            except Exception as e:
                logger.debug(f"Error during click operation: {e}")
                raise ValueError("No such element.") from None

            target.scroll_into_view_if_needed()

            new_page = None
            try:
                with target_page.expect_event(
                    "popup", timeout=1000
                ) as page_info:
                    box: Optional[FloatRect] = target.bounding_box()
                    if box is None:
                        logger.warning(
                            f"Bounding box not found for element '{element_id}'. "
                            f"Cannot click."
                        )
                        return f"Bounding box not found for element '{element_id}'. Cannot click."
                    target_page.mouse.click(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                    )
                    new_page = page_info.value

                    # If a new page is opened, switch to it
                    if new_page:
                        self.page_history.append(deepcopy(target_page.url))
                        if new_page is not None:
                            target_page = new_page
                            # Update the tabs dict if this was a specific tab
                            if single_tab_id is not None:
                                self.tabs[single_tab_id] = new_page

            except Exception as e:
                logger.debug(f"Error during click operation: {e}")
                pass

            self._wait_for_load()
            return f"Successfully clicked element '{element_id}'."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Validate identifier dictionary if provided
            if isinstance(identifier, dict):
                missing_tabs = [tid for tid in tab_id if tid not in identifier]
                if missing_tabs:
                    raise ValueError(
                        f"Tabs {missing_tabs} not found in identifier dictionary"
                    )

            # Define the click operation function
            def click_single_tab(tid: int) -> Tuple[int, Tuple[bool, str]]:
                """Click on an element in a single tab."""
                try:
                    page = self.tabs[tid]

                    # Get the identifier for this specific tab
                    if isinstance(identifier, dict):
                        element_id = identifier[tid]
                    else:
                        element_id = identifier

                    # Convert identifier to string if it's an integer
                    if isinstance(element_id, int):
                        element_id = str(element_id)

                    target = page.locator(f"[__elementId='{element_id}']")

                    try:
                        target.wait_for(timeout=5000)
                    except Exception as e:
                        logger.debug(
                            f"Error during click operation on tab {tid}: {e}"
                        )
                        return tid, (
                            False,
                            f"Element '{element_id}' not found on tab {tid}",
                        )

                    target.scroll_into_view_if_needed()

                    new_page = None
                    try:
                        with page.expect_event(
                            "popup", timeout=1000
                        ) as page_info:
                            box: Optional[FloatRect] = target.bounding_box()
                            if box is None:
                                logger.warning(
                                    f"Bounding box not found for element '{element_id}' on tab {tid}. "
                                    f"Cannot click."
                                )
                                return tid, (
                                    False,
                                    f"Bounding box not found for element '{element_id}' on tab {tid}",
                                )

                            page.mouse.click(
                                box["x"] + box["width"] / 2,
                                box["y"] + box["height"] / 2,
                            )
                            new_page = page_info.value

                            # If a new page is opened, update the tabs dict
                            if new_page:
                                self.tabs[tid] = new_page

                    except Exception as e:
                        logger.debug(
                            f"Error during click operation on tab {tid}: {e}"
                        )
                        pass

                    # Wait for load on this specific tab
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability

                    return tid, (
                        True,
                        f"Successfully clicked element '{element_id}' on tab {tid}",
                    )

                except Exception as e:
                    logger.error(f"Error clicking on tab {tid}: {e}")
                    return tid, (
                        False,
                        f"Error clicking on tab {tid}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                click_single_tab, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if click was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to click on tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def extract_url_content(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, str]]:
        r"""Extract the content of the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to extract content from.
                If None, uses the current active page. If int, extracts content from single tab.
                If List[int], extracts content from multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, str]]: For single tab: string content of the page.
                For multiple tabs: dictionary mapping tab IDs to string content.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page content extraction
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            content = target_page.content()
            return content

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the content extraction operation function
            def extract_single_tab_content(tid: int) -> Tuple[int, str]:
                """Extract content for a single tab."""
                try:
                    page = self.tabs[tid]
                    content = page.content()
                    return tid, content
                except Exception as e:
                    logger.error(
                        f"Error extracting content for tab {tid}: {e}"
                    )
                    return tid, f"Error extracting content: {e!s}"

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                extract_single_tab_content, valid_tabs
            )

            # Process results and filter out failed extractions
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if not result[1].startswith(
                        "Error extracting content"
                    ):  # Check if content was extracted successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to extract content for tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def download_file_id(
        self,
        identifier: Union[str, int, Dict[int, Union[str, int]]],
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Download a file with the given identifier from the current page, a specific tab, or multiple tabs simultaneously.

        Supports downloading different files from different tabs by providing a dictionary mapping tab IDs to identifiers.

        Args:
            identifier (Union[str, int, Dict[int, Union[str, int]]]): The identifier of the file to download.
                Can be a single identifier (str/int) for all tabs, or a dictionary mapping tab IDs to specific identifiers.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to download from.
                If None, uses the current active page. If int, downloads from single tab.
                If List[int], downloads from multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the download action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
            ValueError: If identifier is a dict but tab_id is not provided or doesn't match dict keys.
        """
        # Handle single tab or current page download
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Get the identifier for this specific tab
            if isinstance(identifier, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "When identifier is a dictionary, tab_id must be specified"
                    )
                if single_tab_id not in identifier:
                    raise ValueError(
                        f"Tab {single_tab_id} not found in identifier dictionary"
                    )
                element_id = identifier[single_tab_id]
            else:
                element_id = identifier

            # Convert identifier to string if it's an integer
            if isinstance(element_id, int):
                element_id = str(element_id)

            try:
                target = target_page.locator(f"[__elementId='{element_id}']")
            except Exception as e:
                logger.debug(f"Error during download operation: {e}")
                logger.warning(
                    f"Element with identifier '{element_id}' not found."
                )
                return f"Element with identifier '{element_id}' not found."

            target.scroll_into_view_if_needed()

            file_path_val = os.path.join(self.cache_dir)
            self._wait_for_load()

            try:
                with target_page.expect_download() as download_info:
                    target.click()
                    download = download_info.value
                    file_name = download.suggested_filename

                    file_path_val = os.path.join(file_path_val, file_name)
                    download.save_as(file_path_val)

                return f"Downloaded file to path '{file_path_val}'."

            except Exception as e:
                logger.debug(f"Error during download operation: {e}")
                return (
                    f"Failed to download file with identifier '{element_id}'."
                )

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Validate identifier dictionary if provided
            if isinstance(identifier, dict):
                missing_tabs = [tid for tid in tab_id if tid not in identifier]
                if missing_tabs:
                    raise ValueError(
                        f"Tabs {missing_tabs} not found in identifier dictionary"
                    )

            # Define the download operation function
            def download_single_tab_file(
                tid: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Download file from a single tab."""
                try:
                    page = self.tabs[tid]

                    # Get the identifier for this specific tab
                    if isinstance(identifier, dict):
                        element_id = identifier[tid]
                    else:
                        element_id = identifier

                    # Convert identifier to string if it's an integer
                    if isinstance(element_id, int):
                        element_id = str(element_id)

                    try:
                        target = page.locator(f"[__elementId='{element_id}']")
                    except Exception as e:
                        logger.debug(
                            f"Error during download operation on tab {tid}: {e}"
                        )
                        return tid, (
                            False,
                            f"Element with identifier '{element_id}' not found on tab {tid}",
                        )

                    target.scroll_into_view_if_needed()

                    file_path_val = os.path.join(self.cache_dir)
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability

                    try:
                        with page.expect_download() as download_info:
                            target.click()
                            download = download_info.value
                            file_name = download.suggested_filename

                            file_path_val = os.path.join(
                                file_path_val, file_name
                            )
                            download.save_as(file_path_val)

                        return tid, (
                            True,
                            f"Downloaded file to path '{file_path_val}' from tab {tid}",
                        )

                    except Exception as e:
                        logger.debug(
                            f"Error during download operation on tab {tid}: {e}"
                        )
                        return tid, (
                            False,
                            f"Failed to download file with identifier '{element_id}' from tab {tid}",
                        )

                except Exception as e:
                    logger.error(f"Error downloading file from tab {tid}: {e}")
                    return tid, (
                        False,
                        f"Error downloading file from tab {tid}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                download_single_tab_file, valid_tabs
            )

            # Process results and filter out failed downloads
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if download was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to download file from tab {tid}: {result[1][1]}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def fill_input_id(
        self,
        identifier: Union[str, int, Dict[int, Union[str, int]]],
        text: Union[str, Dict[int, str]],
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Fill an input field with the given text, and then press Enter for the current page, a specific tab, or multiple tabs simultaneously.

        Supports filling different input fields on different tabs by providing dictionaries mapping tab IDs to identifiers and texts.

        Args:
            identifier (Union[str, int, Dict[int, Union[str, int]]]): The identifier of the input field to fill.
                Can be a single identifier (str/int) for all tabs, or a dictionary mapping tab IDs to specific identifiers.
            text (Union[str, Dict[int, str]]): The text to fill in the input field.
                Can be a single text string for all tabs, or a dictionary mapping tab IDs to specific texts.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to fill input on.
                If None, uses the current active page. If int, fills input on single tab.
                If List[int], fills input on multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the fill action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
            ValueError: If identifier/text is a dict but tab_id is not provided or doesn't match dict keys.
        """
        # Handle single tab or current page fill
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Get the identifier and text for this specific tab
            if isinstance(identifier, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "When identifier is a dictionary, tab_id must be specified"
                    )
                if single_tab_id not in identifier:
                    raise ValueError(
                        f"Tab {single_tab_id} not found in identifier dictionary"
                    )
                element_id = identifier[single_tab_id]
            else:
                element_id = identifier

            if isinstance(text, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "When text is a dictionary, tab_id must be specified"
                    )
                if single_tab_id not in text:
                    raise ValueError(
                        f"Tab {single_tab_id} not found in text dictionary"
                    )
                fill_text = text[single_tab_id]
            else:
                fill_text = text

            # Convert identifier to string if it's an integer
            if isinstance(element_id, int):
                element_id = str(element_id)

            try:
                target = target_page.locator(f"[__elementId='{element_id}']")
            except Exception as e:  # Consider using playwright specific
                # TimeoutError
                logger.debug(f"Error during fill operation: {e}")
                logger.warning(
                    f"Element with identifier '{element_id}' not found."
                )
                return f"Element with identifier '{element_id}' not found."

            target.scroll_into_view_if_needed()
            target.focus()
            try:
                target.fill(fill_text)
            except Exception as e:  # Consider using playwright specific
                # TimeoutError
                logger.debug(f"Error during fill operation: {e}")
                target.press_sequentially(fill_text)

            target.press("Enter")
            self._wait_for_load()
            return (
                f"Filled input field '{element_id}' with text '{fill_text}' "
                f"and pressed Enter."
            )

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Validate identifier and text dictionaries if provided
            if isinstance(identifier, dict):
                missing_tabs = [tid for tid in tab_id if tid not in identifier]
                if missing_tabs:
                    raise ValueError(
                        f"Tabs {missing_tabs} not found in identifier dictionary"
                    )

            if isinstance(text, dict):
                missing_tabs = [tid for tid in tab_id if tid not in text]
                if missing_tabs:
                    raise ValueError(
                        f"Tabs {missing_tabs} not found in text dictionary"
                    )

            # Define the fill input operation function
            def fill_single_tab_input(
                tab_id: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Fill input on a single tab."""
                try:
                    page = self.tabs[tab_id]

                    # Get the identifier and text for this specific tab
                    if isinstance(identifier, dict):
                        element_id = identifier[tab_id]
                    else:
                        element_id = identifier

                    if isinstance(text, dict):
                        fill_text = text[tab_id]
                    else:
                        fill_text = text

                    # Convert identifier to string if it's an integer
                    if isinstance(element_id, int):
                        element_id = str(element_id)

                    try:
                        target = page.locator(f"[__elementId='{element_id}']")
                    except (
                        Exception
                    ) as e:  # Consider using playwright specific
                        # TimeoutError
                        logger.debug(
                            f"Error during fill operation on tab {tab_id}: {e}"
                        )
                        return tab_id, (
                            False,
                            f"Element with identifier '{element_id}' not found on tab {tab_id}",
                        )

                    target.scroll_into_view_if_needed()
                    target.focus()
                    try:
                        target.fill(fill_text)
                    except (
                        Exception
                    ) as e:  # Consider using playwright specific
                        # TimeoutError
                        logger.debug(
                            f"Error during fill operation on tab {tab_id}: {e}"
                        )
                        target.press_sequentially(fill_text)

                    target.press("Enter")
                    # Wait for load on this specific tab
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability

                    return tab_id, (
                        True,
                        f"Filled input field '{element_id}' with text '{fill_text}' and pressed Enter on tab {tab_id}",
                    )

                except Exception as e:
                    logger.error(f"Error filling input on tab {tab_id}: {e}")
                    return tab_id, (
                        False,
                        f"Error filling input on tab {tab_id}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                fill_single_tab_input, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if fill was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to fill input on tab {tid}: {result[1][1]}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def scroll_to_bottom(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Scroll to the bottom of the page for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to scroll to bottom.
                If None, uses the current active page. If int, scrolls to bottom of single tab.
                If List[int], scrolls to bottom of multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the scroll action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page scroll
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            target_page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            self._wait_for_load()
            return "Successfully scrolled to the bottom of the page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the scroll to bottom operation function
            def scroll_single_tab_to_bottom(
                tab_id: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Scroll to bottom for a single tab."""
                try:
                    page = self.tabs[tab_id]
                    page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability
                    return tab_id, (
                        True,
                        f"Successfully scrolled to bottom of tab {tab_id}",
                    )
                except Exception as e:
                    logger.error(
                        f"Error scrolling to bottom of tab {tab_id}: {e}"
                    )
                    return tab_id, (
                        False,
                        f"Error scrolling to bottom of tab {tab_id}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                scroll_single_tab_to_bottom, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if scroll was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to scroll to bottom of tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def scroll_to_top(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Scroll to the top of the page for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to scroll to top.
                If None, uses the current active page. If int, scrolls to top of single tab.
                If List[int], scrolls to top of multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the scroll action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page scroll
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            target_page.evaluate("window.scrollTo(0, 0);")
            self._wait_for_load()
            return "Successfully scrolled to the top of the page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the scroll to top operation function
            def scroll_single_tab_to_top(
                tab_id: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Scroll to top for a single tab."""
                try:
                    page = self.tabs[tab_id]
                    page.evaluate("window.scrollTo(0, 0);")
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability
                    return tab_id, (
                        True,
                        f"Successfully scrolled to top of tab {tab_id}",
                    )
                except Exception as e:
                    logger.error(
                        f"Error scrolling to top of tab {tab_id}: {e}"
                    )
                    return tab_id, (
                        False,
                        f"Error scrolling to top of tab {tab_id}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                scroll_single_tab_to_top, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if scroll was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to scroll to top of tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def hover_id(
        self,
        identifier: Union[str, int, Dict[int, Union[str, int]]],
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Hover over an element with the given identifier on the current page, a specific tab, or multiple tabs simultaneously.

        Supports hovering over different elements on different tabs by providing a dictionary mapping tab IDs to identifiers.

        Args:
            identifier (Union[str, int, Dict[int, Union[str, int]]]): The identifier of the element to hover over.
                Can be a single identifier (str/int) for all tabs, or a dictionary mapping tab IDs to specific identifiers.
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to hover on.
                If None, uses the current active page. If int, hovers on single tab.
                If List[int], hovers on multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: success message.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
            ValueError: If identifier is a dict but tab_id is not provided or doesn't match dict keys.
        """
        # Handle single tab or current page hover
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            # Get the identifier for this specific tab
            if isinstance(identifier, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "When identifier is a dictionary, tab_id must be specified"
                    )
                if single_tab_id not in identifier:
                    raise ValueError(
                        f"Tab {single_tab_id} not found in identifier dictionary"
                    )
                element_id = identifier[single_tab_id]
            else:
                element_id = identifier

            # Convert identifier to string if it's an integer
            if isinstance(element_id, int):
                element_id = str(element_id)

            try:
                target = target_page.locator(f"[__elementId='{element_id}']")
            except Exception as e:
                logger.debug(f"Error during hover operation: {e}")
                logger.warning(
                    f"Element with identifier '{element_id}' not found."
                )
                return f"Element with identifier '{element_id}' not found."

            target.scroll_into_view_if_needed()
            target.hover()
            self._wait_for_load()
            return f"Hovered over element with identifier '{element_id}'."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Validate identifier dictionary if provided
            if isinstance(identifier, dict):
                missing_tabs = [tid for tid in tab_id if tid not in identifier]
                if missing_tabs:
                    raise ValueError(
                        f"Tabs {missing_tabs} not found in identifier dictionary"
                    )

            # Define the hover operation function
            def hover_single_tab(tab_id: int) -> Tuple[int, Tuple[bool, str]]:
                """Hover over an element in a single tab."""
                try:
                    page = self.tabs[tab_id]

                    # Get the identifier for this specific tab
                    if isinstance(identifier, dict):
                        element_id = identifier[tab_id]
                    else:
                        element_id = identifier

                    # Convert identifier to string if it's an integer
                    if isinstance(element_id, int):
                        element_id = str(element_id)

                    try:
                        target = page.locator(f"[__elementId='{element_id}']")
                    except Exception as e:
                        logger.debug(
                            f"Error during hover operation on tab {tab_id}: {e}"
                        )
                        return tab_id, (
                            False,
                            f"Element '{element_id}' not found on tab {tab_id}",
                        )

                    target.scroll_into_view_if_needed()
                    target.hover()

                    # Wait for load on this specific tab
                    page.wait_for_load_state("load", timeout=20000)
                    time.sleep(2)  # Additional wait for stability

                    return tab_id, (
                        True,
                        f"Hovered over element with identifier '{element_id}' on tab {tab_id}",
                    )

                except Exception as e:
                    logger.error(f"Error hovering on tab {tab_id}: {e}")
                    return tab_id, (
                        False,
                        f"Error hovering on tab {tab_id}: {e!s}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                hover_single_tab, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if hover was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to hover on tab {tid}: {result[1][1]}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def find_text_on_page(
        self,
        search_text: Union[str, Dict[int, str]],
        tab_id: Optional[Union[int, List[int]]] = None,
    ) -> Union[str, Dict[int, str]]:
        r"""Find the next given text on the page, and scroll the page to the
        targeted text. It is equivalent to pressing Ctrl + F and searching for
        the text.

        Args:
            search_text (Union[str, Dict[int, str]]): The text to search for on the page.
                If str, uses the same text for all specified tabs.
                If Dict[int, str], uses different text for each tab (key is tab_id, value is search text).
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to search in.
                If None, uses the current active page. If int, searches in single tab.
                If List[int], searches in multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, str]]: For single tab: string result of the search.
                For multiple tabs: dictionary mapping tab IDs to search results.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
            ValueError: If search_text is a dict but tab_id is not a list, or if dict keys don't match tab_ids.
        """
        # Handle single tab or current page search
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id

            # Validate search_text for single tab
            if isinstance(search_text, dict):
                if single_tab_id is None:
                    raise ValueError(
                        "search_text cannot be a dict when tab_id is None (current page)"
                    )
                if single_tab_id not in search_text:
                    raise ValueError(
                        f"search_text dict must contain key for tab {single_tab_id}"
                    )
                actual_search_text = search_text[single_tab_id]
            else:
                actual_search_text = search_text

            target_page, _ = self._get_target_page(single_tab_id)

            # Perform the search
            script = f"""
            (function() {{ 
                let text = "{actual_search_text}";
                let found = window.find(text);
                if (!found) {{
                    let elements = document.querySelectorAll("*:not(script):not(style)"); 
                    for (let el of elements) {{
                        if (el.innerText && el.innerText.includes(text)) {{
                            el.scrollIntoView({{behavior: "smooth", block: "center"}});
                            el.style.backgroundColor = "yellow";
                            el.style.border = '2px solid red';
                            return true;
                        }}
                    }}
                    return false;
                }}
                return true;
            }})();
            """
            found_eval = target_page.evaluate(script)
            found = cast(bool, found_eval)  # Ensure found is bool
            self._wait_for_load()
            if found:
                return f"Found text '{actual_search_text}' on the page."
            else:
                return f"Text '{actual_search_text}' not found on the page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Prepare search text mapping for multiple tabs
            if isinstance(search_text, dict):
                # Validate that all tab_ids have corresponding search text
                missing_tabs = [
                    tid for tid in tab_id if tid not in search_text
                ]
                if missing_tabs:
                    raise ValueError(
                        f"search_text dict missing keys for tabs: {missing_tabs}"
                    )
                search_text_mapping = search_text
            else:
                # Use the same search text for all tabs
                search_text_mapping = {tid: search_text for tid in tab_id}

            # Define the search text operation function
            def find_text_single_tab(tab_id: int) -> Tuple[int, str]:
                """Search text in a single tab."""
                try:
                    page = self.tabs[tab_id]
                    tab_search_text = search_text_mapping[tab_id]
                    script = f"""
                    (function() {{ 
                        let text = "{tab_search_text}";
                        let found = window.find(text);
                        if (!found) {{
                            let elements = document.querySelectorAll("*:not(script):not(style)"); 
                            for (let el of elements) {{
                                if (el.innerText && el.innerText.includes(text)) {{
                                    el.scrollIntoView({{behavior: "smooth", block: "center"}});
                                    el.style.backgroundColor = "yellow";
                                    el.style.border = '2px solid red';
                                    return true;
                                }}
                            }}
                            return false;
                        }}
                        return true;
                    }})();
                    """
                    found_eval = page.evaluate(script)
                    found = bool(found_eval)  # Ensure found is bool
                    self._wait_for_load()
                    if found:
                        return (
                            tab_id,
                            f"Found text '{tab_search_text}' on the page.",
                        )
                    else:
                        return (
                            tab_id,
                            f"Text '{tab_search_text}' not found on the page.",
                        )
                except Exception as e:
                    logger.error(f"Error searching text in tab {tab_id}: {e}")
                    return tab_id, f"Error searching text: {e!s}"

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                find_text_single_tab, valid_tabs
            )

            # Process results and filter out failed searches
            final_results: Dict[int, str] = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if not result[1].startswith(
                        "Error searching text"
                    ):  # Check if search was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(f"Failed to search text in tab {tid}")

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def back(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Navigate back to the previous page for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to navigate back in.
                If None, uses the current active page. If int, navigates back in single tab.
                If List[int], navigates back in multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the navigation action.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page navigation
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page, _ = self._get_target_page(single_tab_id)

            page_url_before = target_page.url
            target_page.go_back()

            page_url_after = target_page.url

            if page_url_before == page_url_after:
                # If the page is not changed, try to use the history
                if len(self.page_history) > 0:
                    self.visit_page(self.page_history.pop())

            time.sleep(1)
            self._wait_for_load()
            return "Successfully navigated back to the previous page."

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the navigate back operation function
            def navigate_single_tab_back(
                tab_id: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                try:
                    target_page = self.tabs[tab_id]
                    page_url_before = target_page.url
                    target_page.go_back()

                    page_url_after = target_page.url

                    if page_url_after == "about:blank":
                        self.visit_page(page_url_before)

                    if page_url_before == page_url_after:
                        # If the page is not changed, try to use the history
                        if len(self.page_history) > 0:
                            self.visit_page(self.page_history.pop())

                    time.sleep(1)
                    self._wait_for_load()
                    return tab_id, (True, "Successfully navigated back")
                except Exception as e:
                    return tab_id, (False, f"Error navigating back: {e!s}")

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                navigate_single_tab_back, valid_tabs
            )

            # Process results and filter out failed navigations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if navigation was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to navigate back in tab {tid}: {result[1][1]}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def close(self):
        if self.context is not None:
            self.context.close()
        if (
            self.browser is not None
        ):  # Only close browser if it was launched separately
            self.browser.close()
        if self.playwright:
            self.playwright.stop()  # Stop playwright instance

    # ruff: noqa: E501
    def show_interactive_elements(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, Tuple[bool, str]]]:
        r"""Show simple interactive elements on the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to show interactive elements for.
                If None, uses the current active page. If int, shows elements for single tab.
                If List[int], shows elements for multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, Tuple[bool, str]]]: For single tab: string result of the operation.
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        # Handle single tab or current page interactive elements
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page = None

            if single_tab_id is not None:
                # Show interactive elements for specific tab
                if single_tab_id not in self.tabs:
                    raise ValueError(f"Tab {single_tab_id} does not exist")

                target_page = self.tabs[single_tab_id]
                if target_page.is_closed():
                    del self.tabs[single_tab_id]
                    raise ValueError(f"Tab {single_tab_id} has been closed")
            else:
                # Show interactive elements for current active page
                if self.page is None:
                    raise ValueError("No active page available")
                target_page = self.page

            try:
                target_page.evaluate(self.page_script)
                target_page.evaluate("""
                () => {
                    document.querySelectorAll('a, button, input, select, textarea, 
                    [tabindex]:not([tabindex="-1"]), 
                    [contenteditable="true"]').forEach(el => {
                        el.style.border = '2px solid red';
                    });
                }
                """)
                return "Successfully highlighted interactive elements on the page."
            except Exception as e:
                logger.warning(f"Error showing interactive elements: {e}")
                return f"Error showing interactive elements: {e}"

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use the existing validation helper method
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Function to show interactive elements for a single tab
            def show_single_tab_interactive_elements(
                tab_id: int,
            ) -> Tuple[int, Tuple[bool, str]]:
                """Show interactive elements for a single tab."""
                try:
                    page = self.tabs[tab_id]
                    page.evaluate(self.page_script)
                    page.evaluate("""
                    () => {
                        document.querySelectorAll('a, button, input, select, textarea, 
                        [tabindex]:not([tabindex="-1"]), 
                        [contenteditable="true"]').forEach(el => {
                            el.style.border = '2px solid red';
                        });
                    }
                    """)
                    return tab_id, (
                        True,
                        "Interactive elements highlighted successfully",
                    )
                except Exception as e:
                    logger.error(
                        f"Error showing interactive elements for tab {tab_id}: {e}"
                    )
                    return tab_id, (
                        False,
                        f"Failed to show interactive elements: {e}",
                    )

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                show_single_tab_interactive_elements, valid_tabs
            )

            # Process results and filter out failed operations
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if result[1][0]:  # Check if operation was successful
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to show interactive elements for tab {tid}: {result[1][1]}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    @retry_on_error()
    def get_webpage_content(
        self, tab_id: Optional[Union[int, List[int]]] = None
    ) -> Union[str, Dict[int, str]]:
        r"""Get the webpage content as markdown for the current page, a specific tab, or multiple tabs simultaneously.

        Args:
            tab_id (Optional[Union[int, List[int]]]): The ID(s) of the tab(s) to get content from.
                If None, uses the current active page. If int, gets content from single tab.
                If List[int], gets content from multiple tabs simultaneously.

        Returns:
            Union[str, Dict[int, str]]: For single tab: markdown content of the page.
                For multiple tabs: dictionary mapping tab IDs to markdown content.

        Raises:
            ValueError: If any of the specified tab_ids do not exist or refer to closed tabs.
        """
        try:
            from html2text import html2text  # type: ignore[import-not-found]
        except ImportError:
            # Fallback if html2text is not available
            def html2text(
                html: str, baseurl: str = "", bodywidth: Optional[int] = None
            ) -> str:
                """Simple fallback HTML to text converter."""
                import re

                # Remove HTML tags
                text = re.sub(r'<[^>]+>', '', html)
                # Decode HTML entities
                import html as html_module

                text = html_module.unescape(text)
                # Remove extra whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                return text

        # Handle single tab or current page content extraction
        if tab_id is None or isinstance(tab_id, int):
            single_tab_id = tab_id
            target_page = None

            if single_tab_id is not None:
                # Get content from specific tab
                if single_tab_id not in self.tabs:
                    raise ValueError(f"Tab {single_tab_id} does not exist")

                target_page = self.tabs[single_tab_id]
                if target_page.is_closed():
                    del self.tabs[single_tab_id]
                    raise ValueError(f"Tab {single_tab_id} has been closed")
            else:
                # Get content from current active page
                if self.page is None:
                    raise ValueError("No active page available")
                target_page = self.page

            self._wait_for_load()
            html_content = target_page.content()
            markdown_content = html2text(html_content)
            return markdown_content

        # Handle multiple tabs simultaneously
        elif isinstance(tab_id, list):
            if not tab_id:
                return {}

            # Use _validate_tab_ids for validation
            valid_tabs, _ = self._validate_tab_ids(tab_id)

            # Define the content extraction operation function
            def get_single_tab_content(tid: int) -> Tuple[int, str]:
                """Get webpage content for a single tab."""
                try:
                    page = self.tabs[tid]
                    self._wait_for_load()
                    html_content = page.content()
                    markdown_content = html2text(html_content)
                    return tid, markdown_content
                except Exception as e:
                    logger.error(
                        f"Error getting webpage content for tab {tid}: {e}"
                    )
                    return tid, f"Error getting webpage content: {e!s}"

            # Use _execute_parallel_operation for parallel execution
            results_dict = self._execute_parallel_operation(
                get_single_tab_content, valid_tabs
            )

            # Process results and filter out failed extractions
            final_results = {}
            for tid in tab_id:
                if tid in results_dict:
                    result = results_dict[tid]
                    if not result[1].startswith(
                        "Error getting webpage content"
                    ):  # Check if content was extracted successfully
                        final_results[tid] = result[1]
                    else:
                        logger.warning(
                            f"Failed to get webpage content for tab {tid}"
                        )

            return final_results

        else:
            raise TypeError(
                "tab_id must be None, an integer, or a list of integers"
            )

    def _ensure_browser_installed(self) -> None:
        r"""Ensure the browser is installed."""
        import platform
        import subprocess
        import sys

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(channel=self.channel)
                browser.close()
        except Exception:
            logger.info("Installing Chromium browser...")
            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "playwright",
                        "install",
                        self.channel,
                    ],
                    check=True,
                    capture_output=True,
                )
                if platform.system().lower() == "linux":
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "playwright",
                            "install-deps",
                            self.channel,
                        ],
                        check=True,
                        capture_output=True,
                    )
                logger.info("Chromium browser installation completed")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to install browser: {e.stderr}")

    def _validate_tab_ids(
        self, tab_ids: Union[int, List[int], None]
    ) -> Tuple[List[int], List[int]]:
        """Validate tab IDs and return valid tabs and closed tabs."""
        if tab_ids is None:
            return [], []

        if isinstance(tab_ids, int):
            tab_ids = [tab_ids]

        # Validate all tab IDs
        invalid_tabs = [tid for tid in tab_ids if tid not in self.tabs]
        if invalid_tabs:
            raise ValueError(f"Tabs {invalid_tabs} do not exist")

        # Check for closed tabs
        closed_tabs = []
        valid_tabs = []
        for tid in tab_ids:
            if self.tabs[tid].is_closed():
                closed_tabs.append(tid)
                del self.tabs[tid]
            else:
                valid_tabs.append(tid)

        if closed_tabs:
            raise ValueError(f"Tabs {closed_tabs} have been closed")

        return valid_tabs, closed_tabs

    def _get_target_page(
        self, tab_id: Optional[int] = None
    ) -> Tuple[Any, Optional[int]]:
        """Get target page and tab ID for single tab operations."""
        if tab_id is not None:
            if tab_id not in self.tabs:
                raise ValueError(f"Tab {tab_id} does not exist")

            target_page = self.tabs[tab_id]
            if target_page.is_closed():
                del self.tabs[tab_id]
                raise ValueError(f"Tab {tab_id} has been closed")
        else:
            if self.page is None:
                raise ValueError("No active page available")
            target_page = self.page

        return target_page, tab_id

    def _execute_parallel_operation(
        self, operation_func: Callable, tab_ids: List[int], **kwargs
    ) -> Dict[int, Any]:
        """Execute an operation in parallel across multiple tabs.

        Args:
            operation_func: Function to execute for each tab (should take tab_id as first arg)
            tab_ids: List of tab IDs to operate on
            **kwargs: Additional arguments to pass to operation_func

        Returns:
            Dictionary mapping tab IDs to operation results
        """
        threads = []
        results = {}

        for tid in tab_ids:
            thread = threading.Thread(
                target=lambda t=tid: results.update(
                    {t: operation_func(t, **kwargs)}
                )
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return results


class BrowserToolkit(BaseToolkit):
    r"""A class for browsing the web and interacting with web pages.

    This class provides methods for browsing the web and interacting with web
    pages.
    """

    def __init__(
        self,
        headless: bool = False,
        cache_dir: Optional[str] = None,
        channel: Literal["chrome", "msedge", "chromium"] = "chromium",
        history_window: int = 5,
        web_agent_model: Optional[BaseModelBackend] = None,
        planning_agent_model: Optional[BaseModelBackend] = None,
        output_language: str = "en",
        cookie_json_path: Optional[str] = None,
        user_data_dir: Optional[str] = None,
    ):
        r"""Initialize the BrowserToolkit instance.

        Args:
            headless (bool): Whether to run the browser in headless mode.
            cache_dir (Union[str, None]): The directory to store cache files.
            channel (Literal["chrome", "msedge", "chromium"]): The browser
                channel to use. Must be one of "chrome", "msedge", or
                "chromium".
            history_window (int): The window size for storing the history of
                actions.
            web_agent_model (Optional[BaseModelBackend]): The model backend
                for the web agent.
            planning_agent_model (Optional[BaseModelBackend]): The model
                backend for the planning agent.
            output_language (str): The language to use for output.
                (default: :obj:`"en`")
            cookie_json_path (Optional[str]): Path to a JSON file containing
                authentication cookies and browser storage state. If provided
                and the file exists, the browser will load this state to
                maintain
                authenticated sessions without requiring manual login.
                (default: :obj:`None`)
            user_data_dir (Optional[str]): The directory to store user data
                for persistent context. If None, a fresh browser instance
                is used without saving data. (default: :obj:`None`)
        """
        super().__init__()  # Call to super().__init__() added
        self.browser = BaseBrowser(
            headless=headless,
            cache_dir=cache_dir,
            channel=channel,
            cookie_json_path=cookie_json_path,
            user_data_dir=user_data_dir,
        )
        self.browser.web_agent_model = web_agent_model  # Pass model to
        # BaseBrowser instance

        self.history_window = history_window
        self.web_agent_model = web_agent_model
        self.planning_agent_model = planning_agent_model
        self.output_language = output_language

        self.history: List[Dict[str, Any]] = []  # Typed history list
        self.web_agent: ChatAgent
        self.planning_agent: ChatAgent
        self.web_agent, self.planning_agent = self._initialize_agent(
            web_agent_model, planning_agent_model
        )

    def _reset(self):
        r"""Reset the internal state of the browser toolkit."""

        # Reset agents
        self.web_agent.reset()
        self.planning_agent.reset()
        self.history = []

        os.makedirs(self.browser.cache_dir, exist_ok=True)

        if hasattr(self.browser, 'tabs'):
            for tab_id, page in list(self.browser.tabs.items()):
                if page is not None and not page.is_closed():
                    logger.debug(f"Closing tab {tab_id}")
                    page.close()
            self.browser.tabs.clear()
            self.browser.current_tab_id = None

        self.browser.page = None
        self.browser.page_url = None
        self.browser.page_history = []

    def _initialize_agent(
        self,
        web_agent_model_backend: Optional[BaseModelBackend],
        planning_agent_model_backend: Optional[BaseModelBackend],
    ) -> Tuple[ChatAgent, ChatAgent]:
        r"""Initialize the agent."""
        from camel.agents import ChatAgent

        if web_agent_model_backend is None:
            web_agent_model_instance = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4_1,
                model_config_dict={"temperature": 0, "top_p": 1},
            )
        else:
            web_agent_model_instance = web_agent_model_backend

        if planning_agent_model_backend is None:
            planning_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.O3_MINI,
            )
        else:
            planning_model = planning_agent_model_backend

        system_prompt = WEB_AGENT_SYSTEM_PROMPT

        web_agent = ChatAgent(
            system_message=system_prompt,
            model=web_agent_model_instance,
            output_language=self.output_language,
        )

        planning_system_prompt = PLANNING_AGENT_SYSTEM_PROMPT

        planning_agent = ChatAgent(
            system_message=planning_system_prompt,
            model=planning_model,
            output_language=self.output_language,
        )

        return web_agent, planning_agent

    def _observe(
        self, task_prompt: str, detailed_plan: Optional[str] = None
    ) -> Tuple[str, str, str]:
        r"""Let agent observe the current environment, and get the next
        action."""

        detailed_plan_prompt_str = ""

        if detailed_plan is not None:
            detailed_plan_prompt_str = f"""
Here is a plan about how to solve the task step-by-step which you must follow:
<detailed_plan>{detailed_plan}<detailed_plan>
        """

        tab_info = []
        for tab_id, page in self.browser.tabs.items():
            tab_info.append(f"Tab {tab_id}: {page.url}")

        tab_summary = "\n".join(tab_info) if tab_info else "No tabs open"

        observe_prompt = OBSERVE_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt,
            detailed_plan_prompt=detailed_plan_prompt_str,
            AVAILABLE_ACTIONS_PROMPT=AVAILABLE_ACTIONS_PROMPT,
            history_window=self.history_window,
            history=self.history[-self.history_window :],
            tab_summary=tab_summary,
            current_tab_id=self.browser.current_tab_id,
        )

        # get current state
        # Take screenshots of all open tabs
        all_tab_ids = list(self.browser.tabs.keys())
        if all_tab_ids:
            # Get screenshots for all tabs
            som_screenshots = self.browser.get_som_screenshot(
                save_image=True, tab_id=all_tab_ids
            )

            # Create a dictionary mapping tab IDs to their screenshots
            tab_screenshots = {}
            for tab_id in all_tab_ids:
                if tab_id in som_screenshots:
                    screenshot_result = som_screenshots[tab_id]
                    if (
                        isinstance(screenshot_result, tuple)
                        and len(screenshot_result) >= 2
                    ):
                        screenshot = screenshot_result[0]
                        if screenshot is not None:
                            img = _reload_image(screenshot)
                            tab_screenshots[tab_id] = img

            # Convert to list while maintaining tab ID order
            image_list = []
            for tab_id in all_tab_ids:
                if tab_id in tab_screenshots:
                    image_list.append(tab_screenshots[tab_id])

            # If no screenshots were captured successfully, fall back to current tab
            if not image_list:
                som_screenshot_result = self.browser.get_som_screenshot(
                    save_image=True
                )
                if (
                    isinstance(som_screenshot_result, tuple)
                    and len(som_screenshot_result) >= 2
                ):
                    som_screenshot = som_screenshot_result[0]
                    if som_screenshot is not None:
                        img = _reload_image(som_screenshot)
                        image_list = [img]
        else:
            # Fall back to current tab if no tabs are open
            som_screenshot_result = self.browser.get_som_screenshot(
                save_image=True
            )
            if (
                isinstance(som_screenshot_result, tuple)
                and len(som_screenshot_result) >= 2
            ):
                som_screenshot = som_screenshot_result[0]
                if som_screenshot is not None:
                    img = _reload_image(som_screenshot)
                    image_list = [img]

        message = BaseMessage.make_user_message(
            role_name='user', content=observe_prompt, image_list=image_list
        )
        # Reset the history message of web_agent.
        self.web_agent.reset()
        resp = self.web_agent.step(message)

        resp_content = resp.msgs[0].content

        resp_dict = _parse_json_output(resp_content, logger)  # Pass logger to
        # _parse_json_output
        observation_result: str = resp_dict.get("observation", "")
        reasoning_result: str = resp_dict.get("reasoning", "")
        action_code: str = resp_dict.get("action_code", "")

        if action_code and "(" in action_code and ")" not in action_code:
            action_match = re.search(
                r'"action_code"\s*:\s*[`"]([^`"]*\([^)]*\))[`"]', resp_content
            )
            if action_match:
                action_code = action_match.group(1)
            else:
                logger.warning(
                    f"Incomplete action_code detected: {action_code}"
                )
                if action_code.startswith("fill_input_id("):
                    parts = action_code.split(",", 1)
                    if len(parts) > 1:
                        id_part = (
                            parts[0].replace("fill_input_id(", "").strip()
                        )
                        action_code = (
                            f"fill_input_id({id_part}, 'Please "
                            f"fill the text here.')"
                        )

        action_code = action_code.replace("`", "").strip()

        return observation_result, reasoning_result, action_code

    def _act(
        self, action_code: str
    ) -> Union[Tuple[bool, str], Dict[int, Tuple[bool, str]]]:
        r"""Let agent act based on the given action code.

        Supports multi-tab operations by embedding tab information in the action code.
        Syntax examples:
        - Single tab: "click_id('button1')" (current tab)
        - Single tab: "click_id('button1', tab_id=1)" (specific tab)
        - Multiple tabs: "click_id('button1', tab_id=[1,2,3])" (same action on multiple tabs)
        - Different actions: "{1: 'click_id(\"login\")', 2: 'fill_input_id(\"search\", \"query\")'}" (different actions per tab)

        Args:
            action_code (str): The action code to act. Can include tab information.

        Returns:
            Union[Tuple[bool, str], Dict[int, Tuple[bool, str]]]: For single tab: (success, message).
                For multiple tabs: dictionary mapping tab IDs to (success, message) tuples.
        """

        def _check_if_with_feedback(action_code: str) -> bool:
            r"""Check if the action code needs feedback."""

            for action_with_feedback in ACTION_WITH_FEEDBACK_LIST:
                if action_with_feedback in action_code:
                    return True

            return False

        def _fix_action_code(action_code: str) -> str:
            r"""Fix potential missing quotes in action code for multi-tab operations"""

            # Handle dictionary format for multi-tab actions (e.g., {1: 'login', 2: 'search'})
            if action_code.strip().startswith(
                '{'
            ) and action_code.strip().endswith('}'):
                try:
                    # Parse the dictionary
                    actions_dict = eval(action_code)
                    if not isinstance(actions_dict, dict):
                        return action_code

                    # Fix each action in the dictionary
                    fixed_actions = {}
                    for tab_id, action in actions_dict.items():
                        # Handle both string values and action codes
                        if isinstance(action, str):
                            # If it's a simple string (like 'login'), quote it
                            if not (
                                action.startswith('"')
                                or action.startswith("'")
                            ):
                                fixed_actions[tab_id] = f"'{action}'"
                            else:
                                fixed_actions[tab_id] = action
                        else:
                            # If it's an action code, fix it
                            fixed_actions[tab_id] = _fix_single_action(
                                str(action)
                            )

                    return str(fixed_actions)
                except Exception:
                    return action_code

            # Handle single action (with or without tab_id parameter)
            return _fix_single_action(action_code)

        def _fix_single_action(action_code: str) -> str:
            r"""Fix a single action code by adding missing quotes and handling tab_id"""

            # Handle tab_id as named parameter (legacy format)
            tab_id_match = re.search(
                r'tab_id\s*=\s*(\[[^\]]+\]|\d+)', action_code
            )
            if tab_id_match:
                # Extract and preserve tab_id parameter
                tab_id_str = tab_id_match.group(1)
                # Remove tab_id parameter temporarily for processing
                action_without_tab_id = re.sub(
                    r',\s*tab_id\s*=\s*(\[[^\]]+\]|\d+)', '', action_code
                )

                # Fix the action without tab_id
                fixed_action = _fix_action_arguments(action_without_tab_id)

                # Add tab_id parameter back
                return f"{fixed_action}, tab_id={tab_id_str}"

            return _fix_action_arguments(action_code)

        def _fix_action_arguments(action_code: str) -> str:
            r"""Fix arguments in a single action code with proper handling of complex data structures"""

            match = re.match(r'(\w+)\((.*)\)', action_code)
            if not match:
                return action_code

            func_name, args_str = match.groups()

            # Parse arguments with proper handling of nested structures
            args = _parse_arguments(args_str)

            # Fix arguments
            fixed_args = []
            for arg in args:
                fixed_args.append(_fix_single_argument(arg))

            return f"{func_name}({', '.join(fixed_args)})"

        def _parse_arguments(args_str: str) -> List[str]:
            r"""Parse arguments string, properly handling nested structures like lists and dicts"""

            args = []
            current_arg = ""
            in_quotes = False
            quote_char = None
            brace_level = 0  # Track nested braces for dicts and lists
            bracket_level = 0  # Track nested brackets for lists

            for char in args_str:
                if char in ['"', "'"]:
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                        current_arg += char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                        current_arg += char
                    else:
                        current_arg += char
                elif char == '{':
                    if not in_quotes:
                        brace_level += 1
                    current_arg += char
                elif char == '}':
                    if not in_quotes:
                        brace_level -= 1
                    current_arg += char
                elif char == '[':
                    if not in_quotes:
                        bracket_level += 1
                    current_arg += char
                elif char == ']':
                    if not in_quotes:
                        bracket_level -= 1
                    current_arg += char
                elif (
                    char == ','
                    and not in_quotes
                    and brace_level == 0
                    and bracket_level == 0
                ):
                    args.append(current_arg.strip())
                    current_arg = ""
                else:
                    current_arg += char

            if current_arg:
                args.append(current_arg.strip())

            return args

        def _fix_single_argument(arg: str) -> str:
            r"""Fix a single argument, preserving complex data structures"""

            arg = arg.strip()

            # Already quoted strings
            if (arg.startswith('"') and arg.endswith('"')) or (
                arg.startswith("'") and arg.endswith("'")
            ):
                return arg

            # Numbers (integers, floats, scientific notation, hex)
            if (
                re.match(r'^-?\d+(\.\d+)?$', arg)
                or re.match(r'^-?\d+\.?\d*[eE][-+]?\d+$', arg)
                or re.match(r'^0[xX][0-9a-fA-F]+$', arg)
            ):
                return arg

            # Lists (e.g., [1,2,3])
            if arg.startswith('[') and arg.endswith(']'):
                return arg

            # Dictionaries (e.g., {1: 'login', 2: 'search'})
            if arg.startswith('{') and arg.endswith('}'):
                return arg

            # Boolean values
            if arg.lower() in ['true', 'false', 'none']:
                return arg

            # Default: quote the argument
            return f"'{arg}'"

        action_code = _fix_action_code(action_code)
        prefix = "self.browser."
        code = f"{prefix}{action_code}"

        try:
            if _check_if_with_feedback(action_code):
                # execute code, and get the executed result
                result = eval(code)
                time.sleep(1)
                return True, result

            else:
                exec(code)
                time.sleep(1)
                return True, "Action was successful."

        except Exception as e:
            time.sleep(1)
            return (
                False,
                f"Error while executing the action {action_code}: {e}. "
                f"If timeout, please recheck whether you have provided the "
                f"correct identifier.",
            )

    def _get_final_answer(self, task_prompt: str) -> str:
        r"""Get the final answer based on the task prompt and current
        browser state.
        It is used when the agent thinks that the task can be completed
        without any further action, and answer can be directly found in the
        current viewport.
        """
        # tab information is present in history no need to pass into prompt
        prompt = GET_FINAL_ANSWER_PROMPT_TEMPLATE.format(
            history=self.history, task_prompt=task_prompt
        )

        message = BaseMessage.make_user_message(
            role_name='user',
            content=prompt,
        )
        self.web_agent.reset()  # Reset before step
        resp = self.web_agent.step(message)
        return resp.msgs[0].content

    def _task_planning(self, task_prompt: str, start_url: str) -> str:
        r"""Plan the task based on the given task prompt."""

        planning_prompt = TASK_PLANNING_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt, start_url=start_url
        )

        message = BaseMessage.make_user_message(
            role_name='user', content=planning_prompt
        )
        self.planning_agent.reset()  # Reset before step
        resp = self.planning_agent.step(message)
        return resp.msgs[0].content

    def _task_replanning(
        self, task_prompt: str, detailed_plan: str
    ) -> Tuple[bool, str]:
        r"""Replan the task based on the given task prompt.

        Args:
            task_prompt (str): The original task prompt.
            detailed_plan (str): The detailed plan to replan.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating
            whether the task needs to be replanned, and the replanned schema.
        """

        replanning_prompt = TASK_REPLANNING_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt,
            detailed_plan=detailed_plan,
            history_window=self.history_window,
            history=self.history[-self.history_window :],
        )
        # Reset the history message of planning_agent.
        self.planning_agent.reset()
        resp = self.planning_agent.step(replanning_prompt)
        resp_dict = _parse_json_output(
            resp.msgs[0].content, logger
        )  # Pass logger

        if_need_replan_eval = resp_dict.get("if_need_replan", False)
        if_need_replan = cast(bool, if_need_replan_eval)  # Ensure bool
        replanned_schema: str = resp_dict.get("replanned_schema", "")

        if if_need_replan:
            return True, replanned_schema
        else:
            return False, replanned_schema

    @dependencies_required("playwright")
    def browse_url(
        self, task_prompt: str, start_url: str, round_limit: int = 12
    ) -> str:
        r"""A powerful toolkit which can simulate the browser interaction to
        solve the task which needs multi-step actions.

        Args:
            task_prompt (str): The task prompt to solve.
            start_url (str): The start URL to visit.
            round_limit (int): The round limit to solve the task.
                (default: :obj:`12`).

        Returns:
            str: The simulation result to the task.
        """

        self._reset()
        task_completed = False
        detailed_plan = self._task_planning(task_prompt, start_url)
        logger.debug(f"Detailed plan: {detailed_plan}")

        self.browser.init()
        self.browser.visit_page(start_url)

        for i in range(round_limit):
            observation, reasoning, action_code = self._observe(
                task_prompt, detailed_plan
            )
            logger.debug(f"Observation: {observation}")
            logger.debug(f"Reasoning: {reasoning}")
            logger.debug(f"Action code: {action_code}")
            trajectory_info: Dict[str, Any]
            if "stop" in action_code:
                task_completed = True
                trajectory_info = {  # Typed trajectory_info
                    "round": i,
                    "observation": observation,
                    "thought": reasoning,
                    "action": action_code,
                    "action_if_success": True,
                    "info": None,
                    "current_url": self.browser.get_url(),
                    "current_tab_id": self.browser.current_tab_id,
                    "all_tab_urls": self.browser.get_url(
                        list(self.browser.tabs.keys())
                    )
                    if self.browser.tabs
                    else {},
                    "total_tabs": len(self.browser.tabs),
                }
                self.history.append(trajectory_info)
                break

            else:
                success, info = self._act(action_code)
                if not success:
                    logger.warning(f"Error while executing the action: {info}")

                trajectory_info = {  # Typed trajectory_info
                    "round": i,
                    "observation": observation,
                    "thought": reasoning,
                    "action": action_code,
                    "action_if_success": success,
                    "info": info,
                    "current_url": self.browser.get_url(),
                    "current_tab_id": self.browser.current_tab_id,
                    "all_tab_urls": self.browser.get_url(
                        list(self.browser.tabs.keys())
                    )
                    if self.browser.tabs
                    else {},
                    "total_tabs": len(self.browser.tabs),
                }
                self.history.append(trajectory_info)

                # Replan the task if necessary
                if_need_replan, replanned_schema = self._task_replanning(
                    task_prompt, detailed_plan
                )
                if if_need_replan:
                    detailed_plan = replanned_schema
                    logger.debug(f"Replanned schema: {replanned_schema}")

        simulation_result: str
        if not task_completed:
            simulation_result = f"""
                The task is not completed within the round limit. Please 
                check the last round {self.history_window} information to 
                see if there is any useful information:
                <history>{self.history[-self.history_window :]}</history>
            """

        else:
            simulation_result = self._get_final_answer(task_prompt)

        self.browser.close()  # Close browser after task completion or limit
        # reached
        return simulation_result

    def get_tools(self) -> List[FunctionTool]:
        tools = [FunctionTool(self.browse_url)]
        return tools
