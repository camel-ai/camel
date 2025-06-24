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
        r"""Launches a new browser session. This should be the first step.

        Args:
            start_url (Optional[str]): The URL to navigate to after the browser
                launches. If not provided, the browser will open with a blank
                page. (default: :obj:`None`)

        Returns:
            Dict[str, str]: A dictionary containing the result of the action
                and a snapshot of the page. The keys are "result" and
                "snapshot". The "snapshot" is a YAML-like representation of
                the page's DOM structure, including element references
                (e.g., "e3") that can be used in other tool calls.
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
        r"""Closes the current browser session, freeing up all associated
        resources. This should be called when the browsing task is complete.

        Returns:
            str: A confirmation message indicating the session has been
                closed.
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
        r"""Navigates the current browser page to a new URL.

        Args:
            url (str): The URL to navigate to. Must be a fully qualified URL
                (e.g., "https://www.google.com").

        Returns:
            Dict[str, str]: A dictionary containing the navigation result and a
                snapshot of the new page. The keys are "result" and
                "snapshot". The "snapshot" provides a fresh view of the
                page's DOM structure.
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
        r"""Performs a click action on a specified element on the current page.

        Args:
            ref (str): The reference ID of the element to click. This ID is
                obtained from the page snapshot (e.g., "e12").

        Returns:
            Dict[str, str]: A dictionary containing the result of the action.
                If the click causes a change in the page's structure, a
                "snapshot" key will be included with a diff of the changes.
        """
        self._validate_ref(ref, "click")

        action: Dict[str, Any] = {"type": "click", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def type(self, *, ref: str, text: str) -> Dict[str, str]:
        r"""Types text into an input field or textarea on the current page.

        Args:
            ref (str): The reference ID of the input element. This ID is
                obtained from the page snapshot (e.g., "e25").
            text (str): The text to be typed into the element.

        Returns:
            Dict[str, str]: A dictionary containing the result of the action.
                The key is "result".
        """
        self._validate_ref(ref, "type")

        action: Dict[str, Any] = {"type": "type", "ref": ref, "text": text}
        return await self._exec_with_snapshot(action)

    async def select(self, *, ref: str, value: str) -> Dict[str, str]:
        r"""Selects an option from a dropdown (<select>) element on the page.

        Args:
            ref (str): The reference ID of the <select> element. This ID is
                obtained from the page snapshot.
            value (str): The value of the option to be selected. This should
                match the 'value' attribute of an <option> tag.

        Returns:
            Dict[str, str]: A dictionary containing the result of the action.
                The key is "result".
        """
        self._validate_ref(ref, "select")

        action: Dict[str, Any] = {"type": "select", "ref": ref, "value": value}
        return await self._exec_with_snapshot(action)

    async def scroll(self, *, direction: str, amount: int) -> Dict[str, str]:
        r"""Scrolls the current page up or down by a specified amount.

        Args:
            direction (str): The direction to scroll. Must be either "up" or
                "down".
            amount (int): The number of pixels to scroll.

        Returns:
            Dict[str, str]: A dictionary containing the result of the action.
                The key is "result".
        """
        if direction not in ("up", "down"):
            logger.error("scroll(): 'direction' must be 'up' or 'down'")
            return {
                "result": "scroll() Error: 'direction' must be 'up' or 'down'"
            }

        action = {"type": "scroll", "direction": direction, "amount": amount}
        return await self._exec_with_snapshot(action)

    async def enter(self, *, ref: str) -> Dict[str, str]:
        r"""Simulates pressing the Enter key on a specific element.
        This is often used to submit forms.

        Args:
            ref (str): The reference ID of the element to focus before
                pressing Enter. This ID is obtained from the page snapshot.

        Returns:
            Dict[str, str]: A dictionary containing the result of the action.
                If pressing Enter causes a page navigation or DOM change, a
                "snapshot" key will be included with a diff of the changes.
        """
        self._validate_ref(ref, "enter")

        action: Dict[str, Any] = {"type": "enter", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def wait_user(
        self,
        timeout_sec: Optional[float] = None,
    ) -> Dict[str, str]:
        r"""Pauses the agent's execution and waits for human intervention.
        This is useful for tasks that require manual steps, like solving a
        CAPTCHA. The agent will print a message and wait for the user to
        press the Enter key in the console.

        Args:
            timeout_sec (Optional[float]): The maximum time in seconds to wait
                for the user. If `None`, it will wait indefinitely. Defaults
                to `None`. (default: :obj:`None`)

        Returns:
            Dict[str, str]: A dictionary containing a result message and a
                full snapshot of the current page after the user has acted.
                The keys are "result" and "snapshot".
        """

        import asyncio

        prompt = (
            "🕑 Agent is waiting for human input. "
            "Complete the required action in the browser, then press Enter "
            "to continue..."
        )

        logger.info(f"\n{prompt}\n")

        async def _await_enter():
            await asyncio.to_thread(input, ">>> Press Enter to resume <<<\n")

        try:
            if timeout_sec is not None:
                await asyncio.wait_for(_await_enter(), timeout=timeout_sec)
                result_msg = "User resumed."
            else:
                await _await_enter()
                result_msg = "User resumed."
        except asyncio.TimeoutError:
            result_msg = f"Timeout {timeout_sec}s reached, auto-resumed."

        snapshot = await self._session.get_snapshot(
            force_refresh=True,
            diff_only=False,
        )

        return {"result": result_msg, "snapshot": snapshot}

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
