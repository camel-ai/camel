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

from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

from .agent import PlaywrightLLMAgent

# session wrapper
from .nv_browser_session import NVBrowserSession


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
        r"""Ensure cleanup when toolkit is garbage collected."""
        # Note: __del__ cannot be async, so we schedule cleanup if needed
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(self.close_browser())
                # Don't wait for completion to avoid blocking
                del task
            else:
                asyncio.run(self.close_browser())
        except Exception:
            pass  # Don't fail during garbage collection

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _ensure_browser(self):
        await self._session.ensure_browser()

    async def _require_page(self):
        await self._session.ensure_browser()
        return await self._session.get_page()

    def _validate_ref(self, ref: str, method_name: str) -> None:
        """Validate that ref parameter is a non-empty string."""
        if not ref or not isinstance(ref, str):
            raise ValueError(
                f"{method_name}(): 'ref' must be a non-empty string, "
                f"got: {ref}"
            )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------
    async def open_browser(
        self, start_url: Optional[str] = None
    ) -> Dict[str, str]:
        r"""Launch a Playwright browser session.

        Args:
            start_url (Optional[str]): If provided, the page will navigate to
                this URL immediately after the browser launches.

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

    # Navigation / page state ------------------------------------------------
    async def visit_page(self, url: str) -> Dict[str, str]:
        """Navigate the current page to the specified URL.

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
            snapshot even
                if the URL has not changed.
            diff_only (bool): If ``True`` return only the diff relative to the
                previous snapshot.

        Returns:
            str: Formatted snapshot string.
        """
        return await self._session.get_snapshot(
            force_refresh=force_refresh, diff_only=diff_only
        )

    # Element-level wrappers -------------------------------------------------
    async def click(self, *, ref: str) -> Dict[str, str]:
        r"""Click an element identified by ``ref``

        Args:
            ref (str): Element reference ID extracted from snapshot (e.g.
            ``"e3"``).

        Returns:
            Dict[str, str]: Result message from ``ActionExecutor``.
        """
        self._validate_ref(ref, "click")

        action: Dict[str, Any] = {"type": "click", "ref": ref}
        return await self._exec_with_snapshot(action)

    async def type(self, *, ref: str, text: str) -> Dict[str, str]:
        r"""Type text into an input or textarea element.

        Args:
            ref (str): Element reference ID extracted from snapshot (e.g.
            ``"e3"``).
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
            direction (str): ``"down"`` or ``"up"``.
            amount (int): Pixel distance to scroll.

        Returns:
            Dict[str, str]: Execution result message.
        """
        if direction not in ("up", "down"):
            raise ValueError("scroll(): 'direction' must be 'up' or 'down'")

        action = {"type": "scroll", "direction": direction, "amount": amount}
        return await self._exec_with_snapshot(action)

    async def wait(
        self, *, timeout_ms: int | None = None, selector: str | None = None
    ) -> Dict[str, str]:
        r"""Explicit wait utility.

        Args:
            timeout_ms (Optional[int]): Milliseconds to sleep.
            selector (Optional[str]): Wait until this CSS selector appears
                in DOM.

        Returns:
            Dict[str, str]: Execution result message.
        """
        # Default to 1 000 ms sleep when no arguments provided
        if timeout_ms is None and selector is None:
            timeout_ms = 1000

        action: Dict[str, Any] = {"type": "wait"}
        if timeout_ms is not None:
            action["timeout"] = timeout_ms
        if selector is not None:
            action["selector"] = selector
        return await self._exec_with_snapshot(action)

    async def extract(self, *, ref: str) -> Dict[str, str]:
        r"""Extract text content from an element.

        Args:
            ref (str): Element reference ID obtained from snapshot.

        Returns:
            Dict[str, str]: Extracted text or error message.
        """
        self._validate_ref(ref, "extract")
        return await self._exec_with_snapshot({"type": "extract", "ref": ref})

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

    # ------------------------------------------------------------------
    # Optional PlaywrightLLMAgent helpers
    # ------------------------------------------------------------------
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
        `web_agent_model`)."""

        agent = self._ensure_agent()
        await agent.navigate(start_url)
        await agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

    # ------------------------------------------------------------------
    # Toolkit registration
    # ------------------------------------------------------------------
    def get_tools(self) -> List[FunctionTool]:
        base_tools = [
            FunctionTool(self.open_browser),
            FunctionTool(self.close_browser),
            FunctionTool(self.visit_page),
            FunctionTool(self.get_page_snapshot),
            FunctionTool(self.click),
            FunctionTool(self.type),
            FunctionTool(self.select),
            FunctionTool(self.scroll),
            FunctionTool(self.wait),
            FunctionTool(self.extract),
            FunctionTool(self.enter),
        ]

        if self.web_agent_model is not None:
            base_tools.append(FunctionTool(self.solve_task))

        return base_tools
