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
import datetime
import json
import os
import subprocess
import time
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import websockets
else:
    try:
        import websockets
    except ImportError:
        websockets = None

from camel.logger import get_logger
from camel.utils.tool_result import ToolResult

logger = get_logger(__name__)


def action_logger(func):
    """Decorator to add logging to action methods."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        action_name = func.__name__
        start_time = time.time()

        # Log inputs (skip self)
        inputs = {
            "args": args,
            "kwargs": kwargs,
        }

        try:
            # Execute the original function
            result = await func(self, *args, **kwargs)
            execution_time = time.time() - start_time

            # Extract page load time if available
            page_load_time = None
            if isinstance(result, dict) and 'page_load_time_ms' in result:
                page_load_time = result['page_load_time_ms'] / 1000.0

            # Log success
            await self._log_action(
                action_name=action_name,
                inputs=inputs,
                outputs=result,
                execution_time=execution_time,
                page_load_time=page_load_time,
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {e!s}"

            # Log error
            await self._log_action(
                action_name=action_name,
                inputs=inputs,
                outputs=None,
                execution_time=execution_time,
                error=error_msg,
            )

            raise

    return wrapper


class WebSocketBrowserWrapper:
    """Python wrapper for the TypeScript hybrid browser
    toolkit implementation using WebSocket."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the wrapper.

        Args:
            config: Configuration dictionary for the browser toolkit
        """
        if websockets is None:
            raise ImportError(
                "websockets package is required for WebSocket communication. "
                "Install with: pip install websockets"
            )

        self.config = config or {}
        self.ts_dir = os.path.join(os.path.dirname(__file__), 'ts')
        self.process: Optional[subprocess.Popen] = None
        self.websocket = None
        self.server_port = None
        self._send_lock = asyncio.Lock()  # Lock for sending messages
        self._receive_task = None  # Background task for receiving messages
        self._pending_responses: Dict[
            str, asyncio.Future[Dict[str, Any]]
        ] = {}  # Message ID -> Future

        # Logging configuration
        self.browser_log_to_file = (config or {}).get(
            'browser_log_to_file', False
        )
        self.session_id = (config or {}).get('session_id', 'default')
        self.log_file_path: Optional[str] = None
        self.log_buffer: List[Dict[str, Any]] = []

        # Set up log file if needed
        if self.browser_log_to_file:
            log_dir = "browser_log"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = os.path.join(
                log_dir,
                f"hybrid_browser_toolkit_ws_{timestamp}_{self.session_id}.log",
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Start the WebSocket server and connect to it."""
        # Check if npm is installed
        npm_check = subprocess.run(
            ['npm', '--version'],
            capture_output=True,
            text=True,
        )
        if npm_check.returncode != 0:
            raise RuntimeError(
                "npm is not installed or not in PATH. "
                "Please install Node.js and npm from https://nodejs.org/ "
                "to use the hybrid browser toolkit."
            )

        # Check if node is installed
        node_check = subprocess.run(
            ['node', '--version'],
            capture_output=True,
            text=True,
        )
        if node_check.returncode != 0:
            raise RuntimeError(
                "node is not installed or not in PATH. "
                "Please install Node.js from https://nodejs.org/ "
                "to use the hybrid browser toolkit."
            )

        # Check if node_modules exists (dependencies installed)
        node_modules_path = os.path.join(self.ts_dir, 'node_modules')
        if not os.path.exists(node_modules_path):
            logger.warning("Node modules not found. Running npm install...")
            install_result = subprocess.run(
                ['npm', 'install'],
                cwd=self.ts_dir,
                capture_output=True,
                text=True,
            )
            if install_result.returncode != 0:
                logger.error(f"npm install failed: {install_result.stderr}")
                raise RuntimeError(
                    f"Failed to install npm dependencies: {install_result.stderr}\n"  # noqa:E501
                    f"Please run 'npm install' in {self.ts_dir} manually."
                )
            logger.info("npm dependencies installed successfully")

        # Ensure the TypeScript code is built
        build_result = subprocess.run(
            ['npm', 'run', 'build'],
            cwd=self.ts_dir,
            capture_output=True,
            text=True,
        )
        if build_result.returncode != 0:
            logger.error(f"TypeScript build failed: {build_result.stderr}")
            raise RuntimeError(
                f"TypeScript build failed: {build_result.stderr}"
            )

        # Start the WebSocket server
        self.process = subprocess.Popen(
            ['node', 'websocket-server.js'],
            cwd=self.ts_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for server to output the port
        server_ready = False
        timeout = 10  # 10 seconds timeout
        start_time = time.time()

        while not server_ready and time.time() - start_time < timeout:
            if self.process.poll() is not None:
                # Process died
                stderr = self.process.stderr.read()
                raise RuntimeError(
                    f"WebSocket server failed to start: {stderr}"
                )

            try:
                line = self.process.stdout.readline()
                if line.startswith('SERVER_READY:'):
                    self.server_port = int(line.split(':')[1].strip())
                    server_ready = True
                    logger.info(
                        f"WebSocket server ready on port {self.server_port}"
                    )
            except (ValueError, IndexError):
                continue

        if not server_ready:
            self.process.kill()
            raise RuntimeError(
                "WebSocket server failed to start within timeout"
            )

        # Connect to the WebSocket server
        try:
            self.websocket = await websockets.connect(
                f"ws://localhost:{self.server_port}",
                ping_interval=30,
                ping_timeout=10,
                max_size=50 * 1024 * 1024,  # 50MB limit to match server
            )
            logger.info("Connected to WebSocket server")
        except Exception as e:
            self.process.kill()
            raise RuntimeError(
                f"Failed to connect to WebSocket server: {e}"
            ) from e

        # Start the background receiver task
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Initialize the browser toolkit
        await self._send_command('init', self.config)

    async def stop(self):
        """Stop the WebSocket connection and server."""
        # Cancel the receiver task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            try:
                await self._send_command('shutdown', {})
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error during websocket shutdown: {e}")
            finally:
                self.websocket = None

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")
            finally:
                self.process = None

    async def _log_action(
        self,
        action_name: str,
        inputs: Dict[str, Any],
        outputs: Any,
        execution_time: float,
        page_load_time: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log action details with comprehensive
        information including detailed timing breakdown."""
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
            # Handle ToolResult objects for JSON serialization
            if hasattr(outputs, 'text') and hasattr(outputs, 'images'):
                # This is a ToolResult object
                log_entry["outputs"] = {
                    "text": outputs.text,
                    "images_count": len(outputs.images)
                    if outputs.images
                    else 0,
                }
            else:
                log_entry["outputs"] = outputs

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

    async def _receive_loop(self):
        r"""Background task to receive messages from WebSocket."""
        try:
            while self.websocket:
                try:
                    response_data = await self.websocket.recv()
                    response = json.loads(response_data)

                    message_id = response.get('id')
                    if message_id and message_id in self._pending_responses:
                        # Set the result for the waiting coroutine
                        future = self._pending_responses.pop(message_id)
                        if not future.done():
                            future.set_result(response)
                    else:
                        # Log unexpected messages
                        logger.warning(
                            f"Received unexpected message: {response}"
                        )

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in receive loop: {e}")
                    # Notify all pending futures of the error
                    for future in self._pending_responses.values():
                        if not future.done():
                            future.set_exception(e)
                    self._pending_responses.clear()
                    break
        finally:
            logger.debug("Receive loop terminated")

    async def _ensure_connection(self) -> None:
        """Ensure WebSocket connection is alive."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        # Check if connection is still alive
        try:
            # Send a ping to check connection
            await self.websocket.ping()
        except Exception as e:
            logger.warning(f"WebSocket ping failed: {e}")
            self.websocket = None
            raise RuntimeError("WebSocket connection lost")

    async def _send_command(
        self, command: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a command to the WebSocket server and get response."""
        await self._ensure_connection()

        message_id = str(uuid.uuid4())
        message = {'id': message_id, 'command': command, 'params': params}

        # Create a future for this message
        future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
        self._pending_responses[message_id] = future

        try:
            # Use lock only for sending to prevent interleaved messages
            async with self._send_lock:
                if self.websocket is None:
                    raise RuntimeError("WebSocket connection not established")
                await self.websocket.send(json.dumps(message))

            # Wait for response (no lock needed, handled by background
            # receiver)
            try:
                response = await asyncio.wait_for(future, timeout=60.0)

                if not response.get('success'):
                    raise RuntimeError(
                        f"Command failed: {response.get('error')}"
                    )
                return response['result']

            except asyncio.TimeoutError:
                # Remove from pending if timeout
                self._pending_responses.pop(message_id, None)
                raise RuntimeError(
                    f"Timeout waiting for response to command: {command}"
                )

        except Exception as e:
            # Clean up the pending response
            self._pending_responses.pop(message_id, None)

            # Check if it's a connection closed error
            if (
                "close frame" in str(e)
                or "connection closed" in str(e).lower()
            ):
                logger.error(f"WebSocket connection closed unexpectedly: {e}")
                # Mark connection as closed
                self.websocket = None
                raise RuntimeError(
                    f"WebSocket connection lost "
                    f"during {command} operation: {e}"
                )
            else:
                logger.error(f"WebSocket communication error: {e}")
                raise

    # Browser action methods
    @action_logger
    async def open_browser(
        self, start_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Open browser."""
        response = await self._send_command(
            'open_browser', {'startUrl': start_url}
        )
        return response

    @action_logger
    async def close_browser(self) -> str:
        """Close browser."""
        response = await self._send_command('close_browser', {})
        return response['message']

    @action_logger
    async def visit_page(self, url: str) -> Dict[str, Any]:
        """Visit a page."""
        response = await self._send_command('visit_page', {'url': url})
        return response

    @action_logger
    async def get_page_snapshot(self, viewport_limit: bool = False) -> str:
        """Get page snapshot."""
        response = await self._send_command(
            'get_page_snapshot', {'viewport_limit': viewport_limit}
        )
        # The backend returns the snapshot string directly,
        # not wrapped in an object
        if isinstance(response, str):
            return response
        # Fallback if wrapped in an object
        return response.get('snapshot', '')

    @action_logger
    async def get_snapshot_for_ai(self) -> Dict[str, Any]:
        """Get snapshot for AI with element details."""
        response = await self._send_command('get_snapshot_for_ai', {})
        return response

    @action_logger
    async def get_som_screenshot(self) -> ToolResult:
        """Get screenshot."""
        logger.info("Requesting screenshot via WebSocket...")
        start_time = time.time()

        response = await self._send_command('get_som_screenshot', {})

        end_time = time.time()
        logger.info(f"Screenshot completed in {end_time - start_time:.2f}s")

        return ToolResult(text=response['text'], images=response['images'])

    @action_logger
    async def click(self, ref: str) -> Dict[str, Any]:
        """Click an element."""
        response = await self._send_command('click', {'ref': ref})
        return response

    @action_logger
    async def type(self, ref: str, text: str) -> Dict[str, Any]:
        """Type text into an element."""
        response = await self._send_command('type', {'ref': ref, 'text': text})
        return response

    @action_logger
    async def select(self, ref: str, value: str) -> Dict[str, Any]:
        """Select an option."""
        response = await self._send_command(
            'select', {'ref': ref, 'value': value}
        )
        return response

    @action_logger
    async def scroll(self, direction: str, amount: int) -> Dict[str, Any]:
        """Scroll the page."""
        response = await self._send_command(
            'scroll', {'direction': direction, 'amount': amount}
        )
        return response

    @action_logger
    async def enter(self) -> Dict[str, Any]:
        """Press enter."""
        response = await self._send_command('enter', {})
        return response

    @action_logger
    async def back(self) -> Dict[str, Any]:
        """Navigate back."""
        response = await self._send_command('back', {})
        return response

    @action_logger
    async def forward(self) -> Dict[str, Any]:
        """Navigate forward."""
        response = await self._send_command('forward', {})
        return response

    @action_logger
    async def switch_tab(self, tab_id: str) -> Dict[str, Any]:
        """Switch to a tab."""
        response = await self._send_command('switch_tab', {'tabId': tab_id})
        return response

    @action_logger
    async def close_tab(self, tab_id: str) -> Dict[str, Any]:
        """Close a tab."""
        response = await self._send_command('close_tab', {'tabId': tab_id})
        return response

    @action_logger
    async def get_tab_info(self) -> List[Dict[str, Any]]:
        """Get tab information."""
        response = await self._send_command('get_tab_info', {})
        # The backend returns the tab list directly, not wrapped in an object
        if isinstance(response, list):
            return response
        # Fallback if wrapped in an object
        return response.get('tabs', [])

    @action_logger
    async def wait_user(
        self, timeout_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for user input."""
        response = await self._send_command(
            'wait_user', {'timeout': timeout_sec}
        )
        return response
