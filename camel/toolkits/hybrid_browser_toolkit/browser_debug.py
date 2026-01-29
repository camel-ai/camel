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
from typing import Any, Dict, List, Literal, Optional, Set, Union

from camel.toolkits.hybrid_browser_toolkit import HybridBrowserToolkit
from camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts import (
    HybridBrowserToolkit as TSToolkit,
)
from camel.toolkits.hybrid_browser_toolkit_py import (
    HybridBrowserToolkit as PyToolkit,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
grandparent_dir = os.path.dirname(parent_dir)
root_dir = os.path.dirname(grandparent_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class BrowserDebugDemo:
    """Interactive debug demo for hybrid_browser_toolkit."""

    @staticmethod
    def _extract_all_tools_from_files() -> Set[str]:
        """Extract ALL_TOOLS from both TypeScript and Python implementations."""
        # Simply get the union of ALL_TOOLS from both implementations
        all_tools = set()

        try:
            # Get from TypeScript implementation
            all_tools.update(TSToolkit.ALL_TOOLS)
        except Exception as e:
            print(f"Warning: Could not get ALL_TOOLS from TSToolkit: {e}")

        try:
            # Get from Python implementation
            all_tools.update(PyToolkit.ALL_TOOLS)
        except Exception as e:
            print(f"Warning: Could not get ALL_TOOLS from PyToolkit: {e}")

        return all_tools

    @staticmethod
    def _generate_tool_command_map() -> Dict[str, tuple[str, str]]:
        """Generate mapping from tool names to command names and handlers."""
        # Extract all tools from files
        all_tools = BrowserDebugDemo._extract_all_tools_from_files()

        # Generate mapping based on naming conventions
        tool_map = {}
        for tool in all_tools:
            if tool.startswith("browser_"):
                # Remove browser_ prefix
                base_name = tool[8:]  # len("browser_") = 8

                # Special cases and naming conventions
                if base_name == "visit_page":
                    cmd_name = "navigate"
                elif base_name == "get_page_snapshot":
                    cmd_name = "snapshot"
                elif base_name == "get_som_screenshot":
                    cmd_name = "screenshot"
                elif base_name == "get_page_links":
                    cmd_name = "links"
                elif base_name == "wait_user":
                    cmd_name = "wait"
                elif base_name == "solve_task":
                    cmd_name = "solve"  # Special command for solve_task
                else:
                    cmd_name = base_name

                # Generate handler name
                handler_name = f"_cmd_{cmd_name}"

                tool_map[tool] = (cmd_name, handler_name)

        return tool_map

    def __init__(
        self,
        mode: Literal["typescript", "python"] = "typescript",
        headless: bool = False,
        cache_dir: str = "debug_output",
    ):
        """Initialize the debug demo.

        Args:
            mode (Literal["typescript", "python"]): Browser toolkit mode.
                Defaults to "typescript".
            headless (bool): Whether to run browser in headless mode.
                Defaults to False.
            cache_dir (str): Directory for debug output.
                Defaults to "debug_output".
        """
        self.toolkit: Optional[Union[TSToolkit, PyToolkit]] = None
        self.mode = mode
        self.headless = headless
        self.cache_dir = Path(cache_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.command_count = 0
        self.session_dir = self.cache_dir / f"session_{self.session_id}"
        self.available_commands: dict = {}  # Will be populated after toolkit init
        self.tool_info: dict = {}  # Store tool name -> (cmd_name, docstring)
        self.tool_command_map = self._generate_tool_command_map()

    async def start(self):
        """Start the debug session."""
        print("\nStarting hybrid_browser_toolkit Debug Demo")
        print(f"Mode: {self.mode.upper()}")
        print("Browser will automatically open https://google.com on startup.")
        print("Type 'help' for available commands or 'exit' to quit.\n")

        try:
            # Initialize toolkit
            if self.mode == "python":
                print("Note: Python mode has the following limitations:")
                print("  - No CDP connection support")
                print("  - No viewport_limit support")
                print()

            # Get ALL_TOOLS from the appropriate implementation
            if self.mode == "typescript":
                all_tools = TSToolkit.ALL_TOOLS
            else:
                all_tools = PyToolkit.ALL_TOOLS

            self.toolkit = HybridBrowserToolkit(
                mode=self.mode,
                headless=self.headless,
                stealth=True,
                enabled_tools=all_tools,
                browser_log_to_file=True,
                user_data_dir=r"C:\Users\moizh\workspace\camel\working_dir\debug",
            )

            # Build available commands based on enabled tools
            self._build_available_commands()

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

    def _build_available_commands(self):
        """Build available commands based on enabled tools."""
        if not self.toolkit:
            return

        # Get enabled tools from toolkit
        # Since HybridBrowserToolkit is a factory, get ALL_TOOLS from the implementation
        if self.mode == "typescript":
            default_tools = TSToolkit.ALL_TOOLS
        else:
            default_tools = PyToolkit.ALL_TOOLS

        enabled_tools = getattr(self.toolkit, 'enabled_tools', default_tools)

        # Build command map and store tool info
        self.tool_info = {}  # Store tool name -> (cmd_name, docstring)

        for tool_name, (
            cmd_name,
            handler_name,
        ) in self.tool_command_map.items():
            if tool_name in enabled_tools:
                handler = getattr(self, handler_name, None)
                if handler:
                    self.available_commands[cmd_name] = handler
                elif cmd_name == "solve":
                    # Special handling for solve_task - create a simple wrapper
                    self.available_commands[cmd_name] = (
                        self._create_solve_handler()
                    )

                # Try to get docstring from toolkit method
                toolkit_method = getattr(self.toolkit, tool_name, None)
                if toolkit_method and hasattr(toolkit_method, '__doc__'):
                    self.tool_info[cmd_name] = (
                        tool_name,
                        toolkit_method.__doc__,
                    )
                else:
                    self.tool_info[cmd_name] = (tool_name, None)

        # Add built-in commands that are always available
        self.available_commands.update(
            {
                'help': self._show_help,
                'exit': lambda args: "Goodbye!",
                'quit': lambda args: "Goodbye!",
                'debug_elements': self._cmd_debug_elements,
                'snapshot_mode': self._cmd_snapshot_mode,
            }
        )

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
            parts = shlex.split(command)
        except ValueError as e:
            return f"Command parsing error: {e}"

        if not parts:
            return "Empty command"

        cmd = parts[0]
        args = parts[1:]

        # Look up command in available commands
        handler = self.available_commands.get(cmd)
        if handler:
            # Check if it's a coroutine (async function)
            import inspect

            if inspect.iscoroutinefunction(handler):
                return await handler(args)
            else:
                return handler(args)
        else:
            return (
                f"Unknown command: {cmd}. Type 'help' for available commands."
            )

    def _extract_docstring_description(self, docstring: str) -> str:
        """Extract the first line or paragraph from a docstring."""
        if not docstring:
            return ""

        # Clean up the docstring
        lines = docstring.strip().split('\n')
        description_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith(
                ('Args:', 'Returns:', 'Raises:', 'Note:', 'Example:')
            ):
                description_lines.append(line)
            elif line.startswith(('Args:', 'Returns:')):
                break

        return ' '.join(description_lines).strip()

    def _show_help(self, args: Optional[List[str]] = None) -> str:
        """Show available commands with descriptions from docstrings."""
        help_text = f"""
Available Commands:

MODE: {self.mode.upper()}
NOTE: Browser automatically opens https://google.com on startup.

All commands are dynamically mapped from the {self.mode} toolkit implementation.
================================================================================

"""

        # Get all commands except built-in ones
        browser_commands = []
        for cmd in sorted(self.available_commands.keys()):
            if cmd not in [
                'help',
                'exit',
                'quit',
                'debug_elements',
                'snapshot_mode',
            ]:
                # Get tool info
                tool_info = self.tool_info.get(cmd, (None, None))
                tool_name, docstring = tool_info
                description = (
                    self._extract_docstring_description(docstring)
                    if docstring
                    else "No description available"
                )
                browser_commands.append((cmd, tool_name, description))

        # Show all browser commands with their docstrings
        if browser_commands:
            help_text += "Browser Commands:\n"
            help_text += "-" * 80 + "\n"
            for cmd, tool_name, desc in browser_commands:
                # Command name with tool mapping
                help_text += f"\n{cmd}"
                if tool_name:
                    help_text += f" (maps to: {tool_name})"
                help_text += "\n"

                # Description
                help_text += f"  {desc}\n"

                # Usage examples for specific commands
                if cmd == 'navigate':
                    help_text += "  Usage: navigate <url>\n"
                    help_text += "  Example: navigate https://example.com\n"
                elif cmd == 'click':
                    help_text += "  Usage: click <ref>\n"
                    help_text += "  Example: click e5\n"
                elif cmd == 'type':
                    help_text += (
                        "  Usage: type <text> <ref> [<text2> <ref2> ...]\n"
                    )
                    help_text += (
                        "  Example (single): type \"hello world\" e3\n"
                    )
                    help_text += "  Example (multiple): type \"123\" e1 \"456\" e2 \"789\" e3\n"
                elif cmd == 'select':
                    help_text += "  Usage: select <ref> <value>\n"
                    help_text += "  Example: select e7 option1\n"
                elif cmd == 'scroll':
                    help_text += "  Usage: scroll <direction> [amount]\n"
                    help_text += "  Example: scroll down 500\n"
                elif cmd == 'links':
                    help_text += "  Usage: links <ref1> <ref2> ...\n"
                    help_text += "  Example: links e1 e3 e5\n"
                elif cmd == 'switch_tab':
                    help_text += "  Usage: switch_tab <tab_id>\n"
                    help_text += (
                        "  Example: switch_tab tab-001 or switch_tab 1\n"
                    )
                elif cmd == 'close_tab':
                    help_text += "  Usage: close_tab <tab_id>\n"
                    help_text += (
                        "  Example: close_tab tab-001 or close_tab 1\n"
                    )
                elif cmd == 'wait':
                    help_text += "  Usage: wait [timeout_seconds]\n"
                    help_text += "  Example: wait 5\n"
                elif cmd == 'solve':
                    help_text += "  Usage: solve <task_description>\n"
                    help_text += "  Example: solve \"find and click the login button\"\n"
                elif cmd == 'mouse_control':
                    help_text += (
                        "  Usage: mouse_control <control_type> <x> <y>\n"
                    )
                    help_text += "  Example: mouse_control click 100 200\n"
                elif cmd == 'mouse_drag':
                    help_text += "  Usage: mouse_drag <from_ref> <to_ref>\n"
                    help_text += "  Example: mouse_drag e1 e5\n"
                elif cmd == 'press_key':
                    help_text += "  Usage: press_key <key1> [key2] ...\n"
                    help_text += "  Example: press_key Ctrl a\n"
                elif cmd == 'console_exec':
                    help_text += "  Usage: console_exec <javascript_code>\n"
                    help_text += "  Example: console_exec \"document.title\"\n"

        # Add built-in utilities
        help_text += "\n" + "=" * 80 + "\n"
        help_text += "Built-in Debug Commands:\n"
        help_text += "-" * 80 + "\n"
        help_text += "  debug_elements  - Show all available element references on current page\n"
        help_text += (
            "  snapshot_mode   - Show current snapshot mode information\n"
        )
        help_text += "  help           - Show this help message\n"
        help_text += "  exit/quit      - Exit the debug session\n"

        help_text += "\n" + "=" * 80 + "\n"
        help_text += "Tips:\n"
        help_text += "- Element references (e.g., e1, e2, e3) are obtained from snapshots\n"
        help_text += (
            "- Use quotes for text with spaces: type e3 \"hello world\"\n"
        )
        help_text += "- Run 'snapshot' to see all interactive elements on the current page\n"

        # Add mode-specific notes
        if self.mode == "python":
            help_text += "\nNote: Running in Python mode. CDP connection and viewport_limit are not supported.\n"
        elif self.mode == "typescript":
            help_text += "\nNote: Running in TypeScript mode with full feature support.\n"

        # Show statistics
        help_text += f"\nTotal available commands: {len(browser_commands)}\n"

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

            result = await self.toolkit.browser_click(ref=ref)
            return f"Clicked element {ref}\nFull result: {result}"
        except Exception as e:
            return f"Click failed: {e}"

    # Note: _debug_element_info method removed as it accessed internal implementation details
    # The toolkit's public API should be used instead

    async def _cmd_debug_elements(self, args: List[str]) -> Any:
        """Handle debug_elements command - show all available elements."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            # Get a snapshot to see available elements
            snapshot = await self.toolkit.browser_get_page_snapshot()

            # Simple parsing to extract element references
            import re

            refs = re.findall(r'\[e\d+\]', snapshot)
            unique_refs = sorted(set(refs))

            if not unique_refs:
                return "No element references found in current page"

            output = f"Found {len(unique_refs)} element references:\n"
            output += ", ".join(unique_refs[:50])  # Show first 50

            if len(unique_refs) > 50:
                output += f"\n... and {len(unique_refs) - 50} more elements."

            output += "\n\nUse 'snapshot' to see the full page content with element details."

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
        """Handle type command to input text into one or more elements.

        Supports two modes:
        1. Single input mode: Types text into a single element
        2. Multiple inputs mode: Types different text into multiple elements in one call

        The mode is automatically detected based on the number of arguments:
        - If args count is 2: Single input mode
        - If args count > 2 and even: Multiple inputs mode
        - Otherwise: Error (odd number of args > 2)

        Args:
            args (List[str]): Command arguments in one of these formats:
                - Single mode: [text, ref]
                - Multiple mode: [text1, ref1, text2, ref2, ...]
                where:
                - text: The text to type into the element
                - ref: The element reference ID (e.g., 'e1', 'e23')

        Returns:
            str: Success message with typed content summary and full result,
                 or error message if the operation fails.

        Examples:
            Single input:
                >>> type "hello world" e3
                Typed 'hello world' into element e3

            Multiple inputs:
                >>> type "username" e1 "password" e2
                Typed multiple inputs: username -> e1, password -> e2

            Multiple inputs with quotes:
                >>> type "Standard PO (NB)" e5 "Group 001" e7 "Company 1710" e9
                Typed multiple inputs: Standard PO (NB) -> e5, Group 001 -> e7, Company 1710 -> e9
        """
        if len(args) < 2:
            return "Usage: type <text> <ref> [<text2> <ref2> ...]\nExample: type 'hello' e3\nExample: type 'username' e1 'password' e2"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            # Check if this is multiple inputs mode (more than 2 args and even number)
            if len(args) > 2 and len(args) % 2 == 0:
                # Multiple inputs mode: text1 ref1 text2 ref2 ...
                inputs = []
                for i in range(0, len(args), 2):
                    text = args[i]
                    ref = args[i + 1]
                    inputs.append({'text': text, 'ref': ref})

                result = await self.toolkit.browser_type(inputs=inputs)  # type: ignore[call-arg]

                # Format output
                input_summary = ", ".join(
                    [f"{inp['text']} -> {inp['ref']}" for inp in inputs]
                )
                return f"Typed multiple inputs: {input_summary}\nFull result: {result}"
            else:
                # Single input mode: text ref
                text = args[0]
                ref = args[1]

                result = await self.toolkit.browser_type(ref=ref, text=text)
                return (
                    f"Typed '{text}' into element {ref}\nFull result: {result}"
                )

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

            result_text = getattr(result, 'text', str(result))
            if "PIL not available" in result_text:
                return (
                    "Screenshot failed: PIL (Pillow) not available. "
                    "Install with: pip install Pillow"
                )

            return f"SoM Screenshot captured: {result_text}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    async def _cmd_links(self, args: List[str]) -> Any:
        """Handle links command."""
        if not args:
            return "Usage: links <ref1> <ref2> ... (e.g., links e1 e3 e5)"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_get_page_links(ref=args)  # type: ignore[union-attr]

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
        if not args:
            return "Usage: switch_tab <tab_id> (e.g., switch_tab tab-001 or switch_tab 1)"

        if self.toolkit is None:
            return "Toolkit not initialized"

        tab_id = args[0]

        # Support both numeric index and tab ID format
        if tab_id.isdigit():
            # If it's a number, get tab info to find the actual tab ID
            try:
                tab_info = await self.toolkit.browser_get_tab_info()
                tabs = tab_info.get('tabs', [])
                tab_index = int(tab_id)

                # Find tab by index
                if 0 <= tab_index < len(tabs):
                    actual_tab_id = tabs[tab_index].get('tab_id')
                    if actual_tab_id:
                        tab_id = actual_tab_id
                    else:
                        return f"Tab at index {tab_index} has no tab_id"
                else:
                    return f"Invalid tab index {tab_index}. Available: 0-{len(tabs) - 1}"
            except Exception as e:
                return f"Failed to get tab info: {e}"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
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

            return f"Switched to tab {tab_id}\nFull result: {result}"
        except Exception as e:
            return f"Switch tab failed: {e}"

    async def _cmd_close_tab(self, args: List[str]) -> Any:
        """Handle close_tab command."""
        if not args:
            return "Usage: close_tab <tab_id> (e.g., close_tab tab-001 or close_tab 1)"

        if self.toolkit is None:
            return "Toolkit not initialized"

        tab_id = args[0]

        # Support both numeric index and tab ID format
        if tab_id.isdigit():
            # If it's a number, get tab info to find the actual tab ID
            try:
                tab_info = await self.toolkit.browser_get_tab_info()
                tabs = tab_info.get('tabs', [])
                tab_index = int(tab_id)

                # Find tab by index
                if 0 <= tab_index < len(tabs):
                    actual_tab_id = tabs[tab_index].get('tab_id')
                    if actual_tab_id:
                        tab_id = actual_tab_id
                    else:
                        return f"Tab at index {tab_index} has no tab_id"
                else:
                    return f"Invalid tab index {tab_index}. Available: 0-{len(tabs) - 1}"
            except Exception as e:
                return f"Failed to get tab info: {e}"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_close_tab(tab_id=tab_id)
            return f"Closed tab {tab_id}\nFull result: {result}"
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
                status = "🔥" if tab['is_current'] else "  "
                output += (
                    f"{status} [{tab['index']}] {tab['title'][:60]}\n"
                    f"      URL: {tab['url']}\n"
                )

            return output
        except Exception as e:
            return f"Get tab info failed: {e}"

    async def _cmd_scroll(self, args: List[str]) -> Any:
        """Handle scroll command."""
        if len(args) < 1:
            return "Usage: scroll <direction> [amount] (e.g., scroll down 3)"

        direction = args[0]
        if direction not in ['up', 'down', 'left', 'right']:
            return "Direction must be one of: up, down, left, right"

        amount = 3  # default scroll amount
        if len(args) > 1 and args[1].isdigit():
            amount = int(args[1])

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_scroll(
                direction=direction, amount=amount
            )
            return f"Scrolled {direction} by {amount} units\nFull result: {result}"
        except Exception as e:
            return f"Scroll failed: {e}"

    def _create_solve_handler(self):
        """Create a handler for solve_task command."""

        async def solve_handler(args: List[str]) -> Any:
            if not args:
                return "Usage: solve <task_description>"

            task = ' '.join(args)
            try:
                if self.toolkit is None:
                    return "Toolkit not initialized"

                # Check if solve_task is available
                if hasattr(self.toolkit, 'browser_solve_task'):
                    result = await self.toolkit.browser_solve_task(task=task)
                    return f"Task solved: {task}\nFull result: {result}"
                else:
                    return "solve_task is not available in current mode or requires web_agent_model"
            except Exception as e:
                return f"Solve task failed: {e}"

        return solve_handler

    async def _cmd_mouse_control(self, args: List[str]) -> Any:
        """Handle mouse_control command."""
        if len(args) < 3:
            return "Usage: mouse_control <control_type> <x> <y> (e.g., mouse_control click 100 200)"

        control_type = args[0]
        try:
            x = float(args[1])
            y = float(args[2])
        except ValueError:
            return "X and Y must be numeric values"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_mouse_control(
                control=control_type, x=x, y=y
            )
            return f"Mouse {control_type} at ({x}, {y})\nFull result: {result}"
        except Exception as e:
            return f"Mouse control failed: {e}"

    async def _cmd_mouse_drag(self, args: List[str]) -> Any:
        """Handle mouse_drag command."""
        if len(args) < 2:
            return "Usage: mouse_drag <from_ref> <to_ref> (e.g., mouse_drag e1 e5)"

        from_ref = args[0]
        to_ref = args[1]

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_mouse_drag(
                from_ref=from_ref, to_ref=to_ref
            )
            return (
                f"Dragged from {from_ref} to {to_ref}\nFull result: {result}"
            )
        except Exception as e:
            return f"Mouse drag failed: {e}"

    async def _cmd_press_key(self, args: List[str]) -> Any:
        """Handle press_key command."""
        if not args:
            return (
                "Usage: press_key <key1> [key2] ... (e.g., press_key Ctrl a)"
            )

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_press_key(keys=args)
            return f"Pressed keys: {' '.join(args)}\nFull result: {result}"
        except Exception as e:
            return f"Press key failed: {e}"

    async def _cmd_console_view(self, args: List[str]) -> Any:
        """Handle console_view command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_console_view()

            if isinstance(result, list):
                if not result:
                    return "No console logs"

                output = "Console logs:\n"
                for i, log in enumerate(result):
                    output += f"[{i}] {log.get('type', 'log')}: {log.get('text', '')}\n"
                return output
            else:
                return f"Console view result: {result}"
        except Exception as e:
            return f"Console view failed: {e}"

    async def _cmd_console_exec(self, args: List[str]) -> Any:
        """Handle console_exec command."""
        if not args:
            return "Usage: console_exec <javascript_code>"

        code = ' '.join(args)

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"
            result = await self.toolkit.browser_console_exec(code=code)
            return f"Executed: {code}\nResult: {result}"
        except Exception as e:
            return f"Console exec failed: {e}"

    async def _cmd_sheet_input(self, args: List[str]) -> Any:
        """Handle sheet_input command.

        Usage: sheet_input [--keyboard] <row1> <col1> <text1> [<row2> <col2> <text2> ...]

        Flags:
            --keyboard    Use fallback keyboard mode (slower, for debugging)

        Examples:
            sheet_input 0 0 "Name" 0 1 "Age"  (default: optimized batch JS)
            sheet_input 1 0 "Alice" 1 1 "30"
            sheet_input --keyboard 0 0 "Name" 0 1 "Age"  (fallback mode)

        Note: Default mode uses optimized batch JavaScript for maximum speed.
        """
        if len(args) < 3:
            return (
                "Usage: sheet_input <row1> <col1> <text1> [<row2> <col2> <text2> ...]\n"
                "Example: sheet_input 0 0 'Name' 0 1 'Age'\n"
                "Note: Each cell requires 3 arguments: row, col, text\n"
                "Uses optimized batch JS mode"
            )

        # Validate argument count (must be multiple of 3)
        if len(args) % 3 != 0:
            return (
                f"Invalid number of arguments: {len(args)}. "
                "Each cell requires exactly 3 arguments: row, col, text"
            )

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            # Parse cells from arguments
            cells = []
            for i in range(0, len(args), 3):
                try:
                    row = int(args[i])
                    col = int(args[i + 1])
                    text = args[i + 2]
                    cells.append({"row": row, "col": col, "text": text})
                except ValueError as e:
                    return (
                        f"Invalid cell at position {i//3 + 1}: "
                        f"row and col must be integers. Error: {e}"
                    )

            # Execute the sheet input
            print(f"\n{'='*60}")
            print("Executing sheet input in Batch JS mode...")
            print(f"{'='*60}\n")
            result = await self.toolkit.browser_sheet_input(cells=cells)  # type: ignore[union-attr]

            # Format output
            cell_summary = ", ".join(
                [f"({c['row']},{c['col']})='{c['text']}'" for c in cells]
            )
            return (
                f"\n{'='*60}\n"
                f"Sheet input completed (Batch JS mode)\n"
                f"Cells: {cell_summary}\n"
                f"{'='*60}\n"
                f"Full result: {result}"
            )

        except Exception as e:
            return f"Sheet input failed: {e}"

    async def _cmd_sheet_read(self, args: List[str]) -> Any:
        """Handle sheet_read command.

        Usage: sheet_read

        Reads all content from the spreadsheet by selecting all and copying.
        """
        if args:
            return "Usage: sheet_read (no arguments needed)"

        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            result = await self.toolkit.browser_sheet_read()  # type: ignore[union-attr]

            # Format output
            content = result.get("content", "")
            if len(content) > 500:
                content_preview = content[:500] + "..."
            else:
                content_preview = content

            return (
                f"Sheet read successful\n"
                f"Content length: {len(content)} characters\n"
                f"Content preview:\n{content_preview}\n"
                f"\nFull result: {result}"
            )

        except Exception as e:
            return f"Sheet read failed: {e}"

    async def _cmd_open(self, args: List[str]) -> Any:
        """Handle open browser command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            result = await self.toolkit.browser_open()
            return f"Browser opened\nFull result: {result}"
        except Exception as e:
            return f"Open browser failed: {e}"

    async def _cmd_close(self, args: List[str]) -> Any:
        """Handle close browser command."""
        try:
            if self.toolkit is None:
                return "Toolkit not initialized"

            result = await self.toolkit.browser_close()
            return f"Browser closed\nFull result: {result}"
        except Exception as e:
            return f"Close browser failed: {e}"

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
        "--mode",
        choices=["typescript", "python"],
        default="typescript",
        help="Browser toolkit mode: typescript or python (default: typescript)",
    )
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

    demo = BrowserDebugDemo(
        mode=args.mode, headless=args.headless, cache_dir=args.cache_dir
    )

    await demo.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except Exception as e:
        print(f"Program failed: {e}")
        sys.exit(1)
