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
import contextlib
import datetime
import json
import os
import subprocess
import time
import uuid
from contextvars import ContextVar
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

from .installer import check_and_install_dependencies

logger = get_logger(__name__)

# Context variable to track if we're inside a high-level action
_in_high_level_action: ContextVar[bool] = ContextVar(
    '_in_high_level_action', default=False
)


def _create_memory_aware_error(base_msg: str) -> str:
    import psutil

    mem = psutil.virtual_memory()
    if mem.available < 1024**3:
        return (
            f"{base_msg} "
            f"(likely due to insufficient memory). "
            f"Available memory: {mem.available / 1024**3:.2f}GB "
            f"({mem.percent}% used)"
        )
    return base_msg


async def _cleanup_process_and_tasks(process, log_reader_task, ts_log_file):
    if process:
        with contextlib.suppress(ProcessLookupError, Exception):
            process.kill()
        with contextlib.suppress(Exception):
            process.wait(timeout=2)

    if log_reader_task and not log_reader_task.done():
        log_reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await log_reader_task

    if ts_log_file:
        with contextlib.suppress(Exception):
            ts_log_file.close()


def action_logger(func):
    """Decorator to add logging to action methods.

    Skips logging if already inside a high-level action to avoid
    logging internal calls.
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Skip logging if we're already inside a high-level action
        if _in_high_level_action.get():
            return await func(self, *args, **kwargs)

        action_name = func.__name__
        start_time = time.time()

        inputs = {
            "args": args,
            "kwargs": kwargs,
        }

        try:
            result = await func(self, *args, **kwargs)
            execution_time = time.time() - start_time

            page_load_time = None
            if isinstance(result, dict) and 'page_load_time_ms' in result:
                page_load_time = result['page_load_time_ms'] / 1000.0

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

            await self._log_action(
                action_name=action_name,
                inputs=inputs,
                outputs=None,
                execution_time=execution_time,
                error=error_msg,
            )

            raise

    return wrapper


def high_level_action(func):
    """Decorator for high-level actions that should suppress low-level logging.

    When a function is decorated with this, all low-level action_logger
    decorated functions called within it will skip logging. This decorator
    itself will log the high-level action.
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        action_name = func.__name__
        start_time = time.time()

        inputs = {
            "args": args,
            "kwargs": kwargs,
        }

        # Set the context variable to indicate we're in a high-level action
        token = _in_high_level_action.set(True)
        try:
            result = await func(self, *args, **kwargs)
            execution_time = time.time() - start_time

            # Log the high-level action
            if hasattr(self, '_get_ws_wrapper'):
                # This is a HybridBrowserToolkit instance
                ws_wrapper = await self._get_ws_wrapper()
                await ws_wrapper._log_action(
                    action_name=action_name,
                    inputs=inputs,
                    outputs=result,
                    execution_time=execution_time,
                    page_load_time=None,
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {e!s}"

            # Log the error
            if hasattr(self, '_get_ws_wrapper'):
                ws_wrapper = await self._get_ws_wrapper()
                await ws_wrapper._log_action(
                    action_name=action_name,
                    inputs=inputs,
                    outputs=None,
                    execution_time=execution_time,
                    error=error_msg,
                )

            raise
        finally:
            # Reset the context variable
            _in_high_level_action.reset(token)

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
        self._send_lock = asyncio.Lock()
        self._receive_task = None
        self._pending_responses: Dict[str, asyncio.Future[Dict[str, Any]]] = {}
        self._browser_opened = False
        self._server_ready_future = None

        self.browser_log_to_file = (config or {}).get(
            'browser_log_to_file', False
        )
        self.log_dir = (config or {}).get('log_dir', 'browser_log')
        self.session_id = (config or {}).get('session_id', 'default')
        self.log_file_path: Optional[str] = None
        self.log_buffer: List[Dict[str, Any]] = []
        self.ts_log_file_path: Optional[str] = None
        self.ts_log_file = None
        self._log_reader_task = None

        if self.browser_log_to_file:
            log_dir = self.log_dir if self.log_dir else "browser_log"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = os.path.join(
                log_dir,
                f"hybrid_browser_toolkit_ws_{timestamp}_{self.session_id}.log",
            )
            self.ts_log_file_path = os.path.join(
                log_dir,
                f"typescript_console_{timestamp}_{self.session_id}.log",
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def _cleanup_existing_processes(self):
        """Clean up any existing Node.js WebSocket server processes."""
        import psutil

        cleaned_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (
                    proc.info['name']
                    and 'node' in proc.info['name'].lower()
                    and proc.info['cmdline']
                    and any(
                        'websocket-server.js' in arg
                        for arg in proc.info['cmdline']
                    )
                ):
                    if any(self.ts_dir in arg for arg in proc.info['cmdline']):
                        logger.warning(
                            f"Found existing WebSocket server process "
                            f"(PID: {proc.info['pid']}). "
                            f"Terminating it to prevent conflicts."
                        )
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        cleaned_count += 1
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                pass

        if cleaned_count > 0:
            logger.warning(
                f"Cleaned up {cleaned_count} existing WebSocket server "
                f"process(es). This may have been caused by improper "
                f"shutdown in previous sessions."
            )
            await asyncio.sleep(0.5)

    async def start(self):
        """Start the WebSocket server and connect to it."""
        await self._cleanup_existing_processes()

        npm_cmd, node_cmd = await check_and_install_dependencies(self.ts_dir)

        import platform

        use_shell = platform.system() == 'Windows'

        self.process = subprocess.Popen(
            [node_cmd, 'websocket-server.js'],
            cwd=self.ts_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            shell=use_shell,
        )

        self._server_ready_future = asyncio.get_running_loop().create_future()

        self._log_reader_task = asyncio.create_task(
            self._read_and_log_output()
        )

        if self.browser_log_to_file and self.ts_log_file_path:
            logger.info(
                f"TypeScript console logs will be written to: "
                f"{self.ts_log_file_path}"
            )

        server_ready = False
        timeout = 10

        try:
            await asyncio.wait_for(self._server_ready_future, timeout=timeout)
            server_ready = True
        except asyncio.TimeoutError:
            server_ready = False

        if not server_ready:
            await _cleanup_process_and_tasks(
                self.process,
                self._log_reader_task,
                getattr(self, 'ts_log_file', None),
            )
            self.ts_log_file = None
            self.process = None

            error_msg = _create_memory_aware_error(
                "WebSocket server failed to start within timeout"
            )
            raise RuntimeError(error_msg)

        max_retries = 3
        retry_delays = [1, 2, 4]

        for attempt in range(max_retries):
            try:
                connect_timeout = 10.0 + (attempt * 5.0)

                logger.info(
                    f"Attempting to connect to WebSocket server "
                    f"(attempt {attempt + 1}/{max_retries}, "
                    f"timeout: {connect_timeout}s)"
                )

                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        f"ws://localhost:{self.server_port}",
                        ping_interval=30,
                        ping_timeout=10,
                        max_size=50 * 1024 * 1024,
                    ),
                    timeout=connect_timeout,
                )
                logger.info("Connected to WebSocket server")
                break

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"WebSocket handshake timeout "
                        f"(attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Failed to connect to WebSocket server after "
                        f"{max_retries} attempts: Handshake timeout"
                    )

            except Exception as e:
                if attempt < max_retries - 1 and "timed out" in str(e).lower():
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"WebSocket connection failed "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        if not self.websocket:
            await _cleanup_process_and_tasks(
                self.process,
                self._log_reader_task,
                getattr(self, 'ts_log_file', None),
            )
            self.ts_log_file = None
            self.process = None

            error_msg = _create_memory_aware_error(
                "Failed to connect to WebSocket server after multiple attempts"
            )
            raise RuntimeError(error_msg)

        self._receive_task = asyncio.create_task(self._receive_loop())

        await self._send_command('init', self.config)

        if self.config.get('cdpUrl'):
            self._browser_opened = True

    async def stop(self):
        """Stop the WebSocket connection and server."""
        if self.websocket:
            with contextlib.suppress(asyncio.TimeoutError, Exception):
                await asyncio.wait_for(
                    self._send_command('shutdown', {}),
                    timeout=2.0,
                )

            with contextlib.suppress(Exception):
                await self.websocket.close()
            self.websocket = None

        self._browser_opened = False

        # Gracefully stop the Node process before cancelling the log reader
        if self.process:
            try:
                # give the process a short grace period to exit after shutdown
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(ProcessLookupError, Exception):
                        self.process.kill()
                        self.process.wait()
                except Exception as e:
                    logger.warning(f"Error terminating process: {e}")
            except Exception as e:
                logger.warning(f"Error waiting for process: {e}")

        # Now cancel background tasks (reader won't block on readline)
        tasks_to_cancel = [
            ('_receive_task', self._receive_task),
            ('_log_reader_task', self._log_reader_task),
        ]
        for _, task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Close TS log file if open
        if getattr(self, 'ts_log_file', None):
            with contextlib.suppress(Exception):
                self.ts_log_file.close()
            self.ts_log_file = None

        # Ensure process handle cleared
        self.process = None

    async def disconnect_only(self):
        """Disconnect WebSocket and stop server without closing the browser.

        This is useful for CDP mode where the browser should remain open.
        """
        if self.websocket:
            with contextlib.suppress(Exception):
                await self.websocket.close()
            self.websocket = None

        self._browser_opened = False

        # Stop the Node process
        if self.process:
            try:
                # Send SIGTERM to gracefully shutdown
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                with contextlib.suppress(ProcessLookupError, Exception):
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")

        # Cancel background tasks
        tasks_to_cancel = [
            ('_receive_task', self._receive_task),
            ('_log_reader_task', self._log_reader_task),
        ]
        for _, task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Close TS log file if open
        if getattr(self, 'ts_log_file', None):
            with contextlib.suppress(Exception):
                self.ts_log_file.close()
            self.ts_log_file = None

        # Ensure process handle cleared
        self.process = None

        logger.info("WebSocket disconnected without closing browser")

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
                    # Check if it's a normal WebSocket close
                    if isinstance(e, websockets.exceptions.ConnectionClosed):
                        if e.code == 1000:  # Normal closure
                            logger.debug(f"WebSocket closed normally: {e}")
                        else:
                            logger.warning(
                                f"WebSocket closed with code {e.code}: {e}"
                            )
                    else:
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
            error_msg = _create_memory_aware_error("WebSocket not connected")
            raise RuntimeError(error_msg)

        # Check if connection is still alive
        try:
            # Send a ping and wait for the corresponding pong (bounded wait)
            pong_waiter = await self.websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=5.0)
        except Exception as e:
            logger.warning(f"WebSocket ping failed: {e}")
            self.websocket = None

            error_msg = _create_memory_aware_error("WebSocket connection lost")
            raise RuntimeError(error_msg)

    async def _send_command(
        self, command: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a command to the WebSocket server and get response."""
        await self._ensure_connection()

        # Process params to ensure refs have 'e' prefix
        params = self._process_refs_in_params(params)

        message_id = str(uuid.uuid4())
        message = {'id': message_id, 'command': command, 'params': params}

        # Create a future for this message
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Dict[str, Any]] = loop.create_future()
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
                # Special handling for shutdown command
                if command == 'shutdown':
                    logger.debug(
                        "Shutdown command timeout is expected - "
                        "server may have closed before responding"
                    )
                    # Return a success response for shutdown
                    return {
                        'message': 'Browser shutdown (no response received)'
                    }
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
                # Special handling for shutdown command
                if command == 'shutdown':
                    logger.debug(
                        f"Connection closed during shutdown (expected): {e}"
                    )
                    return {'message': 'Browser shutdown (connection closed)'}
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
        self._browser_opened = True
        return response

    @action_logger
    async def close_browser(self) -> str:
        """Close browser."""
        response = await self._send_command('close_browser', {})
        self._browser_opened = False
        return response['message']

    @action_logger
    async def visit_page(self, url: str) -> Dict[str, Any]:
        """Visit a page.

        In non-CDP mode, automatically opens browser if not already open.
        """
        if not self._browser_opened:
            is_cdp_mode = bool(self.config.get('cdpUrl'))

            if not is_cdp_mode:
                logger.info(
                    "Browser not open, automatically opening browser..."
                )
                await self.open_browser()

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

    def _ensure_ref_prefix(self, ref: str) -> str:
        """Ensure ref has proper prefix"""
        if not ref:
            return ref

        # If ref is purely numeric, add 'e' prefix for main frame
        if ref.isdigit():
            return f'e{ref}'

        return ref

    def _process_refs_in_params(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process parameters to ensure all refs have 'e' prefix."""
        if not params:
            return params

        # Create a copy to avoid modifying the original
        processed = params.copy()

        # Handle direct ref parameters
        if 'ref' in processed:
            processed['ref'] = self._ensure_ref_prefix(processed['ref'])

        # Handle from_ref and to_ref for drag operations
        if 'from_ref' in processed:
            processed['from_ref'] = self._ensure_ref_prefix(
                processed['from_ref']
            )
        if 'to_ref' in processed:
            processed['to_ref'] = self._ensure_ref_prefix(processed['to_ref'])

        # Handle inputs array for type_multiple
        if 'inputs' in processed and isinstance(processed['inputs'], list):
            processed_inputs = []
            for input_item in processed['inputs']:
                if isinstance(input_item, dict) and 'ref' in input_item:
                    processed_input = input_item.copy()
                    processed_input['ref'] = self._ensure_ref_prefix(
                        input_item['ref']
                    )
                    processed_inputs.append(processed_input)
                else:
                    processed_inputs.append(input_item)
            processed['inputs'] = processed_inputs

        return processed

    @action_logger
    async def click(self, ref: str) -> Dict[str, Any]:
        """Click an element."""
        response = await self._send_command('click', {'ref': ref})
        return response

    @action_logger
    async def type(self, ref: str, text: str) -> Dict[str, Any]:
        """Type text into an element."""
        response = await self._send_command('type', {'ref': ref, 'text': text})
        # Log the response for debugging
        logger.debug(f"Type response for ref {ref}: {response}")
        return response

    @action_logger
    async def type_multiple(
        self, inputs: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Type text into multiple elements."""
        response = await self._send_command('type', {'inputs': inputs})
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
    async def mouse_control(
        self, control: str, x: float, y: float
    ) -> Dict[str, Any]:
        """Control the mouse to interact with browser with x, y coordinates."""
        response = await self._send_command(
            'mouse_control', {'control': control, 'x': x, 'y': y}
        )
        return response

    @action_logger
    async def mouse_drag(self, from_ref: str, to_ref: str) -> Dict[str, Any]:
        """Control the mouse to drag and drop in the browser using ref IDs."""
        response = await self._send_command(
            'mouse_drag',
            {'from_ref': from_ref, 'to_ref': to_ref},
        )
        return response

    @action_logger
    async def press_key(self, keys: List[str]) -> Dict[str, Any]:
        """Press key and key combinations."""
        response = await self._send_command('press_key', {'keys': keys})
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
    async def console_view(self) -> List[Dict[str, Any]]:
        """Get current page console view"""
        response = await self._send_command('console_view', {})

        if isinstance(response, list):
            return response

        return response.get('logs', [])

    @action_logger
    async def console_exec(self, code: str) -> Dict[str, Any]:
        """Execute javascript code and get result."""
        response = await self._send_command('console_exec', {'code': code})
        return response

    @action_logger
    async def wait_user(
        self, timeout_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for user input."""
        response = await self._send_command(
            'wait_user', {'timeout': timeout_sec}
        )
        return response

    async def _read_and_log_output(self):
        """Read stdout from Node.js process & handle SERVER_READY + logging."""
        if not self.process:
            return

        try:
            with contextlib.ExitStack() as stack:
                if self.ts_log_file_path:
                    self.ts_log_file = stack.enter_context(
                        open(self.ts_log_file_path, 'w', encoding='utf-8')
                    )
                    self.ts_log_file.write(
                        f"TypeScript Console Log - Started at "
                        f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    self.ts_log_file.write("=" * 80 + "\n")
                    self.ts_log_file.flush()

                while self.process and self.process.poll() is None:
                    try:
                        line = (
                            await asyncio.get_running_loop().run_in_executor(
                                None, self.process.stdout.readline
                            )
                        )
                        if not line:  # EOF
                            break

                        # Check for SERVER_READY message
                        if line.startswith('SERVER_READY:'):
                            try:
                                self.server_port = int(
                                    line.split(':', 1)[1].strip()
                                )
                                logger.info(
                                    f"WebSocket server ready on port "
                                    f"{self.server_port}"
                                )
                                if (
                                    self._server_ready_future
                                    and not self._server_ready_future.done()
                                ):
                                    self._server_ready_future.set_result(True)
                            except (ValueError, IndexError) as e:
                                logger.error(
                                    f"Failed to parse SERVER_READY: {e}"
                                )

                        # Write all output to log file
                        if self.ts_log_file:
                            timestamp = time.strftime('%H:%M:%S')
                            self.ts_log_file.write(f"[{timestamp}] {line}")
                            self.ts_log_file.flush()

                    except Exception as e:
                        logger.warning(f"Error reading stdout: {e}")
                        break

                # Footer if we had a file
                if self.ts_log_file:
                    self.ts_log_file.write("\n" + "=" * 80 + "\n")
                    self.ts_log_file.write(
                        f"TypeScript Console Log - Ended at "
                        f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                # ExitStack closes file; clear handle
                self.ts_log_file = None
        except Exception as e:
            logger.warning(f"Error in _read_and_log_output: {e}")
