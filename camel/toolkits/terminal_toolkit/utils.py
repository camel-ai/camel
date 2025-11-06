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

import os
import platform
import re
import shutil
import subprocess
import sys
import venv
from typing import Optional, Set, Tuple

from camel.logger import get_logger

logger = get_logger(__name__)


def check_command_safety(
    command: str,
    allowed_commands: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    r"""Check if a command (potentially with chaining) is safe to execute.

    Args:
        command (str): The command string to check
        allowed_commands (Optional[Set[str]]): Set of allowed commands
            (whitelist mode)

    Returns:
        Tuple[bool, str]: (is_safe, reason)
    """
    if not command.strip():
        return False, "Empty command is not allowed."

    # Dangerous commands list - including ALL rm operations
    dangerous_commands = [
        # System administration
        'sudo',
        'su',
        'reboot',
        'shutdown',
        'halt',
        'poweroff',
        'init',
        # File system manipulation
        'rm',
        'chown',
        'chgrp',
        'umount',
        'mount',
        # Disk operations
        'dd',
        'mkfs',
        'fdisk',
        'parted',
        'fsck',
        'mkswap',
        'swapon',
        'swapoff',
        # Process management
        'service',
        'systemctl',
        'systemd',
        # Network configuration
        'iptables',
        'ip6tables',
        'ifconfig',
        'route',
        'iptables-save',
        # Cron and scheduling
        'crontab',
        'at',
        'batch',
        # User management
        'useradd',
        'userdel',
        'usermod',
        'passwd',
        'chpasswd',
        'newgrp',
        # Kernel modules
        'modprobe',
        'rmmod',
        'insmod',
        'lsmod',
    ]

    # Remove quoted strings to avoid false positives
    clean_command = re.sub(r'''["'][^"']*["']''', ' ', command)

    # If whitelist mode, check ALL commands against the whitelist
    if allowed_commands is not None:
        # Extract all command words (at start or after operators)
        cmd_pattern = r'(?:^|;|\||&&)\s*\b([a-zA-Z_/][\w\-/]*)'
        found_commands = re.findall(cmd_pattern, clean_command, re.IGNORECASE)
        for cmd in found_commands:
            if cmd.lower() not in allowed_commands:
                return (
                    False,
                    f"Command '{cmd}' is not in the allowed commands list.",
                )
        return True, ""

    # Check for dangerous commands
    for cmd in dangerous_commands:
        pattern = rf'(?:^|;|\||&&)\s*\b{re.escape(cmd)}\b'
        if re.search(pattern, clean_command, re.IGNORECASE):
            return False, f"Command '{cmd}' is blocked for safety."

    return True, ""


def sanitize_command(
    command: str,
    use_docker_backend: bool = False,
    safe_mode: bool = True,
    working_dir: Optional[str] = None,
    allowed_commands: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    r"""A comprehensive command sanitizer for both local and Docker backends.

    Args:
        command (str): The command to sanitize
        use_docker_backend (bool): Whether using Docker backend
        safe_mode (bool): Whether to apply security checks
        working_dir (Optional[str]): Working directory for path validation
        allowed_commands (Optional[Set[str]]): Set of allowed commands

    Returns:
        Tuple[bool, str]: (is_safe, message_or_command)
    """
    if not safe_mode:
        return True, command  # Skip all checks if safe_mode is disabled

    # Use safety checker
    is_safe, reason = check_command_safety(command, allowed_commands)
    if not is_safe:
        return False, reason

    # Additional check for Docker backend: prevent cd outside working directory
    if not use_docker_backend and working_dir and 'cd ' in command:
        # Extract cd commands and check their targets
        cd_pattern = r'\bcd\s+([^\s;|&]+)'
        for match in re.finditer(cd_pattern, command):
            target_path = match.group(1).strip('\'"')
            target_dir = os.path.abspath(
                os.path.join(working_dir, target_path)
            )
            if not target_dir.startswith(working_dir):
                return False, "Cannot 'cd' outside of the working directory."

    return True, command


# Environment management utilities


def is_uv_environment() -> bool:
    r"""Detect whether the current Python runtime is managed by uv."""
    return (
        "UV_CACHE_DIR" in os.environ
        or "uv" in sys.executable
        or shutil.which("uv") is not None
    )


def ensure_uv_available(update_callback=None) -> Tuple[bool, Optional[str]]:
    r"""Ensure uv is available, installing it if necessary.

    Args:
        update_callback: Optional callback function to receive status updates

    Returns:
        Tuple[bool, Optional[str]]: (success, uv_path)
    """
    # Check if uv is already available
    existing_uv = shutil.which("uv")
    if existing_uv is not None:
        if update_callback:
            update_callback(f"uv is already available at: {existing_uv}\n")
        return True, existing_uv

    try:
        if update_callback:
            update_callback("uv not found, installing...\n")

        os_type = platform.system()

        # Install uv using the official installer script
        if os_type in ['darwin', 'linux'] or os_type.startswith('linux'):
            # Use curl to download and execute the installer
            install_cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                if update_callback:
                    update_callback(f"Failed to install uv: {result.stderr}\n")
                return False, None

            # Check if uv was installed in the expected location
            home = os.path.expanduser("~")
            uv_bin_path = os.path.join(home, ".cargo", "bin")
            uv_executable = os.path.join(uv_bin_path, "uv")

            if os.path.exists(uv_executable):
                if update_callback:
                    update_callback(
                        f"uv installed successfully at: {uv_executable}\n"
                    )
                return True, uv_executable

        elif os_type == 'Windows':
            # Use PowerShell to install uv on Windows
            install_cmd = (
                "powershell -ExecutionPolicy Bypass -c "
                "\"irm https://astral.sh/uv/install.ps1 | iex\""
            )
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                if update_callback:
                    update_callback(f"Failed to install uv: {result.stderr}\n")
                return False, None

            # Check if uv was installed in the expected location on Windows
            home = os.path.expanduser("~")
            uv_bin_path = os.path.join(home, ".cargo", "bin")
            uv_executable = os.path.join(uv_bin_path, "uv.exe")

            if os.path.exists(uv_executable):
                if update_callback:
                    update_callback(
                        f"uv installed successfully at: {uv_executable}\n"
                    )
                return True, uv_executable

        if update_callback:
            update_callback("Failed to verify uv installation\n")
        return False, None

    except Exception as e:
        if update_callback:
            update_callback(f"Error installing uv: {e!s}\n")
        logger.error(f"Failed to install uv: {e}")
        return False, None


def setup_initial_env_with_uv(
    env_path: str, uv_path: str, working_dir: str, update_callback=None
) -> bool:
    r"""Set up initial environment using uv."""
    try:
        # Create virtual environment with Python 3.10 using uv
        subprocess.run(
            [uv_path, "venv", "--python", "3.10", env_path],
            check=True,
            capture_output=True,
            cwd=working_dir,
            timeout=300,
        )

        # Get the python path from the new environment
        if platform.system() == 'Windows':
            python_path = os.path.join(env_path, "Scripts", "python.exe")
        else:
            python_path = os.path.join(env_path, "bin", "python")

        # Install essential packages using uv
        essential_packages = [
            "pip",
            "setuptools",
            "wheel",
            "pyautogui",
            "plotly",
        ]
        subprocess.run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                python_path,
                *essential_packages,
            ],
            check=True,
            capture_output=True,
            cwd=working_dir,
            timeout=300,
        )

        if update_callback:
            update_callback(
                "[UV] Initial environment created with Python 3.10 "
                "and essential packages"
            )
        return True

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if update_callback:
            update_callback(f"UV setup failed: {error_msg}\n")
        return False
    except subprocess.TimeoutExpired:
        if update_callback:
            update_callback("UV setup timed out after 5 minutes\n")
        return False


