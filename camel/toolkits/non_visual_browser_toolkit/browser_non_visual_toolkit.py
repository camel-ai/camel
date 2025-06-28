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
import os
import urllib.parse
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import sanitize_filename

from .agent import PlaywrightLLMAgent
from .nv_browser_session import NVBrowserSession

logger = get_logger(__name__)


class BrowserNonVisualToolkit(BaseToolkit):
    r"""A lightweight, non-visual browser toolkit exposing primitive
    Playwright actions as CAMEL FunctionTools."""

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        web_agent_model: Optional[BaseModelBackend] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._headless = headless
        self._user_data_dir = user_data_dir
        self.web_agent_model = web_agent_model
        self.cache_dir = "tmp/" if cache_dir is None else cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # Core components
        self._session = NVBrowserSession(
            headless=headless, user_data_dir=user_data_dir
        )
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
                    loop.run_until_complete(self.close_browser())
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

    async def _ensure_browser(self):
        await self._session.ensure_browser()

    async def _require_page(self):
        await self._session.ensure_browser()
        return await self._session.get_page()

    async def _wait_for_page_stability(self):
        """Wait for page to become stable
        after actions that might trigger updates."""
        page = await self._require_page()
        import asyncio

        try:
            # Wait for DOM content to be loaded
            await page.wait_for_load_state('domcontentloaded', timeout=3000)
            logger.debug("DOM content loaded")

            # Try to wait for network idle (important for AJAX/SPA)
            try:
                await page.wait_for_load_state('networkidle', timeout=2000)
                logger.debug("Network idle achieved")
            except Exception:
                logger.debug("Network idle timeout - continuing anyway")

            # Additional small delay for JavaScript execution
            await asyncio.sleep(0.5)
            logger.debug("Page stability wait completed")

        except Exception as e:
            logger.debug(
                f"Page stability wait failed:" f" {e} - continuing anyway"
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

    async def _exec_with_snapshot(
        self, action: Dict[str, Any]
    ) -> Dict[str, str]:
        r"""Execute action and return result with snapshot comparison."""
        import time

        # Log action execution start
        action_type = action.get("type", "unknown")
        logger.info(f"Executing action: {action_type}")

        # Get before snapshot
        logger.info("Capturing pre-action snapshot...")
        snapshot_start = time.time()
        before_snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        snapshot_time = time.time() - snapshot_start
        logger.info(f"Pre-action snapshot captured in {snapshot_time:.2f}s")

        # Execute action
        logger.info(f"Executing {action_type} action...")
        action_start = time.time()
        result = await self._session.exec_action(action)
        action_time = time.time() - action_start
        logger.info(f"Action {action_type} completed in {action_time:.2f}s")

        # Wait for page stability after action (especially important for click)
        if action_type in ["click", "type", "select", "enter"]:
            logger.info(
                f"Waiting for page stability " f"after {action_type}..."
            )
            stability_start = time.time()
            await self._wait_for_page_stability()
            stability_time = time.time() - stability_start
            logger.info(
                f"Page stability wait " f"completed in {stability_time:.2f}s"
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

        return {"result": result, "snapshot": snapshot}

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

    async def open_browser(
        self, start_url: Optional[str] = None
    ) -> Dict[str, str]:
        r"""Launch browser session.

        Args:
            start_url: Optional URL to navigate to after launch.

        Returns:
            Dict with "result" and "snapshot" keys.
        """
        import time

        logger.info("Starting browser session...")

        browser_start = time.time()
        await self._session.ensure_browser()
        browser_time = time.time() - browser_start
        logger.info(f"Browser session started in {browser_time:.2f}s")

        if start_url:
            logger.info(f"Auto-navigating to start URL: {start_url}")
            return await self.visit_page(start_url)

        logger.info("Capturing initial browser snapshot...")
        snapshot_start = time.time()
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        snapshot_time = time.time() - snapshot_start
        logger.info(f"Initial snapshot captured in {snapshot_time:.2f}s")

        return {"result": "Browser session started.", "snapshot": snapshot}

    async def close_browser(self) -> str:
        r"""Close browser session and free resources."""
        if self._agent is not None:
            try:
                await self._agent.close()
            except Exception:
                pass
            self._agent = None

        await self._session.close()
        return "Browser session closed."

    async def visit_page(self, url: str) -> Dict[str, str]:
        r"""Navigate to a URL.

        Args:
            url: The URL to navigate to.

        Returns:
            Dict with navigation result and page snapshot.
        """
        if not url or not isinstance(url, str):
            raise ValueError("'url' must be a non-empty string")

        import time

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

        return {"result": nav_result, "snapshot": snapshot}

    async def get_page_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        r"""Capture DOM snapshot.

        Args:
            force_refresh: Always re-generate snapshot.
            diff_only: Return only diff from previous snapshot.

        Returns:
            Formatted snapshot string.
        """
        import time

        logger.info(
            f"Capturing page snapshot "
            f"(force_refresh={force_refresh}, diff_only={diff_only})"
        )

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

    async def get_som_screenshot(self):
        r"""Capture webpage screenshot with
        interactive elements visually marked.

        This method provides visual information
        about the current webpage by:
        - Taking a full-page screenshot
        - Marking all interactive elements with colored boxes and reference IDs
        - Saving the annotated image to cache for agent analysis
        - Returning the visual data for agent's understanding of page layout

        Only use this method when visual
        information is needed. In most cases,
        actions can be taken based on the DOM's snapshot alone.

        Returns:
            ToolResult: Contains description
            and base64-encoded screenshot image
                with visual element markings for agent analysis.

        """
        try:
            from PIL import Image
        except ImportError:
            from camel.utils.tool_result import ToolResult

            return ToolResult(
                text="Set of Marks screenshot failed: "
                "PIL not available. Install with: pip install Pillow"
            )

        from camel.utils.tool_result import ToolResult

        # Get screenshot and analysis
        page = await self._require_page()

        # Log screenshot timeout start
        screenshot_timeout_ms = 60000
        logger.info(
            f"Starting screenshot capture"
            f"with timeout: {screenshot_timeout_ms}ms (60s)"
        )

        import time

        start_time = time.time()
        image_data = await page.screenshot(timeout=screenshot_timeout_ms)
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

    async def click(self, *, ref: str) -> Dict[str, str]:
        r"""Click an element.

        Args:
            ref: Element reference ID from page snapshot.

        Returns:
            Dict with action result and snapshot.
        """
        self._validate_ref(ref, "click")

        analysis = await self._get_unified_analysis()
        elements = analysis.get("elements", {})
        if ref not in elements:
            logger.error(
                f"Error: Element reference '{ref}' not found in {elements}"
            )
            return {"result": f"Error: Element reference '{ref}' not found"}

        action = {"type": "click", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def type(self, *, ref: str, text: str) -> Dict[str, str]:
        r"""Type text into an input field.

        Args:
            ref: Element reference ID.
            text: Text to type.

        Returns:
            Dict with action result.
        """
        self._validate_ref(ref, "type")
        await self._get_unified_analysis()  # Ensure aria-ref attributes

        action = {"type": "type", "ref": ref, "text": text}
        return await self._exec_with_snapshot(action)

    async def select(self, *, ref: str, value: str) -> Dict[str, str]:
        r"""Select option from dropdown.

        Args:
            ref: Select element reference ID.
            value: Option value to select.

        Returns:
            Dict with action result.
        """
        self._validate_ref(ref, "select")
        await self._get_unified_analysis()

        action = {"type": "select", "ref": ref, "value": value}
        return await self._exec_with_snapshot(action)

    async def scroll(self, *, direction: str, amount: int) -> Dict[str, str]:
        r"""Scroll the page.

        Args:
            direction: "up" or "down".
            amount: Pixels to scroll.

        Returns:
            Dict with action result.
        """
        if direction not in ("up", "down"):
            return {"result": "Error: direction must be 'up' or 'down'"}

        action = {"type": "scroll", "direction": direction, "amount": amount}
        return await self._exec_with_snapshot(action)

    async def enter(self, *, ref: str) -> Dict[str, str]:
        r"""Press Enter key on an element.

        Args:
            ref: Element reference ID.

        Returns:
            Dict with action result and snapshot.
        """
        self._validate_ref(ref, "enter")
        action = {"type": "enter", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def wait_user(
        self, timeout_sec: Optional[float] = None
    ) -> Dict[str, str]:
        r"""Wait for human intervention.

        Args:
            timeout_sec: Max wait time in seconds.

        Returns:
            Dict with result and current snapshot.
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
                import time

                start_time = time.time()
                await asyncio.wait_for(_await_enter(), timeout=timeout_sec)
                wait_time = time.time() - start_time
                logger.info(f"User input received after {wait_time:.2f}s")
                result_msg = "User resumed."
            else:
                logger.info("Waiting for user " "input (no timeout)")
                import time

                start_time = time.time()
                await _await_enter()
                wait_time = time.time() - start_time
                logger.info(f"User input received " f"after {wait_time:.2f}s")
                result_msg = "User resumed."
        except asyncio.TimeoutError:
            wait_time = timeout_sec
            logger.info(
                f"User input timeout reached "
                f"after {wait_time}s, auto-resuming"
            )
            result_msg = f"Timeout {timeout_sec}s reached, auto-resumed."

        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": result_msg, "snapshot": snapshot}

    async def get_page_links(self, *, ref: List[str]) -> Dict[str, Any]:
        r"""Get specific links by reference IDs.

        Args:
            ref: List of link reference IDs.

        Returns:
            Dict with links list and snapshot.
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

    async def solve_task(
        self, task_prompt: str, start_url: str, max_steps: int = 15
    ) -> str:
        r"""Use LLM agent to complete task autonomously.

        Args:
            task_prompt: Task description.
            start_url: Starting URL.
            max_steps: Maximum steps to take.

        Returns:
            Task completion result.
        """
        agent = self._ensure_agent()
        await agent.navigate(start_url)
        await agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

    def get_tools(self) -> List[FunctionTool]:
        r"""Get available function tools."""
        base_tools = [
            FunctionTool(self.open_browser),
            FunctionTool(self.close_browser),
            FunctionTool(self.visit_page),
            FunctionTool(self.get_page_snapshot),
            FunctionTool(self.get_som_screenshot),
            FunctionTool(self.get_page_links),
            FunctionTool(self.click),
            FunctionTool(self.type),
            FunctionTool(self.select),
            FunctionTool(self.scroll),
            FunctionTool(self.wait_user),
        ]

        if self.web_agent_model is not None:
            base_tools.append(FunctionTool(self.solve_task))

        return base_tools
