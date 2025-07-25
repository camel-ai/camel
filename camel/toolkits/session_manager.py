import subprocess
import time

from camel.logger import get_logger


class SessionManager:
    r"""Base class for session management"""

    def __init__(self, session_name: str, working_dir: str):
        self.session_name = session_name
        self.working_dir = working_dir
        self._logger = get_logger(__name__)

    def start_session(self) -> bool:
        r"""Start a new session"""
        raise NotImplementedError

    def send_command(
        self, command: str, block: bool = True, timeout: float = 180.0
    ) -> str:
        r"""Send a command to the session"""
        raise NotImplementedError

    def capture_output(self) -> str:
        r"""Capture the current output from the session"""
        raise NotImplementedError

    def is_session_active(self) -> bool:
        r"""Check if the session is still active"""
        raise NotImplementedError

    def cleanup(self):
        r"""Clean up the session"""
        raise NotImplementedError


class TmuxSession(SessionManager):
    r"""A class that represents a tmux session for Unix systems."""

    _ENTER_KEYS = {"Enter", "C-m", "KPEnter", "C-j", "^M", "^J"}
    _ENDS_WITH_NEWLINE_PATTERN = r"[\r\n]$"
    _NEWLINE_CHARS = "\r\n"
    _TMUX_COMPLETION_COMMAND = "; tmux wait -S done"

    def __init__(self, session_name: str, working_dir: str):
        super().__init__(session_name, working_dir)
        self.session_active = False

    def start_session(self) -> bool:
        try:
            subprocess.run(["tmux", "-V"], check=True, capture_output=True)
            check_cmd = ["tmux", "has-session", "-t", self.session_name]
            result = subprocess.run(check_cmd, capture_output=True)
            if result.returncode == 0:
                self._logger.info(
                    f"Tmux session '{self.session_name}' already exists"
                )
                self.session_active = True
                return True
            start_cmd = [
                "bash",
                "-c",
                f"tmux new-session -x 160 -y 40 -d -s {self.session_name} -c '{self.working_dir}'",
            ]
            subprocess.run(start_cmd, check=True)
            self.session_active = True
            self._logger.info(f"Started tmux session '{self.session_name}'")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self._logger.error(f"Failed to start tmux session: {e}")
            return False

    def _tmux_send_keys(self, keys: list[str]) -> list[str]:
        return [
            "tmux",
            "send-keys",
            "-t",
            self.session_name,
            *keys,
        ]

    def _tmux_capture_pane(self, capture_entire: bool = False) -> list[str]:
        extra_args = ["-S", "-"] if capture_entire else []
        return [
            "tmux",
            "capture-pane",
            "-p",
            *extra_args,
            "-t",
            self.session_name,
        ]

    def _is_executing_command(self, key: str) -> bool:
        return self._is_enter_key(key) or self._ends_with_newline(key)

    def _is_enter_key(self, key: str) -> bool:
        return key in self._ENTER_KEYS

    def _ends_with_newline(self, key: str) -> bool:
        import re

        return bool(re.search(self._ENDS_WITH_NEWLINE_PATTERN, key))

    def _prevent_execution(self, keys: list[str]) -> list[str]:
        keys = keys.copy()
        while keys and self._is_executing_command(keys[-1]):
            if self._is_enter_key(keys[-1]):
                keys.pop()
            else:
                stripped_key = keys[-1].rstrip(self._NEWLINE_CHARS)
                if stripped_key:
                    keys[-1] = stripped_key
                else:
                    keys.pop()
        return keys

    def _prepare_keys(
        self, keys: list[str], block: bool = True
    ) -> tuple[list[str], bool]:
        if isinstance(keys, str):
            keys = [keys]
        if not block or not keys or not self._is_executing_command(keys[-1]):
            return keys, False
        keys = self._prevent_execution(keys)
        keys.extend([self._TMUX_COMPLETION_COMMAND, "Enter"])
        return keys, True

    def _send_blocking_keys(self, keys: list[str], max_timeout_sec: float):
        start_time_sec = time.time()
        subprocess.run(self._tmux_send_keys(keys), check=True)
        result = subprocess.run(
            ["timeout", f"{max_timeout_sec}s", "tmux", "wait", "done"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise TimeoutError(
                f"Command timed out after {max_timeout_sec} seconds"
            )
        elapsed_time_sec = time.time() - start_time_sec
        self._logger.debug(
            f"Blocking command completed in {elapsed_time_sec:.2f}s."
        )

    def _send_non_blocking_keys(self, keys: list[str], min_timeout_sec: float):
        start_time_sec = time.time()
        subprocess.run(self._tmux_send_keys(keys), check=True)
        elapsed_time_sec = time.time() - start_time_sec
        if elapsed_time_sec < min_timeout_sec:
            time.sleep(min_timeout_sec - elapsed_time_sec)

    def send_command(
        self, command: str, block: bool = True, timeout: float = 180.0
    ) -> str:
        if not self.session_active:
            return "Error: Tmux session is not active"
        try:
            keys = [command, "Enter"]
            prepared_keys, is_blocking = self._prepare_keys(
                keys=keys, block=block
            )
            self._logger.debug(f"Sending keys to tmux: {prepared_keys}")
            if is_blocking:
                self._send_blocking_keys(
                    keys=prepared_keys, max_timeout_sec=timeout
                )
                return self.capture_output()
            else:
                self._send_non_blocking_keys(
                    keys=prepared_keys, min_timeout_sec=0.1
                )
                return f"Command sent to tmux session '{self.session_name}'. Use capture_output to see results."
        except Exception as e:
            return f"Tmux error: {e}"

    def capture_output(self) -> str:
        if not self.session_active:
            return "Error: Tmux session is not active"
        try:
            result = subprocess.run(
                self._tmux_capture_pane(capture_entire=True),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error capturing tmux output: {e}"

    def is_session_active(self) -> bool:
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self.session_name],
                capture_output=True,
            )
            self.session_active = result.returncode == 0
            return self.session_active
        except Exception:
            self.session_active = False
            return False

    def cleanup(self):
        if self.session_active:
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", self.session_name],
                    capture_output=True,
                )
                self._logger.info(f"Killed tmux session '{self.session_name}'")
            except Exception as e:
                self._logger.error(f"Error cleaning up tmux session: {e}")
            finally:
                self.session_active = False


class PowerShellSession(SessionManager):
    r"""A class that represents a PowerShell session for Windows systems."""

    def __init__(self, session_name: str, working_dir: str):
        pass

    def start_session(self) -> bool:
        pass

    def send_command(
        self, command: str, block: bool = True, timeout: float = 180.0
    ) -> str:
        pass

    def capture_output(self) -> str:
        pass

    def is_session_active(self) -> bool:
        pass

    def cleanup(self):
        pass
