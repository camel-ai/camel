#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

"""
Debug for hybrid_browser_toolkit

Interactive command-line tool for testing and debugging browser automation
features.
Supports both visual (SoM screenshots) and non-visual (text snapshots)
operations.

Usage:
    python hybrid_browser_debug.py

Input help Show available commands
"""

import asyncio
import os
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from camel.toolkits.hybrid_browser_toolkit_py import HybridBrowserToolkit

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
grandparent_dir = os.path.dirname(parent_dir)
root_dir = os.path.dirname(grandparent_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class BrowserDebugDemo:
    """Interactive debug demo for hybrid_browser_toolkit."""

    def __init__(
        self, headless: bool = False, cache_dir: str = "debug_output"
    ):
        """Initialize the debug demo.

        Args:
            headless (bool): Whether to run browser in headless mode
        """
        self.toolkit: Optional[HybridBrowserToolkit] = None
        self.headless = headless
        self.cache_dir = Path(cache_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.command_count = 0
        self.session_dir = self.cache_dir / f"session_{self.session_id}"

    async def start(self):
        """Start the debug session."""
        print("\nStarting hybrid_browser_toolkit Debug Demo")
        print("Browser will automatically open https://google.com on startup.")
        print("Type 'help' for available commands or 'exit' to quit.\n")

        try:
            # Initialize toolkit
            self.toolkit = HybridBrowserToolkit(
                headless=self.headless,
                stealth=True,  # Enable stealth mode for bot detection evasion
                enabled_tools=HybridBrowserToolkit.ALL_TOOLS,
                browser_log_to_file=True,
            )

            # Auto-navigate to Google on startup
            print("Auto-navigating to https://google.com...")
            result = await self.toolkit.browser_open()
            print(f"Navigation result: {result}")

            # Auto-execute click e117 for testing
            # print("\nAuto-executing 'click e117' for testing...")
            # try:
            #     click_result = await self._cmd_click(['e117'])
            #     print(f"Auto-click result: {click_result}")
            # except Exception as e:
            #     print(f"Auto-click failed: {e}")
            #     import traceback
            #     traceback.print_exc()

            # Start interactive loop
            await self._interactive_loop()

        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
        except Exception as e:
            print(f"Demo failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await self._cleanup()

    async def _interactive_loop(self):
        """Main interactive command loop."""
        while True:
            try:
                # Get user input
                command = input(
                    f"[{self.command_count}] browser_debug> "
                ).strip()

                if not command:
                    continue

                self.command_count += 1

                # Parse and execute command
                result = await self._parse_and_execute(command)

                # Handle result
                await self._handle_result(command, result)

                if command.lower() in ['exit', 'quit']:
                    break

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except UnicodeDecodeError as e:
                print(f"Unicode encoding error: {e}")
                print("This might be caused by non-UTF-8 content on the page.")
                print(
                    "Try navigating to a different page or check the browser "
                    "console."
                )
            except Exception as e:
                print(f"Error executing command: {e}")
                import traceback

                print("Full traceback:")
                traceback.print_exc()

    async def _parse_and_execute(self, command: str) -> Any:
        """Parse user command and execute corresponding action.

        Args:
            command (str): User input command

        Returns:
            Any: Result from the executed action
        """
        # Parse command using shlex for proper quote handling
        try:
            parts = shlex.split(command.lower())
        except ValueError as e:
            return f"Command parsing error: {e}"

        if not parts:
            return "Empty command"

        cmd = parts[0]
        args = parts[1:]

        # Route to appropriate handler
        if cmd == 'help':
            return self._show_help()
        elif cmd == 'exit' or cmd == 'quit':
            return "Goodbye!"
        elif cmd == 'navigate':
            return await self._cmd_navigate(args)
        elif cmd == 'back':
            return await self._cmd_back(args)
        elif cmd == 'forward':
            return await self._cmd_forward(args)
        elif cmd == 'click':
            return await self._cmd_click(args)
        elif cmd == 'type':
            return await self._cmd_type(args)
        elif cmd == 'select':
            return await self._cmd_select(args)
        elif cmd == 'enter':
            return await self._cmd_enter(args)
        elif cmd == 'snapshot':
            return await self._cmd_snapshot(args)
        elif cmd == 'screenshot':
            return await self._cmd_screenshot(args)
        elif cmd == 'links':
            return await self._cmd_links(args)
        elif cmd == 'wait':
            return await self._cmd_wait(args)
        elif cmd == 'switch_tab':
            return await self._cmd_switch_tab(args)
        elif cmd == 'close_tab':
            return await self._cmd_close_tab(args)
        elif cmd == 'get_tab_info':
            return await self._cmd_get_tab_info(args)
        elif cmd == 'debug_elements':
            return await self._cmd_debug_elements(args)
        elif cmd == 'snapshot_mode':
            return await self._cmd_snapshot_mode(args)
        else:
            return (
                f"Unknown command: {cmd}. Type 'help' for available commands."
            )

    def _show_help(self) -> str:
        """Show available commands."""
        help_text = """
Available Commands:

NOTE: Browser automatically opens https://google.com on startup.

Navigation:
  navigate <url>              - Navigate to a URL
                               Example: navigate https://example.com
  back                        - Navigate back in browser history
                               Example: back
  forward                     - Navigate forward in browser history
                               Example: forward

Interaction:
  click <ref>                 - Click an element by reference
                               Example: click e5
  type <ref> <text>           - Type text into an element  
                               Example: type e3 "hello world"
  select <ref> <value>        - Select option from dropdown
                               Example: select e7 option1
  enter                       - Press the Enter key on the page
                               Example: enter

Information:
  snapshot                    - Get text snapshot of current page
  screenshot                  - Get SoM screenshot with visual marks
  links <ref1> <ref2> ...     - Get specific links by references
                               Example: links e1 e3 e5

Multi-Tab Management:
  get_tab_info              - Get information on all open tabs
  switch_tab <index>          - Switch to tab by index (e.g., switch_tab 1)
  close_tab <index>           - Close tab by index (e.g., close_tab 1)

Utilities:
  wait                        - Wait for manual user intervention
  debug_elements              - Show all available element references
  snapshot_mode               - Show current snapshot mode
  help                        - Show this help message
  exit                        - Exit the program

Tips:
- Use quotes for text with spaces: type e3 "hello world"
- References are like e1, e2, e3 (from snapshots)
- Screenshots are saved automatically to the session directory
"""
        return help_text

    async def _cmd_navigate(self, args: List[str]) -> Any:
        """Handle navigate command."""
        if not args:
            return "Usage: navigate <url>"

        url = args[0]
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_visit_page(url)
            return f"Navigated to: {url}\nFull result: {result}"
        except Exception as e:
            return f"Navigation failed: {e}"

    async def _cmd_back(self, args: List[str]) -> Any:
        """Handle back command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_back()
            return f"Navigated back in browser history\nFull result: {result}"
        except Exception as e:
            return f"Back navigation failed: {e}"

    async def _cmd_forward(self, args: List[str]) -> Any:
        """Handle forward command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_forward()
            return (
                f"Navigated forward in browser history\nFull result: {result}"
            )
        except Exception as e:
            return f"Forward navigation failed: {e}"

    async def _cmd_click(self, args: List[str]) -> Any:
        """Handle click command."""
        if not args:
            return "Usage: click <ref> (e.g., click e5)"

        ref = args[0]
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            # Debug: Check if element exists before clicking
            await self._debug_element_info(ref)

            result = await self.toolkit.browser_click(ref=ref)
            return f"Clicked element {ref}\nFull result: {result}"
        except Exception as e:
            return f"Click failed: {e}"

    async def _debug_element_info(self, ref: str) -> str:
        """Debug helper to check element information before click."""
        if self.toolkit is None:
            return "Toolkit not initialized"

        try:
            # Get page handle
            page = await self.toolkit._require_page()

            # First, run unified analysis to ensure aria-ref attributes are set
            analysis = await self.toolkit._get_unified_analysis()

            # Check if element exists in analysis
            elements = analysis.get("elements", {})
            if ref not in elements:
                print(
                    f"DEBUG: Element {ref} not found in analysis. Available "
                    f"refs: {list(elements.keys())[:10]}..."
                )
                return f"Element {ref} not found in analysis"

            element_info = elements[ref]
            print(f"DEBUG: Element {ref} info: {element_info}")

            # Check if element exists in DOM with aria-ref
            selector = f'[aria-ref="{ref}"]'
            element_count = await page.locator(selector).count()
            print(
                f"DEBUG: Found {element_count} elements with selector "
                f"{selector}"
            )

            # Check for duplicates and warn if found
            if element_count > 1:
                print(
                    f"WARNING: Multiple elements ({element_count}) found "
                    f"with selector {selector}"
                )
                print(
                    "This indicates a potential issue with element reference "
                    "assignment."
                )

                # Get details about all matching elements
                all_elements = page.locator(selector)
                for i in range(
                    min(element_count, 3)
                ):  # Check first 3 elements
                    try:
                        elem = all_elements.nth(i)
                        tag_name = await elem.evaluate("el => el.tagName")
                        text_content = await elem.text_content()
                        is_visible = await elem.is_visible()
                        print(
                            f"  Element {i}: {tag_name}, visible: "
                            f"{is_visible}, text: "
                            f"{text_content[:50] if text_content else 'None'}"
                        )
                    except Exception as e:
                        print(f"  Element {i}: Error getting details - {e}")

                # Check analysis metadata for duplicate information
                metadata = analysis.get("metadata", {})
                if metadata.get("duplicateRefsFound"):
                    print(
                        f"DEBUG: Analysis detected duplicate refs: "
                        f"{metadata.get('ariaRefCounts', {})}"
                    )

            if element_count > 0:
                # Get element details for the first element
                element = page.locator(selector).first
                is_visible = await element.is_visible()
                is_enabled = await element.is_enabled()
                tag_name = await element.evaluate("el => el.tagName")

                print(
                    f"DEBUG: First element details - Visible: {is_visible}, "
                    f"Enabled: {is_enabled}, Tag: {tag_name}"
                )

                # Try to get bounding box
                try:
                    bbox = await element.bounding_box()
                    print(f"DEBUG: Bounding box: {bbox}")
                except Exception as e:
                    print(f"DEBUG: Could not get bounding box: {e}")

            return (
                f"Debug info printed for {ref} ({element_count} elements "
                f"found)"
            )

        except Exception as e:
            print(f"DEBUG: Error getting element info: {e}")
            return f"Debug error: {e}"

    async def _cmd_debug_elements(self, args: List[str]) -> Any:
        """Handle debug_elements command - show all available elements."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            # Get analysis data
            analysis = await self.toolkit._get_unified_analysis()
            elements = analysis.get("elements", {})

            if not elements:
                return "No elements found in current page"

            output = f"Found {len(elements)} elements:\n"
            for ref, info in list(elements.items())[:20]:  # Limit to first 20
                role = info.get("role", "unknown")
                name = info.get("name", "")
                output += f"  {ref}: {role}"
                if name:
                    output += f' "{name[:30]}"'
                output += "\n"

            if len(elements) > 20:
                output += (
                    f"... and {len(elements) - 20} more elements. Use "
                    f"'snapshot' to see all."
                )

            return output

        except Exception as e:
            return f"Debug elements failed: {e}"

    async def _cmd_snapshot_mode(self, args: List[str]) -> Any:
        """Handle snapshot_mode command - show current snapshot mode."""
        if not args:
            return (
                "Current snapshot mode: FULL (actions return complete "
                "snapshots)\n"
                "Note: The toolkit has been modified to always return full "
                "snapshots after actions."
            )

        return "Snapshot mode command - currently only supports viewing mode"

    async def _cmd_type(self, args: List[str]) -> Any:
        """Handle type command."""
        if len(args) < 2:
            return "Usage: type <ref> <text> (e.g., type e3 'hello world')"

        ref = args[0]
        text = ' '.join(args[1:])

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_type(ref=ref, text=text)
            return f"Typed '{text}' into element {ref}\nFull result: {result}"
        except Exception as e:
            return f"Type failed: {e}"

    async def _cmd_select(self, args: List[str]) -> Any:
        """Handle select command."""
        if len(args) < 2:
            return "Usage: select <ref> <value> (e.g., select e7 option1)"

        ref = args[0]
        value = args[1]

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_select(ref=ref, value=value)
            return (
                f"Selected '{value}' in element {ref}\nFull result: {result}"
            )
        except Exception as e:
            return f"Select failed: {e}"

    async def _cmd_enter(self, args: List[str]) -> Any:
        """Handle enter command."""
        if args:
            return "Usage: enter (no arguments needed)"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_enter()
            return f"Pressed Enter key\nFull result: {result}"
        except Exception as e:
            return f"Enter command failed: {e}"

    async def _cmd_snapshot(self, args: List[str]) -> Any:
        """Handle snapshot command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_get_page_snapshot()
            return f"Page Snapshot:\n{result}"
        except Exception as e:
            return f"Snapshot failed: {e}"

    async def _cmd_screenshot(self, args: List[str]) -> Any:
        """Handle screenshot command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_get_som_screenshot()

            if "PIL not available" in result:
                return (
                    "Screenshot failed: PIL (Pillow) not available. "
                    "Install with: pip install Pillow"
                )

            return f"SoM Screenshot captured: {result}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    async def _cmd_links(self, args: List[str]) -> Any:
        """Handle links command."""
        if not args:
            return "Usage: links <ref1> <ref2> ... (e.g., links e1 e3 e5)"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_get_page_links(ref=args)

            return str(result).rstrip()
        except Exception as e:
            return f"Links failed: {e}"

    async def _cmd_wait(self, args: List[str]) -> Any:
        """Handle wait command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            timeout = None
            if args and args[0].isdigit():
                timeout = float(args[0])

            result = await self.toolkit.browser_wait_user(timeout_sec=timeout)
            return f"Wait completed\nFull result: {result}"
        except Exception as e:
            return f"Wait failed: {e}"

    async def _cmd_switch_tab(self, args: List[str]) -> Any:
        """Handle switch_tab command."""
        if not args or not args[0].isdigit():
            return "Usage: switch_tab <index> (e.g., switch_tab 1)"

        tab_index = int(args[0])
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            tab_info = await self.toolkit.browser_get_tab_info()
            if tab_index < len(tab_info.get('tabs', [])):
                tab_id = tab_info['tabs'][tab_index]['id']
                result = await self.toolkit.browser_switch_tab(tab_id=tab_id)
                # Don't print the full snapshot, it's too verbose
                snapshot = result.get("snapshot", "")
                if snapshot:
                    result["snapshot_preview"] = (
                        (snapshot[:100] + "...")
                        if len(snapshot) > 100
                        else snapshot
                    )
                    del result["snapshot"]

                return f"Switched to tab {tab_index}\nFull result: {result}"
            else:
                return f"Tab index {tab_index} out of range"
        except Exception as e:
            return f"Switch tab failed: {e}"

    async def _cmd_close_tab(self, args: List[str]) -> Any:
        """Handle close_tab command."""
        if not args or not args[0].isdigit():
            return "Usage: close_tab <index> (e.g., close_tab 1)"

        tab_index = int(args[0])
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            tab_info = await self.toolkit.browser_get_tab_info()
            if tab_index < len(tab_info.get('tabs', [])):
                tab_id = tab_info['tabs'][tab_index]['id']
                result = await self.toolkit.browser_close_tab(tab_id=tab_id)
                return f"Closed tab {tab_index}\nFull result: {result}"
            else:
                return f"Tab index {tab_index} out of range"
        except Exception as e:
            return f"Close tab failed: {e}"

    async def _cmd_get_tab_info(self, args: List[str]) -> Any:
        """Handle get_tab_info command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            result = await self.toolkit.browser_get_tab_info()

            if not result.get("tabs"):
                return "No open tabs."

            output = f"Total tabs: {result['total_tabs']}\n"
            output += f"Current tab: {result['current_tab']}\n\n"
            output += "Tabs:\n"

            for tab in result['tabs']:
                status = "🔥" if tab.get('is_current', False) else "  "
                output += (
                    f"{status} [{tab['index']}] {tab['title'][:60]}\n"
                    f"      URL: {tab['url']}\n"
                )

            return output
        except Exception as e:
            return f"Get tab info failed: {e}"

    async def _handle_result(self, command: str, result: Any):
        """Handle and display command result.

        Args:
            command (str): Original command
            result (Any): Result from command execution
        """
        if isinstance(result, str):
            print(result)
        else:
            print(f"Result: {result}")

    async def _cleanup(self):
        """Cleanup resources."""
        if self.toolkit:
            try:
                await self.toolkit.browser_close()
                print("Browser closed")
            except Exception as e:
                print(f"Cleanup warning: {e}")


async def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Hybrid_BrowserToolkit Debug")
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode"
    )
    parser.add_argument(
        "--cache-dir",
        default="debug_output",
        help="Directory to save screenshots and outputs (default: "
        "debug_output)",
    )

    args = parser.parse_args()

    demo = BrowserDebugDemo(headless=args.headless, cache_dir=args.cache_dir)

    await demo.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except Exception as e:
        print(f"Program failed: {e}")
        sys.exit(1)