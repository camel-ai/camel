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
r"""Computer Use toolkit for GUI automation via Claude and other vision models.

This toolkit wraps Anthropic's computer use tools as CAMEL FunctionTools,
enabling agents to control a desktop environment through screenshots, mouse
actions, and keyboard input — all executed inside a Docker sandbox with a
virtual display.

Architecture::

    CAMEL Agent
        │
        ▼
    ComputerUseToolkit
        ├── screenshot()       → Capture desktop state
        ├── mouse_move(x, y)   → Move cursor
        ├── left_click()       → Click at current position
        ├── type_text(text)    → Type via virtual keyboard
        ├── key_combination()  → Press key combos (Ctrl+C, etc.)
        └── wait(seconds)      → Wait for UI transitions
        │
        ▼
    Docker Sandbox (Xvfb + xdotool)
"""

from __future__ import annotations

import base64
import logging
import os
import shlex
import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from camel.toolkits import BaseToolkit, FunctionTool

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ComputerUseToolkit(BaseToolkit):
    r"""A toolkit for GUI automation via vision models.

    Provides tools for controlling a desktop environment (screenshots,
    mouse movement, clicking, typing) inside a Docker sandbox. Designed
    to work with Claude's computer use capability and other vision models.

    The sandbox runs Xvfb (virtual framebuffer) + xdotool and a minimal
    window manager, providing a deterministic, isolated desktop environment.

    Args:
        display_width (int): Virtual display width in pixels (default: 1280).
        display_height (int): Virtual display height in pixels (default: 720).
        sandbox_image (str): Docker image to use for the sandbox.
        sandbox_container_name (str): Name for the sandbox container.
        use_docker (bool): Whether to use a Docker sandbox. If False,
            operates on the host display directly (for local testing).
    """

    def __init__(
        self,
        display_width: int = 1280,
        display_height: int = 720,
        sandbox_image: str = "camel/computer-use:latest",
        sandbox_container_name: str | None = None,
        use_docker: bool = True,
    ):
        super().__init__()

        self.display_width = display_width
        self.display_height = display_height
        self.sandbox_image = sandbox_image
        self.sandbox_container_name = (
            sandbox_container_name or f"camel-cu-{os.getpid()}"
        )
        self.use_docker = use_docker
        self._cursor_position: Tuple[int, int] = (0, 0)
        self._container_id: str | None = None
        self._docker_client: Any = None
        self._docker_api_client: Any = None

        if self.use_docker:
            self._init_docker_sandbox()
        else:
            logger.info(
                "Running in local mode — operating on host display."
            )

    def _init_docker_sandbox(self) -> None:
        r"""Initialize the Docker sandbox with Xvfb and xdotool.

        Pulls the sandbox image if needed, creates the container with
        virtual display, and installs required automation tools.
        """
        try:
            import docker
            from docker.errors import APIError, NotFound
        except ImportError:
            raise ImportError(
                "The 'docker' library is required for Docker sandbox mode. "
                "Install it with: pip install docker"
            )

        self._docker_client = docker.from_env()
        self._docker_api_client = docker.APIClient(
            base_url="unix://var/run/docker.sock"
        )

        # Try to find an existing container with our name
        try:
            container = self._docker_client.containers.get(
                self.sandbox_container_name
            )
            if container.status != "running":
                container.start()
            self._container_id = container.id
            logger.info(
                "Reusing existing sandbox container '%s'.",
                self.sandbox_container_name,
            )
        except (NotFound, APIError):
            logger.info(
                "Creating new sandbox container '%s'...",
                self.sandbox_container_name,
            )
            container = self._docker_client.containers.run(
                self.sandbox_image,
                name=self.sandbox_container_name,
                environment={
                    "DISPLAY": ":99",
                    "WIDTH": str(self.display_width),
                    "HEIGHT": str(self.display_height),
                },
                detach=True,
                stdin_open=True,
                privileged=True,  # Required by Xvfb
            )
            self._container_id = container.id

            # Wait for Xvfb to be ready
            time.sleep(2)
            logger.info(
                "Sandbox container '%s' started (id=%s).",
                self.sandbox_container_name,
                self._container_id[:12],
            )

    def _docker_exec(
        self, command: str, check_exit_code: bool = True
    ) -> Tuple[int, str]:
        r"""Execute a command inside the Docker sandbox.

        Args:
            command: Shell command to execute.
            check_exit_code: If True, raises RuntimeError on non-zero exit.

        Returns:
            Tuple of (exit_code, output_string).
        """
        if not self._docker_api_client or not self._container_id:
            raise RuntimeError("Docker sandbox is not initialized.")

        try:
            exec_id = self._docker_api_client.exec_create(
                self._container_id,
                command,
            )["Id"]
            output = self._docker_api_client.exec_start(exec_id)
            exec_info = self._docker_api_client.exec_inspect(exec_id)
            exit_code = exec_info["ExitCode"]

            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="ignore")

            if check_exit_code and exit_code != 0:
                raise RuntimeError(
                    f"Sandbox command exited with code {exit_code}: "
                    f"{output[:500]}"
                )

            return exit_code, output
        except Exception as e:
            raise RuntimeError(
                f"Docker sandbox error for '{command[:80]}': {e}"
            ) from e

    # ── Screenshot ──────────────────────────────────────────────

    def screenshot(self) -> str:
        r"""Capture a screenshot of the current desktop state.

        Returns:
            A base64-encoded PNG image string suitable for passing to
            vision-capable LLMs (Claude, Gemini, etc.).

        Example:
            >>> toolkit = ComputerUseToolkit()
            >>> img_b64 = toolkit.screenshot()
            >>> # Pass img_b64 to a vision model for analysis
        """
        if self.use_docker:
            cmd = (
                f"import -window root "
                f"-resize {self.display_width}x{self.display_height}! "
                f"PNG:- | base64 -w 0"
            )
            _, output = self._docker_exec(cmd, check_exit_code=False)
            return output.strip()
        else:
            import subprocess

            result = subprocess.run(
                [
                    "import",
                    "-window",
                    "root",
                    "-resize",
                    f"{self.display_width}x{self.display_height}!",
                    "PNG:-",
                ],
                capture_output=True,
                check=False,
            )
            return base64.b64encode(result.stdout).decode("ascii")

    # ── Mouse Actions ───────────────────────────────────────────

    def mouse_move(self, x: int, y: int) -> str:
        r"""Move the mouse cursor to (x, y) coordinates.

        Args:
            x: X coordinate (0 to display_width).
            y: Y coordinate (0 to display_height).

        Returns:
            Status message with new cursor position.
        """
        x = max(0, min(x, self.display_width - 1))
        y = max(0, min(y, self.display_height - 1))
        self._exec_xdotool(f"mousemove {x} {y}")
        self._cursor_position = (x, y)
        return f"Mouse moved to ({x}, {y})"

    def left_click(self) -> str:
        r"""Click the left mouse button at the current cursor position.

        Returns:
            Status message.
        """
        self._exec_xdotool("click 1")
        return f"Left click at {self._cursor_position}"

    def right_click(self) -> str:
        r"""Click the right mouse button at the current cursor position.

        Returns:
            Status message.
        """
        self._exec_xdotool("click 3")
        return f"Right click at {self._cursor_position}"

    def double_click(self) -> str:
        r"""Double-click the left mouse button at the current cursor position.

        Returns:
            Status message.
        """
        self._exec_xdotool("click --repeat 2 1")
        return f"Double click at {self._cursor_position}"

    def left_click_drag(self, x: int, y: int) -> str:
        r"""Click and drag from the current position to (x, y).

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.

        Returns:
            Status message with drag information.
        """
        cx, cy = self._cursor_position
        self._exec_xdotool(f"mousedown 1 mousemove {x} {y} mouseup 1")
        self._cursor_position = (x, y)
        return f"Dragged from ({cx}, {cy}) to ({x}, {y})"

    def scroll(self, amount: int) -> str:
        r"""Scroll up (positive) or down (negative) at the current cursor.

        Args:
            amount: Pixels to scroll. Positive = up, negative = down.

        Returns:
            Status message.
        """
        button = 4 if amount > 0 else 5  # 4=up, 5=down
        clicks = min(abs(amount), 100)
        self._exec_xdotool(f"click --repeat {clicks} {button}")
        direction = "up" if amount > 0 else "down"
        return f"Scrolled {direction} {clicks} ticks"

    # ── Keyboard Actions ────────────────────────────────────────

    def type_text(self, text: str) -> str:
        r"""Type the given text into the active window.

        Args:
            text: The text to type. Special characters are handled by
                  xdotool's type command.

        Returns:
            Status message.
        """
        safe_text = shlex.quote(text)
        self._exec_xdotool(f"type {safe_text}")
        preview = text[:50] + ("..." if len(text) > 50 else "")
        return f"Typed: {preview}"

    def key_combination(self, keys: List[str]) -> str:
        r"""Press a key combination (e.g., ['ctrl', 'c'] for Ctrl+C).

        Args:
            keys: List of key names to press together.

        Returns:
            Status message.
        """
        key_str = "+".join(keys)
        self._exec_xdotool(f"key {key_str}")
        return f"Pressed: {key_str}"

    def press_key(self, key: str) -> str:
        r"""Press a single key.

        Args:
            key: Key name (e.g., 'Return', 'Escape', 'Tab').

        Returns:
            Status message.
        """
        self._exec_xdotool(f"key {key}")
        return f"Pressed key: {key}"

    # ── Utility ─────────────────────────────────────────────────

    def wait(self, seconds: float = 1.0) -> str:
        r"""Wait for the specified duration (for UI transitions).

        Args:
            seconds: Duration to wait in seconds (capped at 10).

        Returns:
            Status message.
        """
        time.sleep(min(seconds, 10.0))
        return f"Waited {seconds}s"

    def get_screen_size(self) -> dict:
        r"""Get the virtual display dimensions.

        Returns:
            Dict with 'width' and 'height' keys.
        """
        return {"width": self.display_width, "height": self.display_height}

    def get_cursor_position(self) -> dict:
        r"""Get the current cursor position.

        Returns:
            Dict with 'x' and 'y' keys.
        """
        return {"x": self._cursor_position[0], "y": self._cursor_position[1]}

    # ── Internal ────────────────────────────────────────────────

    def _exec_xdotool(self, action: str) -> None:
        r"""Execute an xdotool action inside the sandbox."""
        cmd = f"DISPLAY=:99 xdotool {action}"
        if self.use_docker:
            self._docker_exec(cmd, check_exit_code=False)
        else:
            import subprocess

            subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                check=False,
            )

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the list of computer use tools for agent registration.

        Returns:
            List of FunctionTool instances wrapping each computer use action.
        """
        return [
            FunctionTool(self.screenshot),
            FunctionTool(self.mouse_move),
            FunctionTool(self.left_click),
            FunctionTool(self.right_click),
            FunctionTool(self.double_click),
            FunctionTool(self.left_click_drag),
            FunctionTool(self.scroll),
            FunctionTool(self.type_text),
            FunctionTool(self.key_combination),
            FunctionTool(self.press_key),
            FunctionTool(self.wait),
            FunctionTool(self.get_screen_size),
            FunctionTool(self.get_cursor_position),
        ]

    def cleanup(self) -> None:
        r"""Stop and remove the Docker sandbox container."""
        if self._container_id and self._docker_client:
            try:
                container = self._docker_client.containers.get(
                    self._container_id
                )
                container.stop()
                container.remove()
                logger.info(
                    "Sandbox container '%s' cleaned up.",
                    self.sandbox_container_name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to clean up sandbox container: %s", e
                )

    def __del__(self) -> None:
        r"""Attempt cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception:
            pass
