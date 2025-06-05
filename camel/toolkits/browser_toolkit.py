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
import time
import urllib.parse
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
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

        assert self.context is not None
        assert self.page is not None

    def clean_cache(self) -> None:
        r"""Delete the cache directory and its contents."""
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

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
        self, save_image: bool = False
    ) -> Tuple[Image.Image, Union[str, None]]:
        r"""Get a screenshot of the current page.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, str]: A tuple containing the screenshot
            image and the path to the image file if saved, otherwise
            :obj:`None`.
        """
        assert self.page is not None
        image_data = self.page.screenshot(timeout=60000)
        image = Image.open(io.BytesIO(image_data))

        file_path = None
        if save_image:
            # Get url name to form a file name
            # Use urlparser for a safer extraction the url name
            assert self.page_url is not None
            parsed_url = urllib.parse.urlparse(self.page_url)
            # Max length is set to 241 as there are 10 characters for the
            # timestamp and 4 characters for the file extension:
            url_name = sanitize_filename(str(parsed_url.path), max_length=241)
            timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
            file_path = os.path.join(
                self.cache_dir, f"{url_name}_{timestamp}.png"
            )
            with open(file_path, "wb") as f:
                image.save(f, "PNG")
            f.close()

        return image, file_path

    def capture_full_page_screenshots(
        self, scroll_ratio: float = 0.8
    ) -> List[str]:
        r"""Capture full page screenshots by scrolling the page with a buffer
        zone.

        Args:
            scroll_ratio (float): The ratio of viewport height to scroll each
                step. (default: :obj:`0.8`)

        Returns:
            List[str]: A list of paths to the screenshot files.
        """
        screenshots: List[str] = []  # Ensure screenshots is typed
        assert self.page is not None
        scroll_height_eval = self.page.evaluate("document.body.scrollHeight")
        scroll_height = cast(
            float, scroll_height_eval
        )  # Ensure scroll_height is
        # float

        assert self.page.viewport_size is not None
        viewport_height = self.page.viewport_size["height"]
        current_scroll_eval = self.page.evaluate("window.scrollY")
        current_scroll = cast(float, current_scroll_eval)
        # screenshot_index = 1 # This variable is not used

        max_height = scroll_height - viewport_height
        scroll_step = int(viewport_height * scroll_ratio)

        last_height = 0.0  # Initialize last_height as float

        while True:
            logger.debug(
                f"Current scroll: {current_scroll}, max_height: "
                f"{max_height}, step: {scroll_step}"
            )

            _, file_path = self.get_screenshot(save_image=True)
            if file_path is not None:  # Ensure file_path is not None before
                # appending
                screenshots.append(file_path)

            self.page.evaluate(f"window.scrollBy(0, {scroll_step})")
            # Allow time for content to load
            time.sleep(0.5)

            current_scroll_eval = self.page.evaluate("window.scrollY")
            current_scroll = cast(float, current_scroll_eval)
            # Break if there is no significant scroll
            if abs(current_scroll - last_height) < viewport_height * 0.1:
                break

            last_height = current_scroll
            # screenshot_index += 1 # This variable is not used

        return screenshots

    def get_visual_viewport(self) -> VisualViewport:
        r"""Get the visual viewport of the current page.

        Returns:
            VisualViewport: The visual viewport of the current page.
        """
        assert self.page is not None
        try:
            self.page.evaluate(self.page_script)
        except Exception as e:
            logger.warning(f"Error evaluating page script: {e}")

        visual_viewport_eval = self.page.evaluate(
            "MultimodalWebSurfer.getVisualViewport();"
        )
        return visual_viewport_from_dict(
            cast(Dict[str, Any], visual_viewport_eval)
        )

    def get_interactive_elements(self) -> Dict[str, InteractiveRegion]:
        r"""Get the interactive elements of the current page.

        Returns:
            Dict[str, InteractiveRegion]: A dictionary of interactive elements.
        """
        assert self.page is not None
        try:
            self.page.evaluate(self.page_script)
        except Exception as e:
            logger.warning(f"Error evaluating page script: {e}")

        result = cast(
            Dict[str, Dict[str, Any]],
            self.page.evaluate("MultimodalWebSurfer.getInteractiveRects();"),
        )

        typed_results: Dict[str, InteractiveRegion] = {}
        for k in result:
            typed_results[k] = interactive_region_from_dict(result[k])

        return typed_results

    def get_som_screenshot(
        self,
        save_image: bool = False,
    ) -> Tuple[Image.Image, Union[str, None]]:
        r"""Get a screenshot of the current viewport with interactive elements
        marked.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, Union[str, None]]: A tuple containing the
            screenshot image
                and an optional path to the image file if saved, otherwise
                :obj:`None`.
        """

        self._wait_for_load()
        screenshot, _ = self.get_screenshot(save_image=False)
        rects = self.get_interactive_elements()

        file_path: str | None = None
        comp, _, _, _ = _add_set_of_mark(
            screenshot,
            rects,
        )
        if save_image:
            assert self.page_url is not None
            parsed_url = urllib.parse.urlparse(self.page_url)
            # Max length is set to 241 as there are 10 characters for the
            # timestamp and 4 characters for the file extension:
            url_name = sanitize_filename(str(parsed_url.path), max_length=241)
            timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
            file_path = os.path.join(
                self.cache_dir, f"{url_name}_{timestamp}.png"
            )
            with open(file_path, "wb") as f:
                comp.save(f, "PNG")
            f.close()

        return comp, file_path

    def scroll_up(self) -> None:
        r"""Scroll up the page."""
        assert self.page is not None
        self.page.keyboard.press("PageUp")

    def scroll_down(self) -> None:
        r"""Scroll down the page."""
        assert self.page is not None
        self.page.keyboard.press("PageDown")

    def get_url(self) -> str:
        r"""Get the URL of the current page."""
        assert self.page is not None
        return self.page.url

    def click_id(self, identifier: Union[str, int]) -> None:
        r"""Click an element with the given identifier."""
        assert self.page is not None
        if isinstance(identifier, int):
            identifier = str(identifier)
        target = self.page.locator(f"[__elementId='{identifier}']")

        try:
            target.wait_for(timeout=5000)
        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during click operation: {e}")
            raise ValueError("No such element.") from None

        target.scroll_into_view_if_needed()

        new_page = None
        try:
            with self.page.expect_event("popup", timeout=1000) as page_info:
                box: Optional[FloatRect] = target.bounding_box()
                if box is None:
                    logger.warning(
                        f"Bounding box not found for element '{identifier}'. "
                        f"Cannot click."
                    )
                    return
                self.page.mouse.click(
                    box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                )
                new_page = page_info.value

                # If a new page is opened, switch to it
                if new_page:
                    self.page_history.append(deepcopy(self.page.url))
                    self.page = new_page

        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during click operation: {e}")
            pass

        self._wait_for_load()

    def extract_url_content(self) -> str:
        r"""Extract the content of the current page."""
        assert self.page is not None
        content = self.page.content()
        return content

    def download_file_id(self, identifier: Union[str, int]) -> str:
        r"""Download a file with the given selector.

        Args:
            identifier (str): The identifier of the file to download.

        Returns:
            str: The result of the action.
        """
        assert self.page is not None
        if isinstance(identifier, int):
            identifier = str(identifier)
        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during download operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        target.scroll_into_view_if_needed()

        file_path_val = os.path.join(self.cache_dir)
        self._wait_for_load()

        try:
            with self.page.expect_download() as download_info:
                target.click()
                download = download_info.value
                file_name = download.suggested_filename

                file_path_val = os.path.join(file_path_val, file_name)
                download.save_as(file_path_val)

            return f"Downloaded file to path '{file_path_val}'."

        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during download operation: {e}")
            return f"Failed to download file with identifier '{identifier}'."

    def fill_input_id(self, identifier: Union[str, int], text: str) -> str:
        r"""Fill an input field with the given text, and then press Enter.

        Args:
            identifier (str): The identifier of the input field.
            text (str): The text to fill.

        Returns:
            str: The result of the action.
        """
        assert self.page is not None
        if isinstance(identifier, int):
            identifier = str(identifier)

        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during fill operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        target.scroll_into_view_if_needed()
        target.focus()
        try:
            target.fill(text)
        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during fill operation: {e}")
            target.press_sequentially(text)

        target.press("Enter")
        self._wait_for_load()
        return (
            f"Filled input field '{identifier}' with text '{text}' "
            f"and pressed Enter."
        )

    def scroll_to_bottom(self) -> str:
        assert self.page is not None
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        self._wait_for_load()
        return "Scrolled to the bottom of the page."

    def scroll_to_top(self) -> str:
        assert self.page is not None
        self.page.evaluate("window.scrollTo(0, 0);")
        self._wait_for_load()
        return "Scrolled to the top of the page."

    def hover_id(self, identifier: Union[str, int]) -> str:
        r"""Hover over an element with the given identifier.

        Args:
            identifier (str): The identifier of the element to hover over.

        Returns:
            str: The result of the action.
        """
        assert self.page is not None
        if isinstance(identifier, int):
            identifier = str(identifier)
        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except Exception as e:  # Consider using playwright specific
            # TimeoutError
            logger.debug(f"Error during hover operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        target.scroll_into_view_if_needed()
        target.hover()
        self._wait_for_load()
        return f"Hovered over element with identifier '{identifier}'."

    def find_text_on_page(self, search_text: str) -> str:
        r"""Find the next given text on the page, and scroll the page to the
        targeted text. It is equivalent to pressing Ctrl + F and searching for
        the text.
        """
        # ruff: noqa: E501
        assert self.page is not None
        script = f"""
        (function() {{ 
            let text = "{search_text}";
            let found = window.find(text);
            if (!found) {{
                let elements = document.querySelectorAll("*:not(script):not(
                style)"); 
                for (let el of elements) {{
                    if (el.innerText && el.innerText.includes(text)) {{
                        el.scrollIntoView({{behavior: "smooth", block: 
                        "center"}});
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
        found_eval = self.page.evaluate(script)
        found = cast(bool, found_eval)  # Ensure found is bool
        self._wait_for_load()
        if found:
            return f"Found text '{search_text}' on the page."
        else:
            return f"Text '{search_text}' not found on the page."

    def back(self):
        r"""Navigate back to the previous page."""
        assert self.page is not None
        page_url_before = self.page.url
        self.page.go_back()

        page_url_after = self.page.url

        if page_url_after == "about:blank":
            self.visit_page(page_url_before)

        if page_url_before == page_url_after:
            # If the page is not changed, try to use the history
            if len(self.page_history) > 0:
                self.visit_page(self.page_history.pop())

        time.sleep(1)
        self._wait_for_load()

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
    def show_interactive_elements(self):
        r"""Show simple interactive elements on the current page."""
        assert self.page is not None
        self.page.evaluate(self.page_script)
        self.page.evaluate("""
        () => {
            document.querySelectorAll('a, button, input, select, textarea, 
            [tabindex]:not([tabindex="-1"]), 
            [contenteditable="true"]').forEach(el => {
                el.style.border = '2px solid red';
            });
            }
        """)

    @retry_on_error()
    def get_webpage_content(self) -> str:
        from html2text import html2text

        assert self.page is not None
        self._wait_for_load()
        html_content = self.page.content()

        markdown_content = html2text(html_content)
        return markdown_content

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
        self.web_agent.reset()
        self.planning_agent.reset()
        self.history = []
        os.makedirs(self.browser.cache_dir, exist_ok=True)

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

        observe_prompt = OBSERVE_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt,
            detailed_plan_prompt=detailed_plan_prompt_str,
            AVAILABLE_ACTIONS_PROMPT=AVAILABLE_ACTIONS_PROMPT,
            history_window=self.history_window,
            history=self.history[-self.history_window :],
        )

        # get current state
        som_screenshot, _ = self.browser.get_som_screenshot(save_image=True)
        img = _reload_image(som_screenshot)
        message = BaseMessage.make_user_message(
            role_name='user', content=observe_prompt, image_list=[img]
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

    def _act(self, action_code: str) -> Tuple[bool, str]:
        r"""Let agent act based on the given action code.
        Args:
            action_code (str): The action code to act.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether
                the action was successful, and the information to be returned.
        """

        def _check_if_with_feedback(action_code: str) -> bool:
            r"""Check if the action code needs feedback."""

            for action_with_feedback in ACTION_WITH_FEEDBACK_LIST:
                if action_with_feedback in action_code:
                    return True

            return False

        def _fix_action_code(action_code: str) -> str:
            r"""Fix potential missing quotes in action code"""

            match = re.match(r'(\w+)\((.*)\)', action_code)
            if not match:
                return action_code

            func_name, args_str = match.groups()

            args = []
            current_arg = ""
            in_quotes = False
            quote_char = None

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
                elif char == ',' and not in_quotes:
                    args.append(current_arg.strip())
                    current_arg = ""
                else:
                    current_arg += char

            if current_arg:
                args.append(current_arg.strip())

            fixed_args = []
            for arg in args:
                if (
                    (arg.startswith('"') and arg.endswith('"'))
                    or (arg.startswith("'") and arg.endswith("'"))
                    or re.match(r'^-?\d+(\.\d+)?$', arg)
                    or re.match(r'^-?\d+\.?\d*[eE][-+]?\d+$', arg)
                    or re.match(r'^0[xX][0-9a-fA-F]+$', arg)
                ):
                    fixed_args.append(arg)

                else:
                    fixed_args.append(f"'{arg}'")

            return f"{func_name}({', '.join(fixed_args)})"

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
        return [FunctionTool(self.browse_url)]
