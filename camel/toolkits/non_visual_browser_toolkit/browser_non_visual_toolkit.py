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
from __future__ import annotations

from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

from .agent import PlaywrightLLMAgent
from .nv_browser_session import NVBrowserSession

logger = get_logger(__name__)


class BrowserNonVisualToolkit(BaseToolkit):
    r"""A lightweight, *non-visual* browser toolkit exposing primitive
    Playwright actions as CAMEL `FunctionTool`s.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        web_agent_model: Optional[BaseModelBackend] = None,
    ) -> None:
        super().__init__()
        self._headless = headless
        self._user_data_dir = user_data_dir
        self.web_agent_model = web_agent_model  # Currently unused but kept
        # for compatibility

        # Encapsulated browser session
        self._session = NVBrowserSession(
            headless=headless, user_data_dir=user_data_dir
        )

        # Optional higher-level agent (only if user supplies model)
        self._agent: Optional[PlaywrightLLMAgent] = None

    def __del__(self):
        r"""Best-effort cleanup when toolkit is garbage collected.

        1. We *avoid* running during the Python interpreter shutdown phase
           (`sys.is_finalizing()`), because the import machinery and/or event
           loop may already be torn down which leads to noisy exceptions such
           as `ImportError: sys.meta_path is None` or
           `RuntimeError: Event loop is closed`.
        2. We protect all imports and event-loop operations with defensive
           `try/except` blocks.  This ensures that, even if cleanup cannot be
           carried out, we silently ignore the failure instead of polluting
           stderr on program exit.
        """
        try:
            import sys

            if getattr(sys, "is_finalizing", lambda: False)():
                return  # Skip cleanup during interpreter shutdown

            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread → nothing to clean
                return

            if loop.is_closed():
                # Event loop already closed → cannot run async cleanup
                return

            if loop.is_running():
                try:
                    task = loop.create_task(self.close_browser())
                    del task  # Fire-and-forget
                except RuntimeError:
                    # Loop is running but not in this thread → ignore
                    pass
            else:
                # Own the loop → safe to run
                asyncio.run(self.close_browser())
        except Exception:
            # Suppress *all* errors during garbage collection
            pass

    async def _ensure_browser(self):
        await self._session.ensure_browser()

    async def _require_page(self):
        await self._session.ensure_browser()
        return await self._session.get_page()

    def _validate_ref(self, ref: str, method_name: str) -> None:
        r"""Validate that ref parameter is a non-empty string."""
        if not ref or not isinstance(ref, str):
            logger.error(
                f"{method_name}(): 'ref' must be a non-empty string, "
                f"got: {ref}"
            )

    async def open_browser(
        self, start_url: Optional[str] = None
    ) -> Dict[str, str]:
        r"""Launch a Playwright browser session.

        Args:
            start_url (Optional[str]): Optional URL to navigate to immediately
                after the browser launches. If not provided, the browser will
                not navigate to any URL. (default: :obj:`None`)

        Returns:
            Dict[str, str]: Keys: ``result`` for action outcome,
                ``snapshot`` for full DOM snapshot.
        """
        await self._session.ensure_browser()
        if start_url:
            return await self.visit_page(start_url)
        # If no start_url provided, still capture initial snapshot
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": "Browser session started.", "snapshot": snapshot}

    async def close_browser(self) -> str:
        r"""Terminate the current browser session and free all resources.

        Returns:
            str: Confirmation message.
        """
        # Close agent if it exists
        if self._agent is not None:
            try:
                await self._agent.close()
            except Exception:
                pass  # Don't fail if agent cleanup fails
            self._agent = None

        # Close session
        await self._session.close()
        return "Browser session closed."

    async def visit_page(self, url: str) -> Dict[str, str]:
        r"""Navigate the current page to the specified URL.

        Args:
            url (str): The destination URL.

        Returns:
            Dict[str, str]: Keys: ``result`` for action outcome,
                ``snapshot`` for full DOM snapshot.
        """
        if not url or not isinstance(url, str):
            raise ValueError("visit_page(): 'url' must be a non-empty string")

        nav_result = await self._session.visit(url)
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": nav_result, "snapshot": snapshot}

    async def get_page_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        r"""Capture a YAML-like structural snapshot of the DOM.

        Args:
            force_refresh (bool): When ``True`` always re-generate the
                snapshot even if the URL has not changed. (default:
                :obj:`False`)
            diff_only (bool): When ``True`` return only the diff relative to
                the previous snapshot. (default: :obj:`False`)

        Returns:
            str: Formatted snapshot string.
        """
        return await self._session.get_snapshot(
            force_refresh=force_refresh, diff_only=diff_only
        )

    async def click(self, *, ref: str) -> Dict[str, str]:
        r"""Click an element identified by ``ref``

        Args:
            ref (str): Element reference ID extracted from snapshot
                (e.g.``"e3"``).

        Returns:
            Dict[str, str]: Result message from ``ActionExecutor``.
        """
        self._validate_ref(ref, "click")

        action: Dict[str, Any] = {"type": "click", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def type(self, *, ref: str, text: str) -> Dict[str, str]:
        r"""Type text into an input or textarea element.

        Args:
            ref (str): Element reference ID extracted from snapshot.
                (e.g.``"e3"``).
            text (str): The text to enter.

        Returns:
            Dict[str, str]: Execution result message.
        """
        self._validate_ref(ref, "type")

        action: Dict[str, Any] = {"type": "type", "ref": ref, "text": text}
        return await self._exec_with_snapshot(action)

    async def select(self, *, ref: str, value: str) -> Dict[str, str]:
        r"""Select an option in a ``<select>`` element.

        Args:
            ref (str): Element reference ID.
            value (str): The value / option to select.

        Returns:
            Dict[str, str]: Execution result message.
        """
        self._validate_ref(ref, "select")

        action: Dict[str, Any] = {"type": "select", "ref": ref, "value": value}
        return await self._exec_with_snapshot(action)

    async def scroll(self, *, direction: str, amount: int) -> Dict[str, str]:
        r"""Scroll the page.

        Args:
            direction (str): Scroll direction, should be ``"down"`` or
                ``"up"``.
            amount (int): Pixel distance to scroll.

        Returns:
            Dict[str, str]: Execution result message.
        """
        if direction not in ("up", "down"):
            logger.error("scroll(): 'direction' must be 'up' or 'down'")
            return {
                "result": "scroll() Error: 'direction' must be 'up' or 'down'"
            }

        action = {"type": "scroll", "direction": direction, "amount": amount}
        return await self._exec_with_snapshot(action)

    async def enter(self, *, ref: str) -> Dict[str, str]:
        r"""Press the Enter key.

        Args:
            ref (str): Element reference ID to focus before pressing.

        Returns:
            Dict[str, str]: Execution result message.
        """
        self._validate_ref(ref, "enter")

        action: Dict[str, Any] = {"type": "enter", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def wait_user(self, *, seconds: float = 1.0) -> Dict[str, str]:
        r"""Pause execution for a given amount of *real* time and then
        return a *full* page snapshot.

        This is a convenience wrapper around the existing wait action for
        scenarios where you encounter a CAPTCHA or need to pause for manual
        user input, and want to retrieve the complete DOM snapshot afterward.

        Args:
            seconds (float): How long to sleep, expressed in seconds. Must
                be a positive number. (default: :obj:`1.0`)

        Returns:
            Dict[str, str]: Keys ``result`` and ``snapshot``.
        """
        if seconds is None or seconds <= 0:
            logger.error("wait_time(): 'seconds' must be a positive number")
            return {
                "result": "wait_time(): 'seconds' must be a positive number"
            }

        # Reuse underlying ActionExecutor's ``wait`` implementation (expects
        # ms)
        timeout_ms = int(seconds * 1000)
        action: Dict[str, Any] = {"type": "wait", "timeout": timeout_ms}

        # Execute the sleep via ActionExecutor (no snapshot diff expected)
        result = await self._exec(action)

        # Always return a *full* snapshot after the pause
        snapshot = await self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": result, "snapshot": snapshot}

    # Helper to run through ActionExecutor
    async def _exec(self, action: Dict[str, Any]) -> str:
        return await self._session.exec_action(action)

    async def _exec_with_snapshot(
        self, action: Dict[str, Any]
    ) -> Dict[str, str]:
        r"""Execute action and, if DOM structure changed, include snapshot
        diff.
        """
        result = await self._session.exec_action(action)

        # Only capture diff if action type typically changes DOM
        from .actions import ActionExecutor

        if not ActionExecutor.should_update_snapshot(action):
            return {"result": result}

        # Capture structural diff to previous snapshot
        diff = await self._session.get_snapshot(
            force_refresh=True, diff_only=True
        )

        if diff.startswith("- Page Snapshot (no structural changes)"):
            return {"result": result}

        return {"result": result, "snapshot": diff}

    def _ensure_agent(self) -> PlaywrightLLMAgent:
        r"""Create PlaywrightLLMAgent on first use if `web_agent_model`
        provided."""
        if self.web_agent_model is None:
            raise RuntimeError(
                "web_agent_model not supplied - high-level task planning is "
                "unavailable."
            )

        if self._agent is None:
            self._agent = PlaywrightLLMAgent(
                headless=self._headless,
                user_data_dir=self._user_data_dir,
                model_backend=self.web_agent_model,
            )
        return self._agent

    async def solve_task(
        self, task_prompt: str, start_url: str, max_steps: int = 15
    ) -> str:
        r"""Use LLM agent to autonomously complete the task (requires
        `web_agent_model`).

        Args:
            task_prompt (str): The task prompt to complete.
            start_url (str): The URL to navigate to.
            max_steps (int): The maximum number of steps to take.
                (default: :obj:`15`)

        Returns:
            str: The result of the task.
        """

        agent = self._ensure_agent()
        await agent.navigate(start_url)
        await agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

    def get_tools(self) -> List[FunctionTool]:
        base_tools = [
            FunctionTool(self.open_browser),
            FunctionTool(self.close_browser),
            FunctionTool(self.visit_page),
            FunctionTool(self.click),
            FunctionTool(self.type),
            FunctionTool(self.select),
            FunctionTool(self.scroll),
            FunctionTool(self.enter),
            FunctionTool(self.wait_user),
        ]

        if self.web_agent_model is not None:
            base_tools.append(FunctionTool(self.solve_task))

        return base_tools
