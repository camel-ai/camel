# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Extension Proxy Wrapper for HybridBrowserToolkit.

This module provides a wrapper that communicates with a Chrome extension
to execute browser automation commands via Chrome's debugger API.
This allows browser automation without requiring the user to start Chrome
with special debugging flags.
"""

import asyncio
import datetime
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

try:
    import websockets
    from websockets.asyncio.server import ServerConnection, serve
except ImportError:
    websockets = None
    serve = None
    ServerConnection = None

from camel.logger import get_logger

# Import Playwright-compatible ARIA snapshot script
try:
    from camel.toolkits.hybrid_browser_toolkit.aria_snapshot_script import (
        get_full_init_and_snapshot_script,
        get_init_script,
        get_snapshot_only_script,
    )

    ARIA_SNAPSHOT_AVAILABLE = True
except ImportError:
    ARIA_SNAPSHOT_AVAILABLE = False
    get_init_script = None
    get_snapshot_only_script = None
    get_full_init_and_snapshot_script = None

logger = get_logger(__name__)


class ExtensionProxyWrapper:
    """
    A wrapper that communicates with a Chrome extension to execute
    browser automation commands.

    This wrapper acts as a WebSocket server that the Chrome extension
    connects to. It sends CDP commands to the extension, which executes
    them via chrome.debugger API.

    This allows HybridBrowserToolkit to control a normal Chrome browser
    (not started with --remote-debugging-port).
    """

    def __init__(
        self,
        config: Dict[str, Any],
        host: str = "localhost",
        port: int = 8765,
    ):
        """
        Initialize the Extension Proxy Wrapper.

        Args:
            config: Configuration dictionary (compatible with ws_wrapper config)
            host: Host to bind the WebSocket server
            port: Port to bind the WebSocket server
        """
        if websockets is None:
            raise ImportError(
                "websockets is required for ExtensionProxyWrapper. "
                "Install it with: pip install websockets"
            )

        self.config = config
        self.host = host
        self.port = port

        self._server = None
        self._client: Optional[ServerConnection] = None
        self._client_connected = asyncio.Event()
        self._browser_opened = False

        self._command_id = 0
        self._pending_commands: Dict[int, asyncio.Future] = {}

        self._current_url = ""
        self._current_title = ""

        # Track ARIA snapshot module initialization
        self._aria_module_initialized = False

        # Callbacks for external handling
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_task: Optional[Callable[[str, str], asyncio.Future]] = None
        self._task_queue: asyncio.Queue = asyncio.Queue()

        # Browser action logging support (compatible with ws_wrapper)
        self.browser_log_to_file = config.get("browser_log_to_file", False)
        self.session_id = config.get("session_id", "default")
        self.log_file_path: Optional[str] = None

        if self.browser_log_to_file:
            log_dir = config.get("log_dir", "browser_log")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = os.path.join(
                log_dir, f"browser_actions_{self.session_id}_{timestamp}.json"
            )
            logger.info(
                f"Browser action logging enabled: {self.log_file_path}"
            )

    def set_log_callback(self, callback: Callable[[str, str], None]):
        """Set callback for log messages. callback(level, message)"""
        self._on_log = callback

    def set_task_callback(
        self, callback: Callable[[str, str], asyncio.Future]
    ):
        """Set callback for task handling. callback(task, url) -> Future with result"""
        self._on_task = callback

    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next task from the queue. Returns None if no task."""
        try:
            return self._task_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def wait_for_task(
        self, timeout: float = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for a task from the extension."""
        try:
            if timeout:
                return await asyncio.wait_for(self._task_queue.get(), timeout)
            return await self._task_queue.get()
        except asyncio.TimeoutError:
            return None

    def _log(self, level: str, message: str):
        """Log a message and optionally call the callback."""
        if level == "info":
            logger.info(message)
        elif level == "error":
            logger.error(message)
        elif level == "debug":
            logger.debug(message)

        if self._on_log:
            self._on_log(level, message)

    async def _log_action(
        self,
        action_name: str,
        inputs: Dict[str, Any],
        outputs: Any,
        execution_time: float,
        page_load_time: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log action details with comprehensive information.

        Compatible with WebSocketBrowserWrapper's logging format.
        """
        if not self.browser_log_to_file or not self.log_file_path:
            return

        # Create log entry
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "action": action_name,
            "execution_time_ms": round(execution_time * 1000, 2),
            "inputs": inputs,
        }

        if error:
            log_entry["error"] = error
        else:
            # Handle different output types for JSON serialization
            if hasattr(outputs, 'text') and hasattr(outputs, 'images'):
                # This is a ToolResult object
                log_entry["outputs"] = {
                    "text": outputs.text,
                    "images_count": len(outputs.images)
                    if outputs.images
                    else 0,
                }
            elif isinstance(outputs, dict):
                # For dict outputs, include full content
                log_entry["outputs"] = outputs
            else:
                log_entry["outputs"] = str(outputs) if outputs else None

        if page_load_time is not None:
            log_entry["page_load_time_ms"] = round(page_load_time * 1000, 2)

        # Write to log file
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(
                    json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n'
                )
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")

    async def start(self):
        """Start the WebSocket server and wait for extension connection."""
        self._log(
            "info",
            f"Starting Extension Proxy server on ws://{self.host}:{self.port}",
        )

        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        )

        self._log(
            "info",
            "Extension Proxy server started. Waiting for Chrome extension to connect...",
        )

    async def wait_for_connection(self, timeout: float = 60.0):
        """Wait for the Chrome extension to connect."""
        try:
            await asyncio.wait_for(
                self._client_connected.wait(), timeout=timeout
            )
            self._log("info", "Chrome extension connected!")
            return True
        except asyncio.TimeoutError:
            self._log(
                "error", "Timeout waiting for Chrome extension to connect"
            )
            return False

    async def _handle_client(self, websocket: ServerConnection):
        """Handle incoming WebSocket connection from Chrome extension."""
        self._log("info", "Chrome extension connected")
        self._client = websocket
        self._client_connected.set()

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    self._log("error", f"Invalid JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            self._log("info", "Chrome extension disconnected")
        finally:
            self._client = None
            self._client_connected.clear()

    async def _handle_message(self, data: Dict[str, Any]):
        """Handle message from Chrome extension."""
        msg_type = data.get("type")

        if msg_type == "CDP_RESULT":
            cmd_id = data.get("id")
            if cmd_id in self._pending_commands:
                self._pending_commands[cmd_id].set_result(
                    data.get("result", {})
                )

        elif msg_type == "CDP_ERROR":
            cmd_id = data.get("id")
            if cmd_id in self._pending_commands:
                self._pending_commands[cmd_id].set_exception(
                    Exception(data.get("error", "Unknown error"))
                )

        elif msg_type == "CDP_EVENT":
            method = data.get("method")
            params = data.get("params", {})

            if method == "Page.frameNavigated":
                frame = params.get("frame", {})
                if not frame.get("parentId"):
                    self._current_url = frame.get("url", "")
                    self._log(
                        "debug", f"Page navigated to: {self._current_url}"
                    )

        elif msg_type == "START_TASK":
            # Task received from extension - add to queue
            task_data = {
                "task": data.get("task", ""),
                "url": data.get("url", ""),
                "tabId": data.get("tabId", 0),
            }
            await self._task_queue.put(task_data)
            self._log("info", f"Task received: {task_data['task']}")

        elif msg_type == "CLEAR_CONTEXT":
            # Signal to clear agent context
            task_data = {
                "type": "CLEAR_CONTEXT",
            }
            await self._task_queue.put(task_data)
            self._log("info", "Context clear requested")

        elif msg_type == "DEBUG_COMMAND":
            # Debug command from extension - add to queue
            task_data = {
                "type": "DEBUG_COMMAND",
                "command": data.get("command", ""),
                "url": data.get("url", ""),
                "tabId": data.get("tabId", 0),
            }
            await self._task_queue.put(task_data)
            self._log(
                "info", f"Debug command received: {task_data['command']}"
            )

        elif msg_type == "ATTACH_RESULT":
            # Result of attach request
            if hasattr(self, '_attach_future') and self._attach_future:
                if data.get("success"):
                    self._attach_future.set_result(
                        {
                            "success": True,
                            "tabId": data.get("tabId"),
                            "url": data.get("url"),
                        }
                    )
                else:
                    self._attach_future.set_result(
                        {
                            "success": False,
                            "error": data.get("error", "Unknown error"),
                        }
                    )

    async def request_attach(self, timeout: float = 10.0) -> Dict[str, Any]:
        """Request the extension to attach debugger to current tab.

        Returns:
            Dict with 'success', and optionally 'tabId', 'url', or 'error'
        """
        if not self._client:
            return {"success": False, "error": "Extension not connected"}

        self._attach_future = asyncio.get_event_loop().create_future()

        await self._client.send(json.dumps({"type": "REQUEST_ATTACH"}))

        try:
            result = await asyncio.wait_for(
                self._attach_future, timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout waiting for attach"}
        finally:
            self._attach_future = None

    async def _send_command(self, method: str, params: Dict = None) -> Any:
        """Send a CDP command through the extension."""
        if not self._client:
            raise RuntimeError("Chrome extension not connected")

        self._command_id += 1
        cmd_id = self._command_id

        future = asyncio.get_event_loop().create_future()
        self._pending_commands[cmd_id] = future

        await self._client.send(
            json.dumps(
                {
                    "type": "CDP_COMMAND",
                    "id": cmd_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )

        self._log("debug", f"Sent CDP command: {method}")

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            del self._pending_commands[cmd_id]
            raise TimeoutError(f"CDP command timed out: {method}")
        finally:
            if cmd_id in self._pending_commands:
                del self._pending_commands[cmd_id]

    async def _send_log(self, level: str, message: str):
        """Send log message to the extension."""
        if self._client:
            await self._client.send(
                json.dumps({"type": "LOG", "level": level, "message": message})
            )

    async def _send_action(self, action: str, detail: str = ""):
        """Send action notification to the extension."""
        if self._client:
            await self._client.send(
                json.dumps(
                    {"type": "ACTION", "action": action, "detail": detail}
                )
            )

    async def send_task_complete(self, result: str = ""):
        """Send task completion notification to the extension."""
        if self._client:
            await self._client.send(
                json.dumps({"type": "TASK_COMPLETE", "result": result})
            )

    async def send_task_error(self, error: str):
        """Send task error notification to the extension."""
        if self._client:
            await self._client.send(
                json.dumps({"type": "TASK_ERROR", "error": error})
            )

    async def send_stream_start(self):
        """Signal start of streaming response."""
        if self._client:
            await self._client.send(json.dumps({"type": "STREAM_START"}))

    async def send_stream_text(self, text: str):
        """Send streaming text chunk to the extension."""
        if self._client:
            await self._client.send(
                json.dumps({"type": "STREAM_TEXT", "text": text})
            )

    async def send_stream_end(self):
        """Signal end of streaming response."""
        if self._client:
            await self._client.send(json.dumps({"type": "STREAM_END"}))

    async def highlight_element(self, selector: str, duration: int = 400):
        """Highlight an element on the page before interacting with it.

        Args:
            selector: The element selector (ref like 'e1' or CSS selector)
            duration: How long to show the highlight in milliseconds
        """
        if self._client:
            await self._client.send(
                json.dumps(
                    {
                        "type": "HIGHLIGHT",
                        "selector": selector,
                        "duration": duration,
                    }
                )
            )
            # Brief wait for highlight to be visible
            await asyncio.sleep(0.1)
            logger.info("HIGHLIGHT sent, waited 0.5s")

    # ==================== Browser Control Methods ====================
    # These methods implement the same interface as WebSocketBrowserWrapper

    async def open_browser(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Open browser / initialize session."""
        self._browser_opened = True
        await self._send_log("info", "Browser session initialized")

        # Get current page info
        snapshot = await self.get_page_snapshot()

        return {
            "result": "Browser session initialized via Chrome extension",
            "snapshot": snapshot,
        }

    async def close_browser(self) -> Dict[str, Any]:
        """Close browser session."""
        self._browser_opened = False
        await self._send_log("info", "Browser session closed")

        # Send close notification
        if self._client:
            await self._client.send(json.dumps({"type": "DETACH"}))

        return {"result": "Browser session closed"}

    async def visit_page(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        start_time = time.time()
        await self._send_action("Navigating", url)

        try:
            await self._send_command("Page.navigate", {"url": url})
            await asyncio.sleep(2)  # Wait for navigation

            self._current_url = url
            # Reset ARIA module after navigation
            self._aria_module_initialized = False
            snapshot = await self.get_page_snapshot()

            result = {
                "result": f"Navigated to {url}",
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="visit_page",
                inputs={"url": url},
                outputs=result,
                execution_time=time.time() - start_time,
            )

            return result
        except Exception as e:
            await self._log_action(
                action_name="visit_page",
                inputs={"url": url},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def _init_aria_module(self) -> bool:
        """Initialize the Playwright ARIA snapshot module in the page."""
        if not ARIA_SNAPSHOT_AVAILABLE:
            logger.warning(
                "ARIA snapshot module not available, using fallback"
            )
            return False

        try:
            init_script = get_init_script()
            await self._send_command(
                "Runtime.evaluate",
                {"expression": init_script, "returnByValue": True},
            )
            self._aria_module_initialized = True
            logger.info("ARIA snapshot module initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ARIA module: {e}")
            return False

    async def get_page_snapshot(self, viewport_limit: bool = False) -> str:
        """Get a text snapshot of the current page using Playwright's _snapshotForAI format.

        This uses the same ARIA snapshot implementation as Playwright,
        providing a consistent AI-friendly representation of the page.
        """
        try:
            # Get page title
            title_result = await self._send_command(
                "Runtime.evaluate",
                {"expression": "document.title", "returnByValue": True},
            )
            self._current_title = title_result.get("result", {}).get(
                "value", ""
            )

            # Get page URL
            url_result = await self._send_command(
                "Runtime.evaluate",
                {"expression": "window.location.href", "returnByValue": True},
            )
            self._current_url = url_result.get("result", {}).get("value", "")

            # Use Playwright's ARIA snapshot if available
            if ARIA_SNAPSHOT_AVAILABLE:
                # Initialize module if not already done
                if not self._aria_module_initialized:
                    await self._init_aria_module()

                # Get ARIA snapshot
                snapshot_script = get_snapshot_only_script()
                result = await self._send_command(
                    "Runtime.evaluate",
                    {"expression": snapshot_script, "returnByValue": True},
                )

                aria_snapshot = result.get("result", {}).get("value", "")

                if aria_snapshot and not aria_snapshot.startswith("Error:"):
                    snapshot = f"Page: {self._current_title}\nURL: {self._current_url}\n\nAccessibility Tree:\n{aria_snapshot}"
                    return snapshot
                else:
                    # Module might need re-initialization after navigation
                    logger.info("Re-initializing ARIA module after navigation")
                    self._aria_module_initialized = False
                    await self._init_aria_module()

                    result = await self._send_command(
                        "Runtime.evaluate",
                        {"expression": snapshot_script, "returnByValue": True},
                    )
                    aria_snapshot = result.get("result", {}).get("value", "")

                    if aria_snapshot and not aria_snapshot.startswith(
                        "Error:"
                    ):
                        snapshot = f"Page: {self._current_title}\nURL: {self._current_url}\n\nAccessibility Tree:\n{aria_snapshot}"
                        return snapshot

            # Fallback to simple snapshot if ARIA module fails
            return await self._get_simple_snapshot()

        except Exception as e:
            logger.error(f"Error getting page snapshot: {e}")
            return f"Error getting snapshot: {e}"

    async def _get_simple_snapshot(self) -> str:
        """Fallback simple snapshot when ARIA module is not available."""
        elements_js = """
        (function() {
            const interactiveSelectors = [
                'a[href]', 'button', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[onclick]',
                '[tabindex]:not([tabindex="-1"])'
            ];

            const elements = document.querySelectorAll(interactiveSelectors.join(','));
            const results = [];
            let refIndex = 1;

            elements.forEach(el => {
                const rect = el.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                 window.getComputedStyle(el).visibility !== 'hidden' &&
                                 window.getComputedStyle(el).display !== 'none';

                if (isVisible) {
                    const tag = el.tagName.toLowerCase();
                    const text = (el.textContent || el.value || el.placeholder || '').trim();
                    const type = el.type || '';
                    const href = el.href || '';
                    const role = el.getAttribute('role') || '';
                    const ariaLabel = el.getAttribute('aria-label') || '';

                    let description = `[ref=e${refIndex}] <${tag}`;
                    if (type) description += ` type="${type}"`;
                    if (role) description += ` role="${role}"`;
                    if (ariaLabel) description += ` aria-label="${ariaLabel}"`;
                    description += `>`;
                    if (text) description += ` "${text}"`;
                    if (href && tag === 'a') description += ` -> ${href}`;

                    results.push(description);
                    refIndex++;
                }
            });

            return results.join('\\n');
        })()
        """

        result = await self._send_command(
            "Runtime.evaluate",
            {"expression": elements_js, "returnByValue": True},
        )

        elements_text = result.get("result", {}).get("value", "")
        return f"Page: {self._current_title}\nURL: {self._current_url}\n\nInteractive Elements:\n{elements_text}"

    async def click(self, ref: str) -> Dict[str, Any]:
        """Click an element by reference.

        The ref should be in the format used by the ARIA snapshot (e.g., 'e1', 'e2', etc.)
        """
        start_time = time.time()
        await self._send_action("Click", f"ref={ref}")

        try:
            # Highlight the element before clicking
            await self.highlight_element(ref)
            # Use ARIA module's clickByRef if available
            if ARIA_SNAPSHOT_AVAILABLE and self._aria_module_initialized:
                click_js = f"""
                (function() {{
                    if (typeof __ariaSnapshot !== 'undefined') {{
                        const success = __ariaSnapshot.clickByRef('{ref}', document.body);
                        if (success) {{
                            return 'Clicked element with ref={ref}';
                        }}
                    }}
                    return 'Element not found: ref={ref}';
                }})()
                """
            else:
                # Fallback - try __ariaSnapshot.getElementByRef first (which calls snapshotForAI for fresh refs)
                click_js = f"""
                (function() {{
                    // Try Playwright's getElementByRef first (calls snapshotForAI for fresh refs)
                    if (typeof __ariaSnapshot !== 'undefined' && __ariaSnapshot.getElementByRef) {{
                        const element = __ariaSnapshot.getElementByRef('{ref}', document.body);
                        if (element && element instanceof HTMLElement) {{
                            element.click();
                            return 'Clicked: ' + (element.textContent || element.tagName).substring(0, 100);
                        }}
                    }}
                    // Fallback to walking DOM
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        null,
                        false
                    );

                    let node;
                    while (node = walker.nextNode()) {{
                        if (node._ariaRef && node._ariaRef.ref === '{ref}') {{
                            node.click();
                            return 'Clicked: ' + (node.textContent || node.tagName).substring(0, 100);
                        }}
                    }}
                    return 'Element not found: ref={ref}';
                }})()
                """

            result = await self._send_command(
                "Runtime.evaluate",
                {"expression": click_js, "returnByValue": True},
            )

            result_text = result.get("result", {}).get("value", "Unknown")
            await asyncio.sleep(0.5)  # Wait for any navigation/updates

            # Reset ARIA module flag since page content may have changed
            self._aria_module_initialized = False

            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": result_text,
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="click",
                inputs={"ref": ref},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="click",
                inputs={"ref": ref},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def type(self, ref: str, text: str) -> Dict[str, Any]:
        """Type text into an element using Playwright-equivalent strategy.

        This implements the full Playwright performType strategy:
        1. Locate element by aria-ref
        2. Get element info (placeholder, readonly, type, role, etc.)
        3. Record snapshot before action for diff detection
        4. Strategy 1: Direct fill
        5. Strategy 2: Click then fill
        6. Strategy 3: Find input child elements
        7. Strategy 4: Find newly appeared input with same placeholder
        8. Return diff snapshot for combobox/textbox elements

        The ref should be in the format used by the ARIA snapshot (e.g., 'e1', 'e2', etc.)
        """
        start_time = time.time()
        await self._send_action("Type", f'ref={ref}, text="{text}"')

        try:
            # Highlight the element before typing
            await self.highlight_element(ref)
            # Escape special characters in text for JavaScript
            escaped_text = (
                text.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
            )

            # Ensure ARIA module is initialized
            if ARIA_SNAPSHOT_AVAILABLE and not self._aria_module_initialized:
                await self._init_aria_module()

            # Get snapshot before action to track existing refs
            snapshot_before = await self.get_page_snapshot()

            # Step 1: Locate element and get its info (using Playwright's getElementByRef which calls snapshotForAI first)
            element_info_js = f"""
            (function() {{
                // Use Playwright's getElementByRef - it calls snapshotForAI() first to get fresh refs
                function findElementByRef(ref) {{
                    if (typeof __ariaSnapshot !== 'undefined' && __ariaSnapshot.getElementByRef) {{
                        return __ariaSnapshot.getElementByRef(ref, document.body);
                    }}
                    // Fallback to walking DOM if __ariaSnapshot not available
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        null,
                        false
                    );
                    let node;
                    while (node = walker.nextNode()) {{
                        if (node._ariaRef && node._ariaRef.ref === ref) {{
                            return node;
                        }}
                    }}
                    return null;
                }}

                const element = findElementByRef('{ref}');
                if (!element) {{
                    return JSON.stringify({{ found: false, error: 'Element not found' }});
                }}

                // Get element info
                const info = {{
                    found: true,
                    tagName: element.tagName.toLowerCase(),
                    type: element.type || null,
                    placeholder: element.placeholder || null,
                    readonly: element.readOnly || element.hasAttribute('readonly'),
                    disabled: element.disabled || false,
                    role: element.getAttribute('role'),
                    ariaHaspopup: element.getAttribute('aria-haspopup'),
                    // Check both direct and inherited contentEditable
                    contentEditable: element.contentEditable === 'true' || element.isContentEditable,
                    isVisible: element.offsetParent !== null ||
                               window.getComputedStyle(element).display !== 'none'
                }};

                // Determine element type flags
                info.isCombobox = info.role === 'combobox' ||
                                  info.tagName === 'combobox' ||
                                  info.ariaHaspopup === 'listbox';
                info.isTextbox = info.role === 'textbox' ||
                                 info.tagName === 'input' ||
                                 info.tagName === 'textarea' ||
                                 info.contentEditable === true;
                info.isSpecialInput = ['date', 'datetime-local', 'time'].includes(info.type);
                info.shouldCheckDiff = info.isCombobox || info.isTextbox;

                return JSON.stringify(info);
            }})()
            """

            result = await self._send_command(
                "Runtime.evaluate",
                {"expression": element_info_js, "returnByValue": True},
            )
            element_info = json.loads(
                result.get("result", {}).get("value", "{}")
            )

            # If element not found by ref, try fallback strategies
            if not element_info.get("found"):
                logger.info(
                    f"[Type] Element ref={ref} not found, trying fallback strategies"
                )

                # Strategy: Check if ref looks like a CSS selector
                is_css_selector = any(
                    c in ref for c in ['[', '.', '#', '>', ' ', ':']
                )

                # Strategy: Try CSS selector or contenteditable fallback
                fallback_result = await self._type_fallback_strategies(
                    ref, escaped_text, is_css_selector
                )
                if fallback_result.get("success"):
                    snapshot_after = await self.get_page_snapshot()
                    return {
                        "result": fallback_result.get(
                            "message", "Typed successfully via fallback"
                        ),
                        "snapshot": snapshot_after,
                    }

                # All strategies failed
                return {
                    "result": f"Error: Element not found and fallback strategies failed for ref={ref}",
                    "snapshot": snapshot_before,
                }

            logger.info(f"[Type] Element info for ref={ref}: {element_info}")

            # Step 2: Handle readonly or special date/time inputs
            if element_info.get("readonly") or element_info.get(
                "isSpecialInput"
            ):
                logger.info(
                    "[Type] Element is readonly or special input, clicking to trigger dynamic content"
                )
                click_result = await self._type_click_element(ref)
                await asyncio.sleep(0.5)

                # Look for new input elements with matching placeholder
                if element_info.get("placeholder"):
                    fill_result = await self._type_find_and_fill_new_input(
                        ref,
                        escaped_text,
                        element_info.get("placeholder"),
                        snapshot_before,
                    )
                    if fill_result.get("success"):
                        snapshot_after = await self.get_page_snapshot()
                        diff_snapshot = (
                            self._get_snapshot_diff(
                                snapshot_before, snapshot_after
                            )
                            if element_info.get("shouldCheckDiff")
                            else None
                        )
                        return {
                            "result": fill_result.get(
                                "message", "Typed successfully"
                            ),
                            "snapshot": snapshot_after,
                            **(
                                {"diffSnapshot": diff_snapshot}
                                if diff_snapshot
                                else {}
                            ),
                        }

                snapshot_after = await self.get_page_snapshot()
                return {
                    "result": f"Clicked readonly element ref={ref}, no suitable input found",
                    "snapshot": snapshot_after,
                }

            # Step 3: Try filling strategies
            fill_result = await self._type_fill_element(
                ref, escaped_text, element_info, snapshot_before
            )

            snapshot_after = await self.get_page_snapshot()

            # Check for diff if needed
            diff_snapshot = None
            if element_info.get("shouldCheckDiff"):
                diff_snapshot = self._get_snapshot_diff(
                    snapshot_before, snapshot_after
                )

            action_result = {
                "result": fill_result.get("message", "Type completed"),
                "snapshot": snapshot_after,
            }
            if diff_snapshot:
                action_result["diffSnapshot"] = diff_snapshot

            await self._log_action(
                action_name="type",
                inputs={"ref": ref, "text": text},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result

        except Exception as e:
            logger.error(f"[Type] Error: {e}")
            await self._log_action(
                action_name="type",
                inputs={"ref": ref, "text": text},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def _type_click_element(self, ref: str) -> Dict[str, Any]:
        """Click element by ref (helper for type operation)."""
        click_js = f"""
        (function() {{
            // Use Playwright's getElementByRef - calls snapshotForAI() first for fresh refs
            function findElementByRef(ref) {{
                if (typeof __ariaSnapshot !== 'undefined' && __ariaSnapshot.getElementByRef) {{
                    return __ariaSnapshot.getElementByRef(ref, document.body);
                }}
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_ELEMENT, null, false
                );
                let node;
                while (node = walker.nextNode()) {{
                    if (node._ariaRef && node._ariaRef.ref === ref) return node;
                }}
                return null;
            }}
            const element = findElementByRef('{ref}');
            if (element) {{
                element.click();
                return JSON.stringify({{ success: true }});
            }}
            return JSON.stringify({{ success: false, error: 'Element not found' }});
        }})()
        """
        result = await self._send_command(
            "Runtime.evaluate", {"expression": click_js, "returnByValue": True}
        )
        return json.loads(result.get("result", {}).get("value", "{}"))

    async def _type_fill_element(
        self,
        ref: str,
        escaped_text: str,
        element_info: Dict[str, Any],
        snapshot_before: str,
    ) -> Dict[str, Any]:
        """
        Fill element using Playwright-equivalent multi-strategy approach.

        Strategy 1: Direct fill (focus + clear + set value + events)
        Strategy 2: Click then fill
        Strategy 3: Find input child elements within the target
        Strategy 4: Find newly appeared input with same placeholder
        """

        # Strategy 1: Direct fill
        fill_js = self._get_fill_script(ref, escaped_text, click_first=False)
        result = await self._send_command(
            "Runtime.evaluate", {"expression": fill_js, "returnByValue": True}
        )
        fill_result = json.loads(result.get("result", {}).get("value", "{}"))

        if fill_result.get("success"):
            logger.info(
                f"[Type] Strategy 1 (direct fill) succeeded for ref={ref}"
            )
            return {
                "success": True,
                "message": f"Typed into element ref={ref}",
            }

        logger.info(
            f"[Type] Strategy 1 failed: {fill_result.get('error')}, trying Strategy 2"
        )

        # Strategy 2: Click then fill
        fill_js = self._get_fill_script(ref, escaped_text, click_first=True)
        result = await self._send_command(
            "Runtime.evaluate", {"expression": fill_js, "returnByValue": True}
        )
        fill_result = json.loads(result.get("result", {}).get("value", "{}"))

        if fill_result.get("success"):
            logger.info(
                f"[Type] Strategy 2 (click then fill) succeeded for ref={ref}"
            )
            return {
                "success": True,
                "message": f"Typed into element ref={ref} after clicking",
            }

        logger.info(
            f"[Type] Strategy 2 failed: {fill_result.get('error')}, trying Strategy 3"
        )

        # Strategy 3: Find input child elements
        child_fill_js = f"""
        (function() {{
            // Use Playwright's getElementByRef - calls snapshotForAI() first for fresh refs
            function findElementByRef(ref) {{
                if (typeof __ariaSnapshot !== 'undefined' && __ariaSnapshot.getElementByRef) {{
                    return __ariaSnapshot.getElementByRef(ref, document.body);
                }}
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_ELEMENT, null, false
                );
                let node;
                while (node = walker.nextNode()) {{
                    if (node._ariaRef && node._ariaRef.ref === ref) return node;
                }}
                return null;
            }}

            function fillElement(el, text) {{
                el.focus();
                if (el.select) el.select();
                else if (el.setSelectionRange) {{
                    el.setSelectionRange(0, el.value ? el.value.length : 0);
                }}

                // Clear and set value
                if ('value' in el) {{
                    el.value = text;
                }} else if (el.contentEditable === 'true' || el.isContentEditable) {{
                    el.textContent = text;
                }}

                // Fire events
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}

            const parent = findElementByRef('{ref}');
            if (!parent) {{
                return JSON.stringify({{ success: false, error: 'Parent element not found' }});
            }}

            // Click parent first to potentially reveal inputs
            parent.click();

            // Look for input children
            const selectors = [
                'input:not([type="hidden"])',
                'textarea',
                '[contenteditable="true"]',
                '[role="textbox"]'
            ];

            for (const selector of selectors) {{
                const child = parent.querySelector(selector);
                if (child && child.offsetParent !== null) {{
                    try {{
                        fillElement(child, '{escaped_text}');
                        return JSON.stringify({{
                            success: true,
                            message: 'Filled child ' + child.tagName
                        }});
                    }} catch (e) {{
                        // Continue to next selector
                    }}
                }}
            }}

            return JSON.stringify({{ success: false, error: 'No fillable child element found' }});
        }})()
        """

        result = await self._send_command(
            "Runtime.evaluate",
            {"expression": child_fill_js, "returnByValue": True},
        )
        fill_result = json.loads(result.get("result", {}).get("value", "{}"))

        if fill_result.get("success"):
            logger.info(
                f"[Type] Strategy 3 (child input) succeeded for ref={ref}"
            )
            return {
                "success": True,
                "message": fill_result.get(
                    "message", "Typed into child element"
                ),
            }

        logger.info(
            f"[Type] Strategy 3 failed: {fill_result.get('error')}, trying Strategy 4"
        )

        # Strategy 4: Find new input with matching placeholder
        await asyncio.sleep(0.3)  # Wait for dynamic content

        placeholder = element_info.get("placeholder")
        if placeholder:
            new_input_result = await self._type_find_and_fill_new_input(
                ref, escaped_text, placeholder, snapshot_before
            )
            if new_input_result.get("success"):
                logger.info(
                    "[Type] Strategy 4 (new input with placeholder) succeeded"
                )
                return new_input_result

        logger.info(f"[Type] All strategies failed for ref={ref}")
        return {
            "success": False,
            "message": f"Could not type into element ref={ref}",
        }

    def _get_fill_script(
        self, ref: str, escaped_text: str, click_first: bool = False
    ) -> str:
        """Generate JavaScript to fill an element (simulating Playwright's fill)."""
        click_code = "element.click();" if click_first else ""

        return f"""
        (function() {{
            // Use Playwright's getElementByRef - calls snapshotForAI() first for fresh refs
            function findElementByRef(ref) {{
                if (typeof __ariaSnapshot !== 'undefined' && __ariaSnapshot.getElementByRef) {{
                    return __ariaSnapshot.getElementByRef(ref, document.body);
                }}
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_ELEMENT, null, false
                );
                let node;
                while (node = walker.nextNode()) {{
                    if (node._ariaRef && node._ariaRef.ref === ref) return node;
                }}
                return null;
            }}

            const element = findElementByRef('{ref}');
            if (!element) {{
                return JSON.stringify({{ success: false, error: 'Element not found' }});
            }}

            try {{
                {click_code}

                // Focus the element
                element.focus();

                // Check if element is fillable
                const isInput = element instanceof HTMLInputElement;
                const isTextarea = element instanceof HTMLTextAreaElement;
                // Check both direct and inherited contentEditable
                const isContentEditable = element.contentEditable === 'true' || element.isContentEditable;
                const hasValueProperty = 'value' in element;

                if (!isInput && !isTextarea && !isContentEditable && !hasValueProperty) {{
                    return JSON.stringify({{
                        success: false,
                        error: 'Element is not fillable (not input/textarea/contenteditable)'
                    }});
                }}

                // Select all existing content
                if (element.select) {{
                    element.select();
                }} else if (element.setSelectionRange && element.value !== undefined) {{
                    element.setSelectionRange(0, element.value.length);
                }} else if (isContentEditable) {{
                    const range = document.createRange();
                    range.selectNodeContents(element);
                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                }}

                // Set the value
                if (isInput || isTextarea || hasValueProperty) {{
                    // For input/textarea, use value property
                    element.value = '{escaped_text}';
                }} else if (isContentEditable) {{
                    // For contenteditable, use textContent
                    element.textContent = '{escaped_text}';
                }}

                // Dispatch input event
                element.dispatchEvent(new InputEvent('input', {{
                    bubbles: true,
                    cancelable: true,
                    inputType: 'insertText',
                    data: '{escaped_text}'
                }}));

                // Dispatch change event
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));

                // For React and other frameworks, also try dispatching on native setter
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                )?.set;
                const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value'
                )?.set;

                if (isInput && nativeInputValueSetter) {{
                    nativeInputValueSetter.call(element, '{escaped_text}');
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else if (isTextarea && nativeTextAreaValueSetter) {{
                    nativeTextAreaValueSetter.call(element, '{escaped_text}');
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}

                return JSON.stringify({{ success: true }});
            }} catch (e) {{
                return JSON.stringify({{ success: false, error: e.message }});
            }}
        }})()
        """

    async def _type_find_and_fill_new_input(
        self,
        original_ref: str,
        escaped_text: str,
        placeholder: str,
        snapshot_before: str,
    ) -> Dict[str, Any]:
        """Find newly appeared input elements with matching placeholder and fill them."""

        # Escape placeholder for JS
        escaped_placeholder = placeholder.replace("\\", "\\\\").replace(
            "'", "\\'"
        )

        find_and_fill_js = f"""
        (function() {{
            // Find all input/textarea elements
            const inputs = document.querySelectorAll('input, textarea');

            for (const input of inputs) {{
                // Check if it has matching placeholder
                if (input.placeholder === '{escaped_placeholder}') {{
                    // Check if visible
                    if (input.offsetParent === null &&
                        window.getComputedStyle(input).display === 'none') {{
                        continue;
                    }}

                    try {{
                        input.focus();
                        if (input.select) input.select();
                        input.value = '{escaped_text}';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));

                        return JSON.stringify({{
                            success: true,
                            message: 'Filled new input with matching placeholder'
                        }});
                    }} catch (e) {{
                        continue;
                    }}
                }}
            }}

            return JSON.stringify({{ success: false, error: 'No matching input found' }});
        }})()
        """

        result = await self._send_command(
            "Runtime.evaluate",
            {"expression": find_and_fill_js, "returnByValue": True},
        )
        return json.loads(result.get("result", {}).get("value", "{}"))

    async def _type_fallback_strategies(
        self, ref: str, escaped_text: str, is_css_selector: bool
    ) -> Dict[str, Any]:
        """
        Fallback strategies when element is not found by ARIA ref.

        This handles cases like:
        1. ref is actually a CSS selector (e.g., "[contenteditable]", ".my-input")
        2. Element is a contenteditable that wasn't captured in ARIA snapshot

        Args:
            ref: The ref or selector string
            escaped_text: Text to type (already escaped for JS)
            is_css_selector: Whether ref looks like a CSS selector

        Returns:
            Dict with 'success' and 'message' keys
        """

        # Strategy 1: If ref looks like a CSS selector, use it directly
        if is_css_selector:
            logger.info(f"[Type Fallback] Trying CSS selector: {ref}")
            escaped_selector = (
                ref.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace('"', '\\"')
            )

            fill_by_selector_js = f"""
            (function() {{
                const el = document.querySelector("{escaped_selector}");
                if (!el) {{
                    return JSON.stringify({{ success: false, error: 'Element not found by selector' }});
                }}

                try {{
                    el.focus();

                    // Handle contenteditable
                    if (el.contentEditable === 'true') {{
                        // Select all content first
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);

                        // Set content
                        el.innerHTML = '{escaped_text}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return JSON.stringify({{ success: true, message: 'Filled contenteditable via CSS selector' }});
                    }}

                    // Handle input/textarea
                    if ('value' in el) {{
                        if (el.select) el.select();
                        el.value = '{escaped_text}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return JSON.stringify({{ success: true, message: 'Filled input via CSS selector' }});
                    }}

                    return JSON.stringify({{ success: false, error: 'Element not fillable' }});
                }} catch (e) {{
                    return JSON.stringify({{ success: false, error: e.message }});
                }}
            }})()
            """

            result = await self._send_command(
                "Runtime.evaluate",
                {"expression": fill_by_selector_js, "returnByValue": True},
            )
            fill_result = json.loads(
                result.get("result", {}).get("value", "{}")
            )

            if fill_result.get("success"):
                return fill_result

        # Strategy 2: Try to find any visible contenteditable element
        logger.info(
            "[Type Fallback] Trying to find visible contenteditable element"
        )

        find_contenteditable_js = f"""
        (function() {{
            // Find all contenteditable elements
            const editables = document.querySelectorAll('[contenteditable="true"]');

            for (const el of editables) {{
                // Check if visible
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                  style.display !== 'none' &&
                                  style.visibility !== 'hidden';

                if (isVisible) {{
                    try {{
                        el.focus();

                        // Select all content
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);

                        // Set content
                        el.innerHTML = '{escaped_text}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));

                        return JSON.stringify({{
                            success: true,
                            message: 'Filled first visible contenteditable element'
                        }});
                    }} catch (e) {{
                        continue;
                    }}
                }}
            }}

            return JSON.stringify({{ success: false, error: 'No visible contenteditable found' }});
        }})()
        """

        result = await self._send_command(
            "Runtime.evaluate",
            {"expression": find_contenteditable_js, "returnByValue": True},
        )
        fill_result = json.loads(result.get("result", {}).get("value", "{}"))

        if fill_result.get("success"):
            return fill_result

        # Strategy 3: Try to find input/textarea that's currently focused or active
        logger.info(
            "[Type Fallback] Trying to find focused/active input element"
        )

        find_active_input_js = f"""
        (function() {{
            // Check active element first
            const active = document.activeElement;
            if (active && (active instanceof HTMLInputElement ||
                           active instanceof HTMLTextAreaElement ||
                           active.contentEditable === 'true')) {{
                try {{
                    if ('value' in active) {{
                        active.value = '{escaped_text}';
                    }} else if (active.contentEditable === 'true') {{
                        active.innerHTML = '{escaped_text}';
                    }}
                    active.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    active.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return JSON.stringify({{
                        success: true,
                        message: 'Filled currently active element'
                    }});
                }} catch (e) {{
                    // Continue to next strategy
                }}
            }}

            return JSON.stringify({{ success: false, error: 'No suitable active element' }});
        }})()
        """

        result = await self._send_command(
            "Runtime.evaluate",
            {"expression": find_active_input_js, "returnByValue": True},
        )
        fill_result = json.loads(result.get("result", {}).get("value", "{}"))

        return fill_result

    def _get_snapshot_diff(
        self, snapshot_before: str, snapshot_after: str
    ) -> Optional[str]:
        """
        Extract diff between two snapshots, returning only new option/menuitem elements.
        This mimics Playwright's getSnapshotDiff for combobox/autocomplete handling.
        """
        import re

        # Extract refs from before snapshot
        refs_before = set(re.findall(r'\[ref=([^\]]+)\]', snapshot_before))

        # Find new elements in after snapshot
        new_elements = []
        for line in snapshot_after.split('\n'):
            ref_match = re.search(r'\[ref=([^\]]+)\]', line)
            if ref_match and ref_match.group(1) not in refs_before:
                # Check if it's an option or menuitem
                line_lower = line.lower()
                if 'option' in line_lower or 'menuitem' in line_lower:
                    new_elements.append(line.strip())

        if new_elements:
            return '\n'.join(new_elements)
        return None

    async def scroll(
        self, direction: str, amount: int = 500
    ) -> Dict[str, Any]:
        """Scroll the page."""
        start_time = time.time()
        await self._send_action("Scroll", f"{direction} by {amount}px")

        try:
            scroll_map = {
                "down": (0, amount),
                "up": (0, -amount),
                "right": (amount, 0),
                "left": (-amount, 0),
            }
            dx, dy = scroll_map.get(direction, (0, amount))

            await self._send_command(
                "Runtime.evaluate",
                {
                    "expression": f"window.scrollBy({dx}, {dy})",
                    "returnByValue": True,
                },
            )

            await asyncio.sleep(0.3)
            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": f"Scrolled {direction} by {amount}px",
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="scroll",
                inputs={"direction": direction, "amount": amount},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="scroll",
                inputs={"direction": direction, "amount": amount},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press a keyboard key."""
        start_time = time.time()
        await self._send_action("Press Key", key)

        try:
            key_codes = {
                "Enter": 13,
                "Tab": 9,
                "Escape": 27,
                "Backspace": 8,
                "ArrowUp": 38,
                "ArrowDown": 40,
                "ArrowLeft": 37,
                "ArrowRight": 39,
                "Space": 32,
            }

            key_code = key_codes.get(key, ord(key[0]) if key else 0)

            await self._send_command(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "key": key,
                    "code": f"Key{key}" if len(key) == 1 else key,
                    "windowsVirtualKeyCode": key_code,
                },
            )
            await self._send_command(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyUp",
                    "key": key,
                    "code": f"Key{key}" if len(key) == 1 else key,
                    "windowsVirtualKeyCode": key_code,
                },
            )

            await asyncio.sleep(0.3)
            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": f"Pressed key: {key}",
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="press_key",
                inputs={"key": key},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="press_key",
                inputs={"key": key},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def go_back(self) -> Dict[str, Any]:
        """Go back in browser history."""
        start_time = time.time()
        await self._send_action("Go Back", "")

        try:
            await self._send_command(
                "Runtime.evaluate",
                {"expression": "window.history.back()", "returnByValue": True},
            )

            await asyncio.sleep(1)
            self._aria_module_initialized = False
            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": "Navigated back",
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="go_back",
                inputs={},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="go_back",
                inputs={},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def go_forward(self) -> Dict[str, Any]:
        """Go forward in browser history."""
        start_time = time.time()
        await self._send_action("Go Forward", "")

        try:
            await self._send_command(
                "Runtime.evaluate",
                {
                    "expression": "window.history.forward()",
                    "returnByValue": True,
                },
            )

            await asyncio.sleep(1)
            self._aria_module_initialized = False
            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": "Navigated forward",
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="go_forward",
                inputs={},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="go_forward",
                inputs={},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def select(self, ref: str, value: str) -> Dict[str, Any]:
        """Select an option from a dropdown."""
        start_time = time.time()
        await self._send_action("Select", f'ref={ref}, value="{value}"')

        try:
            # Highlight the element before selecting
            await self.highlight_element(ref)

            escaped_value = value.replace("'", "\\'")

            select_js = f"""
            (function() {{
                const el = document.querySelector('[data-camel-ref="{ref}"]');
                if (el && el.tagName.toLowerCase() === 'select') {{
                    el.value = '{escaped_value}';
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'Selected: ' + el.value;
                }}
                return 'Select element not found: ref={ref}';
            }})()
            """

            result = await self._send_command(
                "Runtime.evaluate",
                {"expression": select_js, "returnByValue": True},
            )

            result_text = result.get("result", {}).get("value", "Unknown")
            snapshot = await self.get_page_snapshot()

            action_result = {
                "result": result_text,
                "snapshot": snapshot,
            }

            await self._log_action(
                action_name="select",
                inputs={"ref": ref, "value": value},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="select",
                inputs={"ref": ref, "value": value},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def get_tab_info(self) -> List[Dict[str, Any]]:
        """Get information about the current tab."""
        return [
            {
                "id": 0,
                "url": self._current_url,
                "title": self._current_title,
                "is_current": True,
            }
        ]

    async def switch_tab(self, tab_id: int) -> Dict[str, Any]:
        """Switch to a different tab (not fully supported in extension mode)."""
        return {
            "result": "Tab switching not supported in extension proxy mode",
            "snapshot": await self.get_page_snapshot(),
        }

    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        """Close a tab (not fully supported in extension mode)."""
        return {
            "result": "Tab closing not supported in extension proxy mode",
            "snapshot": await self.get_page_snapshot(),
        }

    async def console_exec(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript in the page console."""
        start_time = time.time()
        await self._send_action("Execute JS", code)

        try:
            result = await self._send_command(
                "Runtime.evaluate", {"expression": code, "returnByValue": True}
            )

            # Extract result value from CDP response
            result_obj = result.get("result", {})
            result_type = result_obj.get("type", "undefined")

            # Handle different result types
            if result_type == "undefined":
                result_value = "undefined"
            elif result_type in ("string", "number", "boolean"):
                result_value = result_obj.get("value", "")
            elif result_type == "object":
                # For objects, try to get value (works with returnByValue=True)
                # or fall back to description
                if "value" in result_obj:
                    result_value = result_obj.get("value")
                    # Convert to JSON string if it's a dict/list
                    if isinstance(result_value, (dict, list)):
                        import json

                        result_value = json.dumps(
                            result_value, ensure_ascii=False, indent=2
                        )
                else:
                    result_value = result_obj.get(
                        "description", str(result_obj)
                    )
            else:
                result_value = result_obj.get(
                    "value", result_obj.get("description", "")
                )

            # Check for exceptions in evaluated code
            if "exceptionDetails" in result:
                exception = result["exceptionDetails"]
                error_text = exception.get("text", "Unknown error")
                if "exception" in exception:
                    error_text = exception["exception"].get(
                        "description", error_text
                    )
                result_value = f"Error: {error_text}"

            action_result = {
                "result": str(result_value)
                if result_value is not None
                else "",
                "snapshot": await self.get_page_snapshot(),
            }

            await self._log_action(
                action_name="console_exec",
                inputs={"code": code},
                outputs=action_result,
                execution_time=time.time() - start_time,
            )

            return action_result
        except Exception as e:
            await self._log_action(
                action_name="console_exec",
                inputs={"code": code},
                outputs=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )
            raise

    async def stop(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._log("info", "Extension Proxy server stopped")

    async def disconnect_only(self):
        """Disconnect without stopping (for cleanup)."""
        if self._client:
            await self._client.send(json.dumps({"type": "DETACH"}))