def setup_initial_env_with_venv(
    env_path: str, working_dir: str, update_callback=None
) -> bool:
    r"""Set up initial environment using standard venv."""
    try:
        # Create virtual environment with system Python
        venv.create(
            env_path, with_pip=True, system_site_packages=False, symlinks=False
        )

        # Get pip path
        if platform.system() == 'Windows':
            pip_path = os.path.join(env_path, "Scripts", "pip.exe")
        else:
            pip_path = os.path.join(env_path, "bin", "pip")

        # Upgrade pip and install essential packages
        essential_packages = [
            "pip",
            "setuptools",
            "wheel",
            "pyautogui",
            "plotly",
        ]
        subprocess.run(
            [pip_path, "install", "--upgrade", *essential_packages],
            check=True,
            capture_output=True,
            cwd=working_dir,
            timeout=300,
        )

        if update_callback:
            update_callback(
                "Initial environment created with system Python "
                "and essential packages"
            )
        return True

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if update_callback:
            update_callback(f"Venv setup failed: {error_msg}\n")
        return False
    except subprocess.TimeoutExpired:
        if update_callback:
            update_callback("Venv setup timed out after 5 minutes\n")
        return False


def clone_current_environment(
    env_path: str, working_dir: str, update_callback=None
) -> bool:
    r"""Create a new Python virtual environment, optionally using uv."""
    try:
        if os.path.exists(env_path):
            if update_callback:
                update_callback(f"Using existing environment: {env_path}\n")
            return True

        if update_callback:
            update_callback(
                f"Creating new Python environment at: {env_path}\n"
            )

        # Try to use uv if available
        success, uv_path = ensure_uv_available(update_callback)
        if success and uv_path:
            # Get current Python version
            current_version = (
                f"{sys.version_info.major}.{sys.version_info.minor}"
            )

            subprocess.run(
                [uv_path, "venv", "--python", current_version, env_path],
                check=True,
                capture_output=True,
                cwd=working_dir,
                timeout=300,
            )

            # Get the python path from the new environment
            if platform.system() == 'Windows':
                python_path = os.path.join(env_path, "Scripts", "python.exe")
            else:
                python_path = os.path.join(env_path, "bin", "python")

            # Install pip and setuptools using uv
            subprocess.run(
                [
                    uv_path,
                    "pip",
                    "install",
                    "--python",
                    python_path,
                    "pip",
                    "setuptools",
                    "wheel",
                ],
                check=True,
                capture_output=True,
                cwd=working_dir,
                timeout=300,
            )

            if update_callback:
                update_callback(
                    "[UV] Cloned Python environment created successfully!\n"
                )
            return True
        else:
            # Fallback to standard venv
            if update_callback:
                update_callback(
                    "Falling back to standard venv for cloning environment\n"
                )

            venv.create(env_path, with_pip=True, symlinks=False)

            # Ensure pip is properly available
            if platform.system() == 'Windows':
                python_path = os.path.join(env_path, "Scripts", "python.exe")
            else:
                python_path = os.path.join(env_path, "bin", "python")

            if os.path.exists(python_path):
                subprocess.run(
                    [python_path, "-m", "pip", "install", "--upgrade", "pip"],
                    check=True,
                    capture_output=True,
                    cwd=working_dir,
                    timeout=60,
                )
                if update_callback:
                    update_callback(
                        "New Python environment created successfully with pip!"
                    )
            else:
                if update_callback:
                    update_callback(
                        f"Warning: Python executable not found at "
                        f"{python_path}"
                    )
            return True

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if update_callback:
            update_callback(f"Failed to create environment: {error_msg}\n")
        logger.error(f"Failed to create environment: {error_msg}")
        return False
    except subprocess.TimeoutExpired:
        if update_callback:
            update_callback("Environment creation timed out\n")
        return False
    except Exception as e:
        if update_callback:
            update_callback(f"Failed to create environment: {e!s}\n")
        logger.error(f"Failed to create environment: {e}")
        return False


def check_nodejs_availability(update_callback=None) -> Tuple[bool, str]:
    r"""Check if Node.js is available without modifying the system."""
    try:
        # Check if Node.js is already available in the system
        node_result = subprocess.run(
            ["node", "--version"],
            check=False,
            capture_output=True,
            timeout=10,
        )

        npm_result = subprocess.run(
            ["npm", "--version"],
            check=False,
            capture_output=True,
            timeout=10,
        )

        if node_result.returncode == 0 and npm_result.returncode == 0:
            node_version = node_result.stdout.decode().strip()
            npm_version = npm_result.stdout.decode().strip()
            info = (
                f"Node.js {node_version} and npm {npm_version} are available"
            )
            if update_callback:
                update_callback(f"{info}\n")
            return True, info
        else:
            info = "Node.js not found. If needed, please install it manually."
            if update_callback:
                update_callback(f"Note: {info}\n")
            return False, info

    except Exception as e:
        info = f"Could not check Node.js availability - {e}"
        if update_callback:
            update_callback(f"Note: {info}.\n")
        logger.warning(f"Failed to check Node.js: {e}")
        return False, info
