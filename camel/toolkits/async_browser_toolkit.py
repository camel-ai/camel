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

import asyncio
import datetime
import io
import os
import re
import shutil
import urllib.parse
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

from PIL import Image

if TYPE_CHECKING:
    from camel.agents import ChatAgent
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
    _parse_json_output,
    _reload_image,
    add_set_of_mark,
    interactive_region_from_dict,
    visual_viewport_from_dict,
)

logger = get_logger(__name__)

ASYNC_ACTIONS = [
    "fill_input_id",
    "click_id",
    "hover_id",
    "download_file_id",
    "scroll_up",
    "scroll_down",
    "scroll_to_bottom",
    "scroll_to_top",
    "back",
    "stop",
    "find_text_on_page",
    "visit_page",
    "click_blank_area",
]


def extract_function_name(s: str) -> str:
    r"""Extract the pure function name from a string (without parameters or
    parentheses)

    Args:
        s (str): Input string, e.g., `1.`**`click_id(14)`**, `scroll_up()`,
        `\'visit_page(url)\'`, etc.

    Returns:
        str: Pure function name (e.g., `click_id`, `scroll_up`, `visit_page`)
    """
    # 1. Strip leading/trailing whitespace and enclosing backticks or quotes
    s = s.strip().strip('`"\'')

    # Strip any leading numeric prefix like " 12. " or "3.   "
    s = re.sub(r'^\s*\d+\.\s*', '', s)

    # 3. Match a Python-valid identifier followed by an opening parenthesis
    match = re.match(r'^([A-Za-z_]\w*)\s*\(', s)
    if match:
        return match.group(1)

    # 4. Fallback: take everything before the first space or '('
    return re.split(r'[ (\n]', s, maxsplit=1)[0]


