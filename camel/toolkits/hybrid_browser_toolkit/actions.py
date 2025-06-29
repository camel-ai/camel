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
import asyncio
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from playwright.async_api import Page


class ActionExecutor:
    r"""Executes high-level actions (click, type …) on a Playwright Page."""

    # Configuration constants
    DEFAULT_TIMEOUT = 5000  # 5 seconds
    SHORT_TIMEOUT = 2000  # 2 seconds
    MAX_SCROLL_AMOUNT = 5000  # Maximum scroll distance in pixels

    def __init__(self, page: "Page"):
        self.page = page

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    async def execute(self, action: Dict[str, Any]) -> str:
        r"""Execute an action and return the result description."""
        if not action:
            return "No action to execute"

        action_type = action.get("type")
        if not action_type:
            return "Error: action has no type"

        try:
            # small helper to ensure basic stability
            await self._wait_dom_stable()

            handler = {
                "click": self._click,
                "type": self._type,
                "select": self._select,
                "wait": self._wait,
                "extract": self._extract,
                "scroll": self._scroll,
                "enter": self._enter,
            }.get(action_type)

            if handler is None:
                return f"Error: Unknown action type '{action_type}'"

            return await handler(action)
        except Exception as exc:
            return f"Error executing {action_type}: {exc}"

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    async def _click(self, action: Dict[str, Any]) -> str:
        r"""Handle click actions with multiple fallback strategies."""
        ref = action.get("ref")
        text = action.get("text")
        selector = action.get("selector")
        if not (ref or text or selector):
            return "Error: click requires ref/text/selector"

        # Build strategies in priority order: ref > selector > text
        strategies = []
        if ref:
            strategies.append(f"[aria-ref='{ref}']")
        if selector:
            strategies.append(selector)
        if text:
            strategies.append(f'text="{text}"')

        # Strategy 1: Try Playwright force click for each selector
        for sel in strategies:
            try:
                if await self.page.locator(sel).count() > 0:
                    await self.page.click(
                        sel, timeout=self.DEFAULT_TIMEOUT, force=True
                    )
                    return f"Clicked element via force: {sel}"
            except Exception:
                continue

        # Strategy 2: Try JavaScript click as fallback
        for sel in strategies:
            try:
                await self.page.locator(sel).first.evaluate("el => el.click()")
                await asyncio.sleep(0.1)  # Brief wait for effects
                return f"Clicked element via JS: {sel}"
            except Exception:
                continue

        return "Error: All click strategies failed"

    async def _type(self, action: Dict[str, Any]) -> str:
        r"""Handle typing text into input fields."""
        ref = action.get("ref")
        selector = action.get("selector")
        text = action.get("text", "")
        if not (ref or selector):
            return "Error: type requires ref/selector"
        target = selector or f"[aria-ref='{ref}']"
        try:
            await self.page.fill(target, text, timeout=self.SHORT_TIMEOUT)
            return f"Typed '{text}' into {target}"
        except Exception as exc:
            return f"Type failed: {exc}"

    async def _select(self, action: Dict[str, Any]) -> str:
        r"""Handle selecting options from dropdowns."""
        ref = action.get("ref")
        selector = action.get("selector")
        value = action.get("value", "")
        if not (ref or selector):
            return "Error: select requires ref/selector"
        target = selector or f"[aria-ref='{ref}']"
        try:
            await self.page.select_option(
                target, value, timeout=self.DEFAULT_TIMEOUT
            )
            return f"Selected '{value}' in {target}"
        except Exception as exc:
            return f"Select failed: {exc}"

    async def _wait(self, action: Dict[str, Any]) -> str:
        r"""Handle wait actions."""
        if "timeout" in action:
            ms = int(action["timeout"])
            await asyncio.sleep(ms / 1000)
            return f"Waited {ms}ms"
        if "selector" in action:
            sel = action["selector"]
            await self.page.wait_for_selector(
                sel, timeout=self.DEFAULT_TIMEOUT
            )
            return f"Waited for {sel}"
        return "Error: wait requires timeout/selector"

    async def _extract(self, action: Dict[str, Any]) -> str:
        r"""Handle text extraction from elements."""
        ref = action.get("ref")
        if not ref:
            return "Error: extract requires ref"
        target = f"[aria-ref='{ref}']"
        await self.page.wait_for_selector(target, timeout=self.DEFAULT_TIMEOUT)
        txt = await self.page.text_content(target)
        return f"Extracted: {txt[:100] if txt else 'None'}"

    async def _scroll(self, action: Dict[str, Any]) -> str:
        r"""Handle page scrolling with safe parameter validation."""
        direction = action.get("direction", "down")
        amount = action.get("amount", 300)

        # Validate inputs to prevent injection
        if direction not in ("up", "down"):
            return "Error: direction must be 'up' or 'down'"

        try:
            # Safely convert amount to integer and clamp to reasonable range
            amount_int = int(amount)
            amount_int = max(
                -self.MAX_SCROLL_AMOUNT,
                min(self.MAX_SCROLL_AMOUNT, amount_int),
            )  # Clamp to MAX_SCROLL_AMOUNT range
        except (ValueError, TypeError):
            return "Error: amount must be a valid number"

        # Use safe evaluation with bound parameters
        scroll_offset = amount_int if direction == "down" else -amount_int
        await self.page.evaluate(
            "offset => window.scrollBy(0, offset)", scroll_offset
        )
        await asyncio.sleep(0.5)
        return f"Scrolled {direction} by {abs(amount_int)}px"

    async def _enter(self, action: Dict[str, Any]) -> str:
        r"""Handle Enter key press actions."""
        ref = action.get("ref")
        selector = action.get("selector")
        if ref:
            await self.page.focus(f"[aria-ref='{ref}']")
        elif selector:
            await self.page.focus(selector)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(0.3)
        return "Pressed Enter"

    # utilities
    async def _wait_dom_stable(self) -> None:
        r"""Wait for DOM to become stable before executing actions."""
        try:
            # Wait for basic DOM content loading
            await self.page.wait_for_load_state(
                'domcontentloaded', timeout=self.SHORT_TIMEOUT
            )

            # Try to wait for network idle briefly
            try:
                await self.page.wait_for_load_state(
                    'networkidle', timeout=self.SHORT_TIMEOUT
                )
            except Exception:
                pass  # Network idle is optional

        except Exception:
            pass  # Don't fail if wait times out

    # static helpers
    @staticmethod
    def should_update_snapshot(action: Dict[str, Any]) -> bool:
        r"""Determine if an action requires a snapshot update."""
        change_types = {
            "click",
            "type",
            "select",
            "scroll",
            "navigate",
            "enter",
        }
        return action.get("type") in change_types
