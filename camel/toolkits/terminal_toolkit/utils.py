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

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import venv
from typing import List, Optional, Set, Tuple

from camel.logger import get_logger

logger = get_logger(__name__)

# Pre-compiled regex patterns for command safety checks
_CMD_PATTERN = re.compile(
    r'(?:^|;|\||&&)\s*\b([a-zA-Z_/][\w\-/]*)', re.IGNORECASE
)
_QUOTED_STRING_PATTERN = re.compile(r'''["'][^"']*["']''')
# Match cd command with optional quoted or unquoted path
# Handles: cd path, cd "path with spaces", cd 'path with spaces'
_CD_PATTERN = re.compile(r'\bcd\s+(["\'][^"\']*["\']|[^\s;|&]+)')
_SHELL_SUBSTITUTION_PATTERN = re.compile(r'`|(?<!\\)\$\(')
_SHELL_COMMANDS = {'bash', 'sh', 'zsh', 'dash', 'ksh', 'ash'}
_SEPARATORS = {';', '&&', '||', '|', '&'}
_CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE = (
    "Cannot 'cd' outside of the working directory in safe mode. "
    "Allowed root: '{working_dir}'. "
    "To modify files there, copy them (for example with `cp`) "
    "into '{working_dir}' first."
)

# Public list for downstream customization/import.
DANGEROUS_COMMANDS: List[str] = [
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


def _normalize_command_name(command: str) -> str:
    r"""Normalize command names for safer matching."""
    normalized = os.path.basename(command).lower()
    if normalized.endswith('.exe'):
        normalized = normalized[:-4]
    return normalized


def _split_command_segments(command: str) -> Optional[List[List[str]]]:
    r"""Split command by shell separators while preserving quoted content."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|')
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None

    segments: List[List[str]] = []
    current: List[str] = []
    for token in tokens:
        if token in _SEPARATORS:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def _extract_shell_c_payloads(command: str) -> List[str]:
    r"""Extract payloads from shell wrapper commands like `bash -c "<cmd>"`."""
    segments = _split_command_segments(command)
    if segments is None:
        return []

    payloads: List[str] = []
    for segment in segments:
        if not segment:
            continue

        if _normalize_command_name(segment[0]) not in _SHELL_COMMANDS:
            continue

        args = segment[1:]
        for i, arg in enumerate(args):
            is_explicit_c = arg in {'-c', '--command'}
            is_combined_short_flag = (
                arg.startswith('-')
                and not arg.startswith('--')
                and 'c' in arg[1:]
            )
            if is_explicit_c or is_combined_short_flag:
                if i + 1 < len(args):
                    payloads.append(args[i + 1])
                break

    return payloads


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

    # Recursively inspect shell-wrapper payloads to prevent bypasses such as
    # `bash -c "rm -rf /"` where the dangerous sub-command is quoted.
    for payload in _extract_shell_c_payloads(command):
        is_safe, reason = check_command_safety(payload, allowed_commands)
        if not is_safe:
            return False, reason

    # Remove quoted strings to avoid false positives
    clean_command = _QUOTED_STRING_PATTERN.sub(' ', command)

    # If whitelist mode, check ALL commands against the whitelist
    if allowed_commands is not None:
        # Extract all command words (at start or after operators)
        found_commands = _CMD_PATTERN.findall(clean_command)
        for cmd in found_commands:
            if cmd.lower() not in allowed_commands:
                return (
                    False,
                    f"Command '{cmd}' is not in the allowed commands list.",
                )
        return True, ""

    # Check for dangerous commands
    for cmd in DANGEROUS_COMMANDS:
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

    # Additional check for local backend: prevent cd outside working directory
    if not use_docker_backend and working_dir and 'cd ' in command:
        # Extract cd commands and check their targets
        # Normalize working_dir to ensure consistent comparison
        normalized_working_dir = os.path.normpath(os.path.abspath(working_dir))
        current_dir = normalized_working_dir
        for match in _CD_PATTERN.finditer(command):
            target_path = match.group(1).strip('\'"')
            if _SHELL_SUBSTITUTION_PATTERN.search(target_path):
                return (
                    False,
                    "Command substitution is not allowed in 'cd' paths.",
                )

            expanded_target = os.path.expanduser(
                os.path.expandvars(target_path)
            )
            if os.path.isabs(expanded_target):
                resolved_target = expanded_target
            else:
                resolved_target = os.path.join(current_dir, expanded_target)

            target_dir = os.path.normpath(os.path.abspath(resolved_target))
            # Use os.path.commonpath for safe path comparison
            try:
                common = os.path.commonpath(
                    [normalized_working_dir, target_dir]
                )
                if common != normalized_working_dir:
                    return (
                        False,
                        _CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE.format(
                            working_dir=normalized_working_dir
                        ),
                    )
                current_dir = target_dir
            except ValueError:
                # Different drives on Windows or other path issues
                return (
                    False,
                    _CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE.format(
                        working_dir=normalized_working_dir
                    ),
                )

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
        if os_type.lower() in [
            'darwin',
            'linux',
        ] or os_type.lower().startswith('linux'):
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

        elif os_type.lower() == 'windows':
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
        if platform.system() == 'Windows':
            python_path = os.path.join(env_path, "Scripts", "python.exe")
        else:
            python_path = os.path.join(env_path, "bin", "python")

        if os.path.exists(python_path):
            if update_callback:
                update_callback(
                    "[UV] Environment already exists, skipping creation\n"
                )
            return True
        # Create virtual environment with Python 3.10 using uv
        subprocess.run(
            [uv_path, "venv", "--python", "3.10", env_path],
            check=True,
            capture_output=True,
            cwd=working_dir,
            timeout=300,
        )

        # Install essential packages using uv
        essential_packages = [
            "pip",
            "setuptools",
            "wheel",
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
        # Get pip path
        if platform.system() == 'Windows':
            pip_path = os.path.join(env_path, "Scripts", "pip.exe")
        else:
            pip_path = os.path.join(env_path, "bin", "pip")

        # Check if environment already exists
        if os.path.exists(pip_path):
            if update_callback:
                update_callback(
                    "Environment already exists, skipping creation\n"
                )
            return True

        # Create virtual environment with system Python
        try:
            venv.create(
                env_path,
                with_pip=True,
                system_site_packages=False,
                symlinks=True,
            )
        except Exception:
            # Clean up partial environment
            if os.path.exists(env_path):
                shutil.rmtree(env_path)
            # Fallback to symlinks=False if symlinks=True fails
            # (e.g., on some Windows configurations or macOS Beta)
            venv.create(
                env_path,
                with_pip=True,
                system_site_packages=False,
                symlinks=False,
            )

        # Upgrade pip and install essential packages
        essential_packages = [
            "pip",
            "setuptools",
            "wheel",
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
    r"""Clone the current Python environment to a new virtual environment.

    This function creates a new virtual environment with the same Python
    version as the current environment and installs all packages from
    the current environment.

    Args:
        env_path: Path where the new environment will be created.
        working_dir: Working directory for subprocess commands.
        update_callback: Optional callback for status updates.

    Returns:
        True if the environment was created successfully, False otherwise.
    """
    try:
        if os.path.exists(env_path):
            if update_callback:
                update_callback(f"Using existing environment: {env_path}\n")
            return True

        if update_callback:
            update_callback(
                f"Cloning current Python environment to: {env_path}\n"
            )

        # Get current Python version
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # Get list of installed packages in current environment
        if update_callback:
            update_callback("Collecting installed packages...\n")

        freeze_result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if freeze_result.returncode != 0:
            if update_callback:
                update_callback(
                    "Warning: Failed to get installed packages, "
                    "creating empty environment\n"
                )
            installed_packages = ""
        else:
            installed_packages = freeze_result.stdout.strip()

        # Try to use uv if available
        success, uv_path = ensure_uv_available(update_callback)

        if success and uv_path:
            # Create venv with uv
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

            # Install pip, setuptools, wheel first
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

            # Install cloned packages if any
            if installed_packages:
                if update_callback:
                    update_callback("Installing cloned packages with uv...\n")
                # Write requirements to temp file (auto-deleted)
                fd, requirements_file = tempfile.mkstemp(
                    suffix=".txt", prefix="requirements_", dir=working_dir
                )
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(installed_packages)
                    subprocess.run(
                        [
                            uv_path,
                            "pip",
                            "install",
                            "--python",
                            python_path,
                            "-r",
                            requirements_file,
                        ],
                        check=True,
                        capture_output=True,
                        cwd=working_dir,
                        timeout=600,
                    )
                finally:
                    if os.path.exists(requirements_file):
                        os.remove(requirements_file)

            if update_callback:
                update_callback("[UV] Environment cloned successfully!\n")
            return True
        else:
            # Fallback to standard venv
            if update_callback:
                update_callback(
                    "Falling back to standard venv for cloning environment\n"
                )
            try:
                venv.create(env_path, with_pip=True, symlinks=True)
            except Exception:
                # Clean up partial environment
                if os.path.exists(env_path):
                    shutil.rmtree(env_path)
                # Fallback to symlinks=False if symlinks=True fails
                venv.create(env_path, with_pip=True, symlinks=False)

            # Get python/pip path
            if platform.system() == 'Windows':
                python_path = os.path.join(env_path, "Scripts", "python.exe")
            else:
                python_path = os.path.join(env_path, "bin", "python")

            if not os.path.exists(python_path):
                if update_callback:
                    update_callback(
                        f"Warning: Python executable not found at "
                        f"{python_path}\n"
                    )
                return False

            # Upgrade pip
            subprocess.run(
                [python_path, "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                cwd=working_dir,
                timeout=60,
            )

            # Install cloned packages if any
            if installed_packages:
                if update_callback:
                    update_callback("Installing cloned packages with pip...\n")
                # Write requirements to temp file (auto-deleted)
                fd, requirements_file = tempfile.mkstemp(
                    suffix=".txt", prefix="requirements_", dir=working_dir
                )
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(installed_packages)
                    subprocess.run(
                        [
                            python_path,
                            "-m",
                            "pip",
                            "install",
                            "-r",
                            requirements_file,
                        ],
                        check=True,
                        capture_output=True,
                        cwd=working_dir,
                        timeout=600,
                    )
                finally:
                    if os.path.exists(requirements_file):
                        os.remove(requirements_file)

            if update_callback:
                update_callback("Environment cloned successfully!\n")
            return True

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if update_callback:
            update_callback(f"Failed to clone environment: {error_msg}\n")
        logger.error(f"Failed to clone environment: {error_msg}")
        return False
    except subprocess.TimeoutExpired:
        if update_callback:
            update_callback("Environment cloning timed out\n")
        return False
    except Exception as e:
        if update_callback:
            update_callback(f"Failed to clone environment: {e!s}\n")
        logger.error(f"Failed to clone environment: {e}")
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
