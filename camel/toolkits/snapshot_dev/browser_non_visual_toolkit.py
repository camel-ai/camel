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
    """A lightweight, *non-visual* browser toolkit exposing primitive
    Playwright actions as CAMEL `FunctionTool`s.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        web_agent_model: Optional['BaseModelBackend'] = None,
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_browser(self):
        self._session.ensure_browser()

    def _require_page(self):
        self._session.ensure_browser()
        return self._session.page

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------
    def open_browser(self, start_url: Optional[str] = None) -> Dict[str, str]:
        """Launch a Playwright browser session.

        Args:
            start_url (Optional[str]): If provided, the page will navigate to
                this URL immediately after the browser launches.

        Returns:
            Dict[str, str]: Keys: ``result`` for action outcome,
            ``snapshot`` for full DOM snapshot.
        """
        self._session.ensure_browser()
        if start_url:
            return self.visit_page(start_url)
        # If no start_url provided, still capture initial snapshot
        snapshot = self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": "Browser session started.", "snapshot": snapshot}

    def close_browser(self) -> str:
        """Terminate the current browser session and free all resources.

        Returns:
            str: Confirmation message.
        """
        self._session.close()
        return "Browser session closed."

    # Navigation / page state ------------------------------------------------
    def visit_page(self, url: str) -> Dict[str, str]:
        """Navigate the current page to the specified URL.

        Args:
            url (str): The destination URL.

        Returns:
            Dict[str, str]: Keys: ``result`` for action outcome,
            ``snapshot`` for full DOM snapshot.
        """
        nav_result = self._session.visit(url)
        snapshot = self._session.get_snapshot(
            force_refresh=True, diff_only=False
        )
        return {"result": nav_result, "snapshot": snapshot}

    def get_page_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        """Capture a YAML-like structural snapshot of the DOM.

        Args:
            force_refresh (bool): When ``True`` always re-generate the
            snapshot even
                if the URL has not changed.
            diff_only (bool): If ``True`` return only the diff relative to the
                previous snapshot.

        Returns:
            str: Formatted snapshot string.
        """
        return self._session.get_snapshot(
            force_refresh=force_refresh, diff_only=diff_only
        )

    # Element-level wrappers -------------------------------------------------
    def click(self, *, ref: str) -> Dict[str, str]:
        """Click an element identified by ``ref``

        Args:
            ref (str): Element reference ID extracted from snapshot (e.g.
            ``"e3"``).

        Returns:
            Dict[str, str]: Result message from ``ActionExecutor``.
        """
        if not ref:
            raise ValueError("click(): 'ref' must be a non-empty string.")

        action: Dict[str, Any] = {"type": "click", "ref": ref}
        return self._exec_with_snapshot(action)

    def type(self, *, ref: str, text: str) -> Dict[str, str]:
        """Type text into an input or textarea element.

        Args:
            ref (str): Element reference ID extracted from snapshot (e.g.
            ``"e3"``).
            text (str): The text to enter.

        Returns:
            Dict[str, str]: Execution result message.
        """
        if not ref:
            raise ValueError("type(): 'ref' must be non-empty.")

        action: Dict[str, Any] = {"type": "type", "ref": ref, "text": text}
        return self._exec_with_snapshot(action)

    def select(self, *, ref: str, value: str) -> Dict[str, str]:
        """Select an option in a ``<select>`` element.

        Args:
            ref (str): Element reference ID.
            value (str): The value / option to select.

        Returns:
            Dict[str, str]: Execution result message.
        """
        if not ref:
            raise ValueError("select(): 'ref' must be non-empty.")

        action: Dict[str, Any] = {"type": "select", "ref": ref, "value": value}
        return self._exec_with_snapshot(action)

    def scroll(self, *, direction: str, amount: int) -> Dict[str, str]:
        """Scroll the page.

        Args:
            direction (str): ``"down"`` or ``"up"``.
            amount (int): Pixel distance to scroll.

        Returns:
            Dict[str, str]: Execution result message.
        """
        action = {"type": "scroll", "direction": direction, "amount": amount}
        return self._exec_with_snapshot(action)

    def wait(
        self, *, timeout_ms: int | None = None, selector: str | None = None
    ) -> Dict[str, str]:
        """Explicit wait utility.

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
        return self._exec_with_snapshot(action)

    def extract(self, *, ref: str) -> Dict[str, str]:
        """Extract text content from an element.

        Args:
            ref (str): Element reference ID obtained from snapshot.

        Returns:
            Dict[str, str]: Extracted text or error message.
        """
        if not ref:
            raise ValueError("extract(): 'ref' must be non-empty.")
        return self._exec_with_snapshot({"type": "extract", "ref": ref})

    def enter(self, *, ref: str) -> Dict[str, str]:
        """Press the Enter key.

        Args:
            ref (str): Element reference ID to focus before pressing.

        Returns:
            Dict[str, str]: Execution result message.
        """
        if not ref:
            raise ValueError("enter(): 'ref' must be non-empty.")

        action: Dict[str, Any] = {"type": "enter", "ref": ref}
        return self._exec_with_snapshot(action)

    # Helper to run through ActionExecutor
    def _exec(self, action: Dict[str, Any]) -> str:
        return self._session.exec_action(action)

    def _exec_with_snapshot(self, action: Dict[str, Any]) -> Dict[str, str]:
        """Execute action and, if DOM structure changed, include snapshot
        diff."""
        result = self._session.exec_action(action)

        # Capture structural diff to previous snapshot
        diff = self._session.get_snapshot(force_refresh=True, diff_only=True)

        if diff.startswith("- Page Snapshot (no structural changes)"):
            return {"result": result}

        return {"result": result, "snapshot": diff}

    # ------------------------------------------------------------------
    # Optional PlaywrightLLMAgent helpers
    # ------------------------------------------------------------------
    def _ensure_agent(self) -> PlaywrightLLMAgent:
        """Create PlaywrightLLMAgent on first use if `web_agent_model`
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

    def solve_task(
        self, task_prompt: str, start_url: str, max_steps: int = 15
    ) -> str:
        """Use LLM agent to autonomously complete the task (requires
        `web_agent_model`)."""
        agent = self._ensure_agent()
        agent.navigate(start_url)
        agent.process_command(task_prompt, max_steps=max_steps)
        return "Task processing finished - see stdout for detailed trace."

    # ------------------------------------------------------------------
    # Toolkit registration
    # ------------------------------------------------------------------
    def get_tools(self) -> List[FunctionTool]:
        base_tools = [
            FunctionTool(self.open_browser),
            FunctionTool(self.close_browser),
            FunctionTool(self.visit_page),
            # FunctionTool(self.get_page_snapshot),
            FunctionTool(self.click),
            FunctionTool(self.type),
            FunctionTool(self.select),
            FunctionTool(self.scroll),
            FunctionTool(self.wait),
            # FunctionTool(self.extract),
            FunctionTool(self.enter),
        ]

        if self.web_agent_model is not None:
            base_tools.append(FunctionTool(self.solve_task))

        return base_tools
