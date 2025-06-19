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
import time
from typing import Any, Dict

from playwright.sync_api import Page


class ActionExecutor:
    """Executes high-level actions (click, type …) on a Playwright Page."""

    def __init__(self, page: Page):
        self.page = page

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def execute(self, action: Dict[str, Any]) -> str:
        if not action:
            return "No action to execute"

        action_type = action.get("type")
        if not action_type:
            return "Error: action has no type"

        try:
            # small helper to ensure basic stability
            self._wait_dom_stable()

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

            return handler(action)
        except Exception as exc:
            return f"Error executing {action_type}: {exc}"

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    def _click(self, action):
        ref = action.get("ref")
        text = action.get("text")
        selector = action.get("selector")
        if not (ref or text or selector):
            return "Error: click requires ref/text/selector"

        strategies = []
        if selector:
            strategies.append(selector)
        if text:
            strategies.append(f'text="{text}"')
        if ref:
            strategies.append(f"[aria-ref='{ref}']")

        for sel in strategies:
            try:
                if self.page.locator(sel).count() > 0:
                    self.page.click(sel, timeout=2000, force=True)
                    return f"Clicked element via {sel}"
            except Exception:
                pass
        return "Error: Could not click element"

    def _type(self, action):
        ref = action.get("ref")
        selector = action.get("selector")
        text = action.get("text", "")
        if not (ref or selector):
            return "Error: type requires ref/selector"
        target = selector or f"[aria-ref='{ref}']"
        try:
            self.page.fill(target, text, timeout=2000)
            return f"Typed '{text}' into {target}"
        except Exception as exc:
            return f"Type failed: {exc}"

    def _select(self, action):
        ref = action.get("ref")
        selector = action.get("selector")
        value = action.get("value", "")
        if not (ref or selector):
            return "Error: select requires ref/selector"
        target = selector or f"[aria-ref='{ref}']"
        try:
            self.page.select_option(target, value, timeout=10000)
            return f"Selected '{value}' in {target}"
        except Exception as exc:
            return f"Select failed: {exc}"

    def _wait(self, action):
        if "timeout" in action:
            ms = action["timeout"]
            time.sleep(ms / 1000)
            return f"Waited {ms}ms"
        if "selector" in action:
            sel = action["selector"]
            self.page.wait_for_selector(sel, timeout=10000)
            return f"Waited for {sel}"
        return "Error: wait requires timeout/selector"

    def _extract(self, action):
        ref = action.get("ref")
        if not ref:
            return "Error: extract requires ref"
        target = f"[aria-ref='{ref}']"
        self.page.wait_for_selector(target, timeout=10000)
        txt = self.page.text_content(target)
        return f"Extracted: {txt[:100] if txt else 'None'}"

    def _scroll(self, action):
        direction = action.get("direction", "down")
        amount = action.get("amount", 300)
        self.page.evaluate(
            f"window.scrollBy(0, "
            f"{amount if direction == 'down' else -amount})"
        )
        time.sleep(0.5)
        return f"Scrolled {direction} by {amount}px"

    def _enter(self, action):
        ref = action.get("ref")
        selector = action.get("selector")
        if ref:
            self.page.focus(f"[aria-ref='{ref}']")
        elif selector:
            self.page.focus(selector)
        self.page.keyboard.press("Enter")
        time.sleep(0.3)
        return "Pressed Enter"

    # utilities
    def _wait_dom_stable(self):
        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=2000)
        except Exception:
            pass

    # static helpers
    @staticmethod
    def should_update_snapshot(action: Dict[str, Any]) -> bool:
        change_types = {
            "click",
            "type",
            "select",
            "scroll",
            "navigate",
            "enter",
        }
        return action.get("type") in change_types
