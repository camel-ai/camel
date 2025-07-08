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
from typing import TYPE_CHECKING, Any, Dict, Optional

from .config_loader import ConfigLoader

if TYPE_CHECKING:
    from playwright.async_api import Page


class ActionExecutor:
    r"""Executes high-level actions (click, type …) on a Playwright Page."""

    def __init__(
        self,
        page: "Page",
        session: Optional[Any] = None,
        default_timeout: Optional[int] = None,
        short_timeout: Optional[int] = None,
        max_scroll_amount: Optional[int] = None,
    ):
        self.page = page
        self.session = session  # HybridBrowserSession instance

        # Configure timeouts using the config file with optional overrides
        self.default_timeout = ConfigLoader.get_action_timeout(default_timeout)
        self.short_timeout = ConfigLoader.get_short_timeout(short_timeout)
        self.max_scroll_amount = ConfigLoader.get_max_scroll_amount(
            max_scroll_amount
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Execute an action and return detailed result information."""
        if not action:
            return {
                "success": False,
                "message": "No action to execute",
                "details": {},
            }

        action_type = action.get("type")
        if not action_type:
            return {
                "success": False,
                "message": "Error: action has no type",
                "details": {},
            }

        try:
            # small helper to ensure basic stability
            # await self._wait_dom_stable()

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
                return {
                    "success": False,
                    "message": f"Error: Unknown action type '{action_type}'",
                    "details": {"action_type": action_type},
                }

            result = await handler(action)
            return {
                "success": True,
                "message": result["message"],
                "details": result.get("details", {}),
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Error executing {action_type}: {exc}",
                "details": {"action_type": action_type, "error": str(exc)},
            }

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    async def _click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle click actions with new tab support for any clickable
        element."""
        ref = action.get("ref")
        text = action.get("text")
        selector = action.get("selector")
        if not (ref or text or selector):
            return {
                "message": "Error: click requires ref/text/selector",
                "details": {"error": "missing_selector"},
            }

        # Build strategies in priority order
        strategies = []
        if ref:
            strategies.append(f"[aria-ref='{ref}']")
        if selector:
            strategies.append(selector)
        if text:
            strategies.append(f'text="{text}"')

        details: Dict[str, Any] = {
            "ref": ref,
            "selector": selector,
            "text": text,
            "strategies_tried": [],
            "successful_strategy": None,
            "click_method": None,
            "new_tab_created": False,
        }

        # Find the first valid selector
        found_selector = None
        for sel in strategies:
            if await self.page.locator(sel).count() > 0:
                found_selector = sel
                break

        if not found_selector:
            details['error'] = "Element not found with any strategy"
            return {
                "message": "Error: Click failed, element not found",
                "details": details,
            }

        element = self.page.locator(found_selector).first
        details['successful_strategy'] = found_selector

        # Attempt ctrl+click first (always)
        try:
            if self.session:
                async with self.page.context.expect_page(
                    timeout=self.short_timeout
                ) as new_page_info:
                    await element.click(modifiers=["ControlOrMeta"])
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded')
                new_tab_index = await self.session.register_page(new_page)
                if new_tab_index is not None:
                    await self.session.switch_to_tab(new_tab_index)
                    self.page = new_page
                details.update(
                    {
                        "click_method": "ctrl_click_new_tab",
                        "new_tab_created": True,
                        "new_tab_index": new_tab_index,
                    }
                )
                return {
                    "message": f"Clicked element (ctrl click), opened in new "
                    f"tab {new_tab_index}",
                    "details": details,
                }
            else:
                await element.click(modifiers=["ControlOrMeta"])
                details["click_method"] = "ctrl_click_no_session"
                return {
                    "message": f"Clicked element (ctrl click, no"
                    f" session): {found_selector}",
                    "details": details,
                }
        except asyncio.TimeoutError:
            # No new tab was opened, click may have still worked
            details["click_method"] = "ctrl_click_same_tab"
            return {
                "message": f"Clicked element (ctrl click, "
                f"same tab): {found_selector}",
                "details": details,
            }
        except Exception as e:
            details['strategies_tried'].append(
                {
                    'selector': found_selector,
                    'method': 'ctrl_click',
                    'error': str(e),
                }
            )
            # Fall through to fallback

        # Fallback to normal force click if ctrl+click fails
        try:
            await element.click(force=True, timeout=self.default_timeout)
            details["click_method"] = "playwright_force_click"
            return {
                "message": f"Fallback clicked element: {found_selector}",
                "details": details,
            }
        except Exception as e:
            details["click_method"] = "playwright_force_click_failed"
            details["error"] = str(e)
            return {
                "message": f"Error: All click strategies "
                f"failed for {found_selector}",
                "details": details,
            }

    async def _type(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle typing text into input fields."""
        ref = action.get("ref")
        selector = action.get("selector")
        text = action.get("text", "")
        if not (ref or selector):
            return {
                "message": "Error: type requires ref/selector",
                "details": {"error": "missing_selector"},
            }

        target = selector or f"[aria-ref='{ref}']"
        details = {
            "ref": ref,
            "selector": selector,
            "target": target,
            "text": text,
            "text_length": len(text),
        }

        try:
            await self.page.fill(target, text, timeout=self.short_timeout)
            return {
                "message": f"Typed '{text}' into {target}",
                "details": details,
            }
        except Exception as exc:
            details["error"] = str(exc)
            return {"message": f"Type failed: {exc}", "details": details}

    async def _select(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle selecting options from dropdowns."""
        ref = action.get("ref")
        selector = action.get("selector")
        value = action.get("value", "")
        if not (ref or selector):
            return {
                "message": "Error: select requires ref/selector",
                "details": {"error": "missing_selector"},
            }

        target = selector or f"[aria-ref='{ref}']"
        details = {
            "ref": ref,
            "selector": selector,
            "target": target,
            "value": value,
        }

        try:
            await self.page.select_option(
                target, value, timeout=self.default_timeout
            )
            return {
                "message": f"Selected '{value}' in {target}",
                "details": details,
            }
        except Exception as exc:
            details["error"] = str(exc)
            return {"message": f"Select failed: {exc}", "details": details}

    async def _wait(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle wait actions."""
        details: Dict[str, Any] = {
            "wait_type": None,
            "timeout": None,
            "selector": None,
        }

        if "timeout" in action:
            ms = int(action["timeout"])
            details["wait_type"] = "timeout"
            details["timeout"] = ms
            await asyncio.sleep(ms / 1000)
            return {"message": f"Waited {ms}ms", "details": details}
        if "selector" in action:
            sel = action["selector"]
            details["wait_type"] = "selector"
            details["selector"] = sel
            await self.page.wait_for_selector(
                sel, timeout=self.default_timeout
            )
            return {"message": f"Waited for {sel}", "details": details}
        return {
            "message": "Error: wait requires timeout/selector",
            "details": details,
        }

    async def _extract(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle text extraction from elements."""
        ref = action.get("ref")
        if not ref:
            return {
                "message": "Error: extract requires ref",
                "details": {"error": "missing_ref"},
            }

        target = f"[aria-ref='{ref}']"
        details = {"ref": ref, "target": target}

        await self.page.wait_for_selector(target, timeout=self.default_timeout)
        txt = await self.page.text_content(target)

        details["extracted_text"] = txt
        details["text_length"] = len(txt) if txt else 0

        return {
            "message": f"Extracted: {txt[:100] if txt else 'None'}",
            "details": details,
        }

    async def _scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle page scrolling with safe parameter validation."""
        direction = action.get("direction", "down")
        amount = action.get("amount", 300)

        details = {
            "direction": direction,
            "requested_amount": amount,
            "actual_amount": None,
            "scroll_offset": None,
        }

        # Validate inputs to prevent injection
        if direction not in ("up", "down"):
            return {
                "message": "Error: direction must be 'up' or 'down'",
                "details": details,
            }

        try:
            # Safely convert amount to integer and clamp to reasonable range
            amount_int = int(amount)
            amount_int = max(
                -self.max_scroll_amount,
                min(self.max_scroll_amount, amount_int),
            )  # Clamp to max_scroll_amount range
            details["actual_amount"] = amount_int
        except (ValueError, TypeError):
            return {
                "message": "Error: amount must be a valid number",
                "details": details,
            }

        # Use safe evaluation with bound parameters
        scroll_offset = amount_int if direction == "down" else -amount_int
        details["scroll_offset"] = scroll_offset

        await self.page.evaluate(
            "offset => window.scrollBy(0, offset)", scroll_offset
        )
        await asyncio.sleep(0.5)
        return {
            "message": f"Scrolled {direction} by {abs(amount_int)}px",
            "details": details,
        }

    async def _enter(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Handle Enter key press on the currently focused element."""
        details = {"action_type": "enter", "target": "focused_element"}

        # Press Enter on whatever element currently has focus
        await self.page.keyboard.press("Enter")
        return {
            "message": "Pressed Enter on focused element",
            "details": details,
        }

    # utilities
    async def _wait_dom_stable(self) -> None:
        r"""Wait for DOM to become stable before executing actions."""
        try:
            # Wait for basic DOM content loading
            await self.page.wait_for_load_state(
                'domcontentloaded', timeout=self.short_timeout
            )

            # Try to wait for network idle briefly
            try:
                await self.page.wait_for_load_state(
                    'networkidle', timeout=self.short_timeout
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