class AsyncBaseBrowser:
    def __init__(
        self,
        headless=True,
        cache_dir: Optional[str] = None,
        channel: Literal["chrome", "msedge", "chromium"] = "chromium",
        cookie_json_path: Optional[str] = None,
    ):
        r"""
        Initialize the asynchronous browser core.

        Args:
            headless (bool): Whether to run the browser in headless mode.
            cache_dir (Union[str, None]): The directory to store cache files.
            channel (Literal["chrome", "msedge", "chromium"]): The browser
                channel to use. Must be one of "chrome", "msedge", or
                "chromium".
            cookie_json_path (Optional[str]): Path to a JSON file containing
                authentication cookies and browser storage state. If provided
                and the file exists, the browser will load this state to
                maintain authenticated sessions without requiring manual login.

        Returns:
            None
        """
        from playwright.async_api import (
            async_playwright,
        )

        self.history: list[Any] = []
        self.headless = headless
        self.channel = channel
        self.playwright = async_playwright()
        self.page_history: list[Any] = []
        self.cookie_json_path = cookie_json_path
        self.playwright_server: Any = None
        self.playwright_started: bool = False
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.page_url: str = ""
        self.web_agent_model: Optional[BaseModelBackend] = None

        # Set the cache directory
        self.cache_dir = "tmp/" if cache_dir is None else cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

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

    async def async_init(self) -> None:
        r"""Asynchronously initialize the browser."""
        # Start Playwright asynchronously (only needed in async mode).
        if not getattr(self, "playwright_started", False):
            await self._ensure_browser_installed()
            self.playwright_server = await self.playwright.start()
            self.playwright_started = True
        # Launch the browser asynchronously.
        self.browser = await self.playwright_server.chromium.launch(
            headless=self.headless, channel=self.channel
        )
        # Check if cookie file exists before using it to maintain
        # authenticated sessions. This prevents errors when the cookie file
        # doesn't exist
        if self.cookie_json_path and os.path.exists(self.cookie_json_path):
            self.context = await self.browser.new_context(
                accept_downloads=True, storage_state=self.cookie_json_path
            )
        else:
            self.context = await self.browser.new_context(
                accept_downloads=True,
            )
        # Create a new page asynchronously.
        self.page = await self.context.new_page()

    def init(self) -> Coroutine[Any, Any, None]:
        r"""Initialize the browser asynchronously."""
        return self.async_init()

    def clean_cache(self) -> None:
        r"""Delete the cache directory and its contents."""
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    async def async_wait_for_load(self, timeout: int = 20) -> None:
        r"""
        Asynchronously Wait for a certain amount of time for the page to load.

        Args:
            timeout (int): Timeout in seconds.
        """
        timeout_ms = timeout * 1000
        await self.page.wait_for_load_state("load", timeout=timeout_ms)

        # TODO: check if this is needed
        await asyncio.sleep(2)

    def wait_for_load(self, timeout: int = 20) -> Coroutine[Any, Any, None]:
        r"""Wait for a certain amount of time for the page to load.

        Args:
            timeout (int): Timeout in seconds.
        """
        return self.async_wait_for_load(timeout)

    async def async_click_blank_area(self) -> None:
        r"""Asynchronously click a blank area of the page to unfocus
        the current element."""
        await self.page.mouse.click(0, 0)
        await self.wait_for_load()

    def click_blank_area(self) -> Coroutine[Any, Any, None]:
        r"""Click a blank area of the page to unfocus the current element."""
        return self.async_click_blank_area()

    async def async_visit_page(self, url: str) -> None:
        r"""Visit a page with the given URL."""

        await self.page.goto(url)
        await self.wait_for_load()
        self.page_url = url

    @retry_on_error()
    def visit_page(self, url: str) -> Coroutine[Any, Any, None]:
        r"""Visit a page with the given URL."""

        return self.async_visit_page(url)

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
    async def async_get_screenshot(
        self, save_image: bool = False
    ) -> Tuple[Image.Image, Union[str, None]]:
        r"""Asynchronously get a screenshot of the current page.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, str]: A tuple containing the screenshot
            image and the path to the image file if saved, otherwise
            :obj:`None`.
        """
        image_data = await self.page.screenshot(timeout=60000)
        image = Image.open(io.BytesIO(image_data))

        file_path = None
        if save_image:
            # Get url name to form a file name
            # Use urlparser for a safer extraction the url name
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

    @retry_on_error()
    def get_screenshot(
        self, save_image: bool = False
    ) -> Coroutine[Any, Any, Tuple[Image.Image, Union[str, None]]]:
        r"""Get a screenshot of the current page.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, str]: A tuple containing the screenshot
            image and the path to the image file if saved, otherwise
            :obj:`None`.
        """
        return self.async_get_screenshot(save_image)

    async def async_capture_full_page_screenshots(
        self, scroll_ratio: float = 0.8
    ) -> List[str]:
        r"""Asynchronously capture full page screenshots by scrolling the
        page with a buffer zone.

        Args:
            scroll_ratio (float): The ratio of viewport height to scroll each
            step (default: 0.8).

        Returns:
            List[str]: A list of paths to the captured screenshots.
        """
        screenshots = []
        scroll_height = await self.page.evaluate("document.body.scrollHeight")
        assert self.page.viewport_size is not None
        viewport_height = self.page.viewport_size["height"]
        current_scroll = 0
        screenshot_index = 1

        max_height = scroll_height - viewport_height
        scroll_step = int(viewport_height * scroll_ratio)

        last_height = 0

        while True:
            logger.debug(
                f"Current scroll: {current_scroll}, max_height: "
                f"{max_height}, step: {scroll_step}"
            )

            _, file_path = await self.get_screenshot(save_image=True)
            if file_path is not None:
                screenshots.append(file_path)

            await self.page.evaluate(f"window.scrollBy(0, {scroll_step})")
            # Allow time for content to load
            await asyncio.sleep(0.5)

            current_scroll = await self.page.evaluate("window.scrollY")
            # Break if there is no significant scroll
            if abs(current_scroll - last_height) < viewport_height * 0.1:
                break

            last_height = current_scroll
            screenshot_index += 1

        return screenshots

    def capture_full_page_screenshots(
        self, scroll_ratio: float = 0.8
    ) -> Coroutine[Any, Any, List[str]]:
        r"""Capture full page screenshots by scrolling the page with
            a buffer zone.

        Args:
            scroll_ratio (float): The ratio of viewport height to scroll each
                step (default: 0.8).

        Returns:
            List[str]: A list of paths to the captured screenshots.
        """
        return self.async_capture_full_page_screenshots(scroll_ratio)

    async def async_get_visual_viewport(self) -> VisualViewport:
        r"""Asynchronously get the visual viewport of the current page.

        Returns:
            VisualViewport: The visual viewport of the current page.
        """
        try:
            await self.page.evaluate(self.page_script)
        except Exception as e:
            logger.warning(f"Error evaluating page script: {e}")

        return visual_viewport_from_dict(
            await self.page.evaluate(
                "MultimodalWebSurfer.getVisualViewport();"
            )
        )

    def get_visual_viewport(self) -> Coroutine[Any, Any, VisualViewport]:
        r"""Get the visual viewport of the current page."""
        return self.async_get_visual_viewport()

    async def async_get_interactive_elements(
        self,
    ) -> Dict[str, InteractiveRegion]:
        r"""Asynchronously get the interactive elements of the current page.

        Returns:
            Dict[str, InteractiveRegion]: A dictionary containing the
            interactive elements of the current page.
        """
        try:
            await self.page.evaluate(self.page_script)
        except Exception as e:
            logger.warning(f"Error evaluating page script: {e}")

        result = cast(
            Dict[str, Dict[str, Any]],
            await self.page.evaluate(
                "MultimodalWebSurfer.getInteractiveRects();"
            ),
        )

        typed_results: Dict[str, InteractiveRegion] = {}
        for k in result:
            typed_results[k] = interactive_region_from_dict(result[k])

        return typed_results

    def get_interactive_elements(
        self,
    ) -> Coroutine[Any, Any, Dict[str, InteractiveRegion]]:
        r"""Get the interactive elements of the current page.

        Returns:
            Dict[str, InteractiveRegion]: A dictionary of interactive elements.
        """
        return self.async_get_interactive_elements()

    async def async_get_som_screenshot(
        self,
        save_image: bool = False,
    ) -> Tuple[Image.Image, Union[str, None]]:
        r"""Asynchronously get a screenshot of the current viewport
        with interactive elements marked.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, str]: A tuple containing the screenshot
                image and the path to the image file.

        """

        await self.wait_for_load()
        screenshot, _ = await self.async_get_screenshot(save_image=False)
        rects = await self.async_get_interactive_elements()

        file_path: str | None = None
        comp, _, _, _ = add_set_of_mark(
            screenshot,
            rects,
        )
        if save_image:
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

    def get_som_screenshot(
        self,
        save_image: bool = False,
    ) -> Coroutine[Any, Any, Tuple[Image.Image, Union[str, None]]]:
        r"""Get a screenshot of the current viewport with interactive elements
        marked.

        Args:
            save_image (bool): Whether to save the image to the cache
                directory.

        Returns:
            Tuple[Image.Image, str]: A tuple containing the screenshot image
                and the path to the image file.
        """
        return self.async_get_som_screenshot(save_image)

    async def async_scroll_up(self) -> None:
        r"""Asynchronously scroll up the page."""
        await self.page.keyboard.press("PageUp")

    def scroll_up(self) -> Coroutine[Any, Any, None]:
        r"""Scroll up the page."""
        return self.async_scroll_up()

    async def async_scroll_down(self) -> None:
        r"""Asynchronously scroll down the page."""
        await self.page.keyboard.press("PageDown")

    def scroll_down(self) -> Coroutine[Any, Any, None]:
        r"""Scroll down the page."""
        return self.async_scroll_down()

    def get_url(self) -> str:
        r"""Get the URL of the current page."""
        return self.page.url

    async def async_click_id(self, identifier: Union[str, int]) -> None:
        r"""Asynchronously click an element with the given ID.

        Args:
            identifier (Union[str, int]): The ID of the element to click.
        """
        if isinstance(identifier, int):
            identifier = str(identifier)
        target = self.page.locator(f"[__elementId='{identifier}']")

        try:
            await target.wait_for(timeout=5000)
        except (TimeoutError, Exception) as e:  # type: ignore[misc]
            logger.debug(f"Error during click operation: {e}")
            raise ValueError("No such element.") from None

        await target.scroll_into_view_if_needed()

        new_page = None
        try:
            async with self.page.expect_event(
                "popup", timeout=1000
            ) as page_info:
                box = cast(
                    Dict[str, Union[int, float]], await target.bounding_box()
                )
                await self.page.mouse.click(
                    box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                )
            new_page = await page_info.value

            # If a new page is opened, switch to it
            if new_page:
                self.page_history.append(deepcopy(self.page.url))
                self.page = new_page

        except (TimeoutError, Exception) as e:  # type: ignore[misc]
            logger.debug(f"Error during click operation: {e}")
            pass

        await self.wait_for_load()

    def click_id(
        self, identifier: Union[str, int]
    ) -> Coroutine[Any, Any, None]:
        r"""Click an element with the given identifier."""
        return self.async_click_id(identifier)

    async def async_extract_url_content(self) -> str:
        r"""Asynchronously extract the content of the current page."""
        content = await self.page.content()
        return content

    def extract_url_content(self) -> Coroutine[Any, Any, str]:
        r"""Extract the content of the current page."""
        return self.async_extract_url_content()

    async def async_download_file_id(self, identifier: Union[str, int]) -> str:
        r"""Asynchronously download a file with the given selector.

        Args:
            identifier (Union[str, int]): The identifier of the file
                to download.

        Returns:
            str: The path to the downloaded file.
        """

        if isinstance(identifier, int):
            identifier = str(identifier)
        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except (TimeoutError, Exception) as e:  # type: ignore[misc]
            logger.debug(f"Error during download operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        await target.scroll_into_view_if_needed()

        file_path = os.path.join(self.cache_dir)
        await self.wait_for_load()

        try:
            async with self.page.expect_download(
                timeout=5000
            ) as download_info:
                await target.click()
                download = await download_info.value
                file_name = download.suggested_filename

                file_path = os.path.join(file_path, file_name)
                await download.save_as(file_path)

            return f"Downloaded file to path '{file_path}'."

        except Exception as e:
            logger.debug(f"Error during download operation: {e}")
            return f"Failed to download file with identifier '{identifier}'."

    def download_file_id(
        self, identifier: Union[str, int]
    ) -> Coroutine[Any, Any, str]:
        r"""Download a file with the given identifier."""
        return self.async_download_file_id(identifier)

    async def async_fill_input_id(
        self, identifier: Union[str, int], text: str
    ) -> str:
        r"""Asynchronously fill an input field with the given text, and then
            press Enter.

        Args:
            identifier (Union[str, int]): The identifier of the input field.
            text (str): The text to fill.

        Returns:
            str: The result of the action.
        """
        if isinstance(identifier, int):
            identifier = str(identifier)

        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except (TimeoutError, Exception) as e:  # type: ignore[misc]
            logger.debug(f"Error during fill operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        await target.scroll_into_view_if_needed()
        await target.focus()
        try:
            await target.fill(text)
        except Exception as e:
            logger.debug(f"Error during fill operation: {e}")
            await target.press_sequentially(text)

        await target.press("Enter")
        await self.wait_for_load()
        return (
            f"Filled input field '{identifier}' with text '{text}' "
            f"and pressed Enter."
        )

    def fill_input_id(
        self, identifier: Union[str, int], text: str
    ) -> Coroutine[Any, Any, str]:
        r"""Fill an input field with the given text, and then press Enter."""
        return self.async_fill_input_id(identifier, text)

    async def async_scroll_to_bottom(self) -> str:
        r"""Asynchronously scroll to the bottom of the page."""
        await self.page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        await self.wait_for_load()
        return "Scrolled to the bottom of the page."

    def scroll_to_bottom(self) -> Coroutine[Any, Any, str]:
        r"""Scroll to the bottom of the page."""
        return self.async_scroll_to_bottom()

    async def async_scroll_to_top(self) -> str:
        r"""Asynchronously scroll to the top of the page."""
        await self.page.evaluate("window.scrollTo(0, 0);")
        await self.wait_for_load()
        return "Scrolled to the top of the page."

    def scroll_to_top(self) -> Coroutine[Any, Any, str]:
        r"""Scroll to the top of the page."""
        return self.async_scroll_to_top()

    async def async_hover_id(self, identifier: Union[str, int]) -> str:
        r"""Asynchronously hover over an element with the given identifier.

        Args:
            identifier (Union[str, int]): The identifier of the element
                to hover over.

        Returns:
            str: The result of the action.
        """
        if isinstance(identifier, int):
            identifier = str(identifier)
        try:
            target = self.page.locator(f"[__elementId='{identifier}']")
        except (TimeoutError, Exception) as e:  # type: ignore[misc]
            logger.debug(f"Error during hover operation: {e}")
            logger.warning(
                f"Element with identifier '{identifier}' not found."
            )
            return f"Element with identifier '{identifier}' not found."

        await target.scroll_into_view_if_needed()
        await target.hover()
        await self.wait_for_load()
        return f"Hovered over element with identifier '{identifier}'."

    def hover_id(
        self, identifier: Union[str, int]
    ) -> Coroutine[Any, Any, str]:
        r"""Hover over an element with the given identifier."""
        return self.async_hover_id(identifier)

    async def async_find_text_on_page(self, search_text: str) -> str:
        r"""Asynchronously find the next given text on the page.It is
        equivalent to pressing Ctrl + F and searching for the text.

        Args:
            search_text (str): The text to search for.

        Returns:
            str: The result of the action.
        """
        script = f"""
        (function() {{
            let text = "{search_text}";
            let found = window.find(text);
            if (!found) {{
                let elements = document.querySelectorAll(
                    "*:not(script):not(style)"
                );
                for (let el of elements) {{
                    if (el.innerText && el.innerText.includes(text)) {{
                        el.scrollIntoView({{
                            behavior: "smooth",
                            block: "center"
                        }});
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
        found = await self.page.evaluate(script)
        await self.wait_for_load()
        if found:
            return f"Found text '{search_text}' on the page."
        else:
            return f"Text '{search_text}' not found on the page."

    def find_text_on_page(self, search_text: str) -> Coroutine[Any, Any, str]:
        r"""Find the next given text on the page, and scroll the page to
        the targeted text. It is equivalent to pressing Ctrl + F and
        searching for the text.

        Args:
            search_text (str): The text to search for.

        Returns:
            str: The result of the action.
        """
        return self.async_find_text_on_page(search_text)

    async def async_back(self) -> None:
        r"""Asynchronously navigate back to the previous page."""

        page_url_before = self.page.url
        await self.page.go_back()

        page_url_after = self.page.url

        if page_url_after == "about:blank":
            await self.visit_page(page_url_before)

        if page_url_before == page_url_after:
            # If the page is not changed, try to use the history
            if len(self.page_history) > 0:
                await self.visit_page(self.page_history.pop())

        await asyncio.sleep(1)
        await self.wait_for_load()

    def back(self) -> Coroutine[Any, Any, None]:
        r"""Navigate back to the previous page."""
        return self.async_back()

    async def async_close(self) -> None:
        r"""Asynchronously close the browser."""
        await self.browser.close()

    def close(self) -> Coroutine[Any, Any, None]:
        r"""Close the browser."""
        return self.async_close()

    async def async_show_interactive_elements(self) -> None:
        r"""Asynchronously show simple interactive elements on
        the current page."""
        await self.page.evaluate(self.page_script)
        await self.page.evaluate("""
        () => {
            document.querySelectorAll(
                'a, button, input, select, textarea, ' +
                '[tabindex]:not([tabindex="-1"]), ' +
                '[contenteditable="true"]'
            ).forEach(el => {
                el.style.border = '2px solid red';
            });
        }
        """)

    def show_interactive_elements(self) -> Coroutine[Any, Any, None]:
        r"""Show simple interactive elements on the current page."""
        return self.async_show_interactive_elements()

    async def async_get_webpage_content(self) -> str:
        r"""Asynchronously extract the content of the current page and convert
        it to markdown."""
        from html2text import html2text

        await self.wait_for_load()
        html_content = await self.page.content()

        markdown_content = html2text(html_content)
        return markdown_content

    @retry_on_error()
    def get_webpage_content(self) -> Coroutine[Any, Any, str]:
        r"""Extract the content of the current page."""
        return self.async_get_webpage_content()

    async def async_ensure_browser_installed(self) -> None:
        r"""Ensure the browser is installed."""

        import platform
        import sys

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(channel=self.channel)
                await browser.close()
        except Exception:
            logger.info("Installing Chromium browser...")
            try:
                proc1 = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "playwright",
                    "install",
                    self.channel,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc1.communicate()
                if proc1.returncode != 0:
                    raise RuntimeError(
                        f"Failed to install browser: {stderr.decode()}"
                    )

                if platform.system().lower() == "linux":
                    proc2 = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "-m",
                        "playwright",
                        "install-deps",
                        self.channel,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout2, stderr2 = await proc2.communicate()
                    if proc2.returncode != 0:
                        error_message = stderr2.decode()
                        raise RuntimeError(
                            f"Failed to install dependencies: {error_message}"
                        )

                logger.info("Chromium browser installation completed")
            except Exception as e:
                raise RuntimeError(f"Installation failed: {e}")

    def _ensure_browser_installed(self) -> Coroutine[Any, Any, None]:
        r"""Ensure the browser is installed."""
        return self.async_ensure_browser_installed()


class AsyncBrowserToolkit(BaseToolkit):
    r"""An asynchronous class for browsing the web and interacting
    with web pages.

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
                maintain authenticated sessions without requiring manual
                login.
                (default: :obj:`None`)
        """
        super().__init__()
        self.browser = AsyncBaseBrowser(
            headless=headless,
            cache_dir=cache_dir,
            channel=channel,
            cookie_json_path=cookie_json_path,
        )

        self.history_window = history_window
        self.web_agent_model = web_agent_model
        self.planning_agent_model = planning_agent_model
        self.output_language = output_language
        self.browser.web_agent_model = web_agent_model

        self.history: list[Any] = []
        self.web_agent, self.planning_agent = self._initialize_agent()

    def _reset(self):
        self.web_agent.reset()
        self.planning_agent.reset()
        self.history = []
        os.makedirs(self.browser.cache_dir, exist_ok=True)

    def _initialize_agent(self) -> Tuple["ChatAgent", "ChatAgent"]:
        r"""Initialize the agent."""
        from camel.agents.chat_agent import ChatAgent

        if self.web_agent_model is None:
            web_agent_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4_1,
                model_config_dict={"temperature": 0, "top_p": 1},
            )
        else:
            web_agent_model = self.web_agent_model

        if self.planning_agent_model is None:
            planning_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.O3_MINI,
            )
        else:
            planning_model = self.planning_agent_model

        system_prompt = WEB_AGENT_SYSTEM_PROMPT

        web_agent = ChatAgent(
            system_message=system_prompt,
            model=web_agent_model,
            output_language=self.output_language,
        )

        planning_system_prompt = PLANNING_AGENT_SYSTEM_PROMPT

        planning_agent = ChatAgent(
            system_message=planning_system_prompt,
            model=planning_model,
            output_language=self.output_language,
        )

        return web_agent, planning_agent

    async def async_observe(
        self, task_prompt: str, detailed_plan: Optional[str] = None
    ) -> Tuple[str, str, str]:
        r"""Let agent observe the current environment, and get the next
        action."""

        detailed_plan_prompt_str = ""

        if detailed_plan is not None:
            detailed_plan_prompt_str = f"""
Here is a plan about how to solve the task step-by-step which you must follow:
<detailed_plan>{detailed_plan}</detailed_plan>
        """

        observe_prompt = OBSERVE_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt,
            detailed_plan_prompt=detailed_plan_prompt_str,
            AVAILABLE_ACTIONS_PROMPT=AVAILABLE_ACTIONS_PROMPT,
            history_window=self.history_window,
            history=self.history[-self.history_window :],
        )
        # get current state
        som_screenshot, _ = await self.browser.async_get_som_screenshot(
            save_image=True
        )
        img = _reload_image(som_screenshot)
        message = BaseMessage.make_user_message(
            role_name='user', content=observe_prompt, image_list=[img]
        )
        # Reset the history message of web_agent.
        self.web_agent.reset()
        resp = self.web_agent.step(message)

        resp_content = resp.msgs[0].content

        resp_dict = _parse_json_output(resp_content, logger)
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
                            f"fill_input_id({id_part}, "
                            f"'Please fill the text here.')"
                        )
        action_code = action_code.replace("`", "").strip()

        return observation_result, reasoning_result, action_code

    async def async_act(self, action_code: str) -> Tuple[bool, str]:
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
        async_flag = extract_function_name(action_code) in ASYNC_ACTIONS
        feedback_flag = _check_if_with_feedback(action_code)

        try:
            result = "Action was successful."
            if async_flag:
                temp_coroutine = eval(code)
                if feedback_flag:
                    result = await temp_coroutine
                else:
                    await temp_coroutine
                await asyncio.sleep(1)
                return True, result
            else:
                if feedback_flag:
                    result = eval(code)
                else:
                    exec(code)
                await asyncio.sleep(1)
                return True, result

        except Exception as e:
            await asyncio.sleep(1)
            return (
                False,
                f"Error while executing the action {action_code}: {e}. "
                f"If timeout, please recheck whether you have provided the "
                f"correct identifier.",
            )

    def _get_final_answer(self, task_prompt: str) -> str:
        r"""Get the final answer based on the task prompt and current browser
        state. It is used when the agent thinks that the task can be completed
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

        resp = self.web_agent.step(message)
        return resp.msgs[0].content

    def _task_planning(self, task_prompt: str, start_url: str) -> str:
        r"""Plan the task based on the given task prompt."""

        # Here are the available browser functions we can
        # use: {AVAILABLE_ACTIONS_PROMPT}

        planning_prompt = TASK_PLANNING_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt, start_url=start_url
        )

        message = BaseMessage.make_user_message(
            role_name='user', content=planning_prompt
        )

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
                whether the task needs to be replanned, and the replanned
                schema.
        """

        # Here are the available browser functions we can
        # use: {AVAILABLE_ACTIONS_PROMPT}
        replanning_prompt = TASK_REPLANNING_PROMPT_TEMPLATE.format(
            task_prompt=task_prompt,
            detailed_plan=detailed_plan,
            history_window=self.history_window,
            history=self.history[-self.history_window :],
        )
        # Reset the history message of planning_agent.
        self.planning_agent.reset()
        resp = self.planning_agent.step(replanning_prompt)
        resp_dict = _parse_json_output(resp.msgs[0].content, logger)

        if_need_replan = resp_dict.get("if_need_replan", False)
        replanned_schema = resp_dict.get("replanned_schema", "")

        if if_need_replan:
            return True, replanned_schema
        else:
            return False, replanned_schema

    @dependencies_required("playwright")
    async def browse_url(
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

        await self.browser.async_init()
        await self.browser.visit_page(start_url)
        for i in range(round_limit):
            observation, reasoning, action_code = await self.async_observe(
                task_prompt, detailed_plan
            )
            logger.debug(f"Observation: {observation}")
            logger.debug(f"Reasoning: {reasoning}")
            logger.debug(f"Action code: {action_code}")

            if "stop" in action_code:
                task_completed = True
                trajectory_info = {
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
                success, info = await self.async_act(action_code)
                if not success:
                    logger.warning(f"Error while executing the action: {info}")

                trajectory_info = {
                    "round": i,
                    "observation": observation,
                    "thought": reasoning,
                    "action": action_code,
                    "action_if_success": success,
                    "info": info,
                    "current_url": self.browser.get_url(),
                }
                self.history.append(trajectory_info)

                # replan the task if necessary
                if_need_replan, replanned_schema = self._task_replanning(
                    task_prompt, detailed_plan
                )
                if if_need_replan:
                    detailed_plan = replanned_schema
                    logger.debug(f"Replanned schema: {replanned_schema}")

        if not task_completed:
            simulation_result = f"""
                The task is not completed within the round limit. Please check 
                the last round {self.history_window} information to see if 
                there is any useful information:
                <history>{self.history[-self.history_window :]}</history>
            """

        else:
            simulation_result = self._get_final_answer(task_prompt)

        await self.browser.close()
        return simulation_result

    def get_tools(self) -> List[FunctionTool]:
        return [FunctionTool(self.browse_url)]
