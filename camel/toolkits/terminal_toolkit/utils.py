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

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import venv
import zipfile
from typing import Optional, Set, Tuple

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

    # Additional check for local backend: prevent cd outside working directory
    if not use_docker_backend and working_dir and 'cd ' in command:
        # Extract cd commands and check their targets
        # Normalize working_dir to ensure consistent comparison
        normalized_working_dir = os.path.normpath(os.path.abspath(working_dir))
        for match in _CD_PATTERN.finditer(command):
            target_path = match.group(1).strip('\'"')
            target_dir = os.path.normpath(
                os.path.abspath(os.path.join(working_dir, target_path))
            )
            # Use os.path.commonpath for safe path comparison
            try:
                common = os.path.commonpath(
                    [normalized_working_dir, target_dir]
                )
                if common != normalized_working_dir:
                    return (
                        False,
                        "Cannot 'cd' outside of the working directory.",
                    )
            except ValueError:
                # Different drives on Windows or other path issues
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


# Runtime auto-install utilities

# Pinned stable versions for auto-install
_GO_VERSION = "1.23.6"
_JAVA_VERSION = "21"
_RUNTIMES_DIR = os.path.join(os.path.expanduser("~"), ".camel", "runtimes")


def _get_platform_info() -> Tuple[str, str]:
    r"""Detect the current OS and architecture for binary downloads.

    Returns:
        Tuple[str, str]: (os_name, arch) suitable for download URLs.
            os_name: 'linux', 'darwin', or 'windows'
            arch: 'amd64' or 'arm64'

    Raises:
        RuntimeError: If the OS or architecture is unsupported.
    """
    os_name = platform.system().lower()
    if os_name not in ('linux', 'darwin', 'windows'):
        raise RuntimeError(f"Unsupported operating system: {os_name}")

    machine = platform.machine().lower()
    arch_map = {
        'x86_64': 'amd64',
        'amd64': 'amd64',
        'aarch64': 'arm64',
        'arm64': 'arm64',
    }
    arch = arch_map.get(machine)
    if arch is None:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    return os_name, arch


def _download_and_extract_runtime(
    url: str,
    target_dir: str,
    archive_type: str = "tar.gz",
    checksum_url: Optional[str] = None,
    update_callback=None,
) -> bool:
    r"""Download and extract a runtime binary archive.

    Args:
        url (str): URL of the archive to download.
        target_dir (str): Directory to extract the archive into.
        archive_type (str): Type of archive - 'tar.gz' or 'zip'.
            (default: :obj:`tar.gz`)
        checksum_url (Optional[str]): URL to a SHA256 checksum file for
            verification. (default: :obj:`None`)
        update_callback: Optional callback function to receive status
            updates.

    Returns:
        bool: True if download and extraction succeeded, False otherwise.
    """
    tmp_file = None
    try:
        os.makedirs(target_dir, exist_ok=True)

        # Download to a temporary file
        suffix = ".tar.gz" if archive_type == "tar.gz" else ".zip"
        fd, tmp_file = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        if update_callback:
            update_callback(f"Downloading from {url}...\n")

        # Use a proper User-Agent header to avoid 403 errors
        # from CDNs that block Python's default User-Agent
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "camel-ai/runtime-installer"},
        )
        with urllib.request.urlopen(req) as response:
            with open(tmp_file, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

        # Verify checksum if provided
        if checksum_url:
            try:
                if update_callback:
                    update_callback("Verifying checksum...\n")
                with urllib.request.urlopen(checksum_url) as response:
                    checksum_data = response.read().decode('utf-8')

                # Calculate SHA256 of downloaded file
                sha256 = hashlib.sha256()
                with open(tmp_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        sha256.update(chunk)
                actual_hash = sha256.hexdigest()

                # Check if our hash is in the checksum data
                if actual_hash not in checksum_data:
                    if update_callback:
                        update_callback(
                            "Checksum verification failed! "
                            "Download may be corrupted.\n"
                        )
                    return False

                if update_callback:
                    update_callback("Checksum verified successfully.\n")
            except Exception as e:
                # Log warning but don't fail the install
                logger.warning(f"Checksum verification skipped: {e}")
                if update_callback:
                    update_callback(
                        f"Warning: Checksum verification skipped: {e}\n"
                    )

        # Extract the archive
        if update_callback:
            update_callback(f"Extracting to {target_dir}...\n")

        if archive_type == "tar.gz":
            with tarfile.open(tmp_file, 'r:gz') as tar:
                tar.extractall(path=target_dir)
        elif archive_type == "zip":
            with zipfile.ZipFile(tmp_file, 'r') as zf:
                zf.extractall(path=target_dir)
        else:
            if update_callback:
                update_callback(f"Unsupported archive type: {archive_type}\n")
            return False

        return True

    except urllib.error.URLError as e:
        if update_callback:
            update_callback(f"Download failed: {e}\n")
        logger.error(f"Failed to download runtime: {e}")
        return False
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        if update_callback:
            update_callback(f"Extraction failed: {e}\n")
        logger.error(f"Failed to extract runtime archive: {e}")
        return False
    except Exception as e:
        if update_callback:
            update_callback(f"Runtime installation failed: {e}\n")
        logger.error(f"Failed to install runtime: {e}")
        return False
    finally:
        # Clean up temp file
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass


def ensure_go_available(
    update_callback=None,
) -> Tuple[bool, Optional[str]]:
    r"""Ensure Go is available, downloading it if necessary.

    Checks if Go is already installed on the system. If not, downloads
    the official Go binary for the current platform and extracts it to
    ``~/.camel/runtimes/go/``.

    Args:
        update_callback: Optional callback function to receive status
            updates.

    Returns:
        Tuple[bool, Optional[str]]: (success, go_bin_path) where
            go_bin_path is the path to the Go bin directory that should
            be added to PATH, or None if Go is not available.
    """
    # Check if Go is already available
    existing_go = shutil.which("go")
    if existing_go is not None:
        try:
            result = subprocess.run(
                ["go", "version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version_info = result.stdout.strip()
                info = f"Go is already available: {version_info}"
                if update_callback:
                    update_callback(f"{info}\n")
                return True, os.path.dirname(existing_go)
        except Exception:
            pass

    # Go not found, attempt auto-install
    if update_callback:
        update_callback(
            f"Go not found, installing Go {_GO_VERSION}...\n"
        )

    try:
        os_name, arch = _get_platform_info()
    except RuntimeError as e:
        if update_callback:
            update_callback(f"Cannot auto-install Go: {e}\n")
        return False, None

    # Construct download URL
    ext = "zip" if os_name == "windows" else "tar.gz"
    filename = f"go{_GO_VERSION}.{os_name}-{arch}.{ext}"
    url = f"https://go.dev/dl/{filename}"
    checksum_url = f"https://go.dev/dl/{filename}.sha256"

    go_runtime_dir = os.path.join(_RUNTIMES_DIR, "go")

    # Check if already downloaded
    go_bin_dir = os.path.join(go_runtime_dir, "go", "bin")
    go_executable = "go.exe" if os_name == "windows" else "go"
    if os.path.exists(os.path.join(go_bin_dir, go_executable)):
        info = (
            f"Go {_GO_VERSION} is already installed at "
            f"{go_runtime_dir}"
        )
        if update_callback:
            update_callback(f"{info}\n")
        return True, go_bin_dir

    archive_type = "zip" if os_name == "windows" else "tar.gz"
    success = _download_and_extract_runtime(
        url=url,
        target_dir=go_runtime_dir,
        archive_type=archive_type,
        checksum_url=checksum_url,
        update_callback=update_callback,
    )

    if success and os.path.exists(os.path.join(go_bin_dir, go_executable)):
        if update_callback:
            update_callback(
                f"Go {_GO_VERSION} installed successfully at "
                f"{go_runtime_dir}\n"
            )
        return True, go_bin_dir

    if update_callback:
        update_callback(
            "Failed to install Go. "
            "If needed, please install it manually.\n"
        )
    return False, None


def ensure_java_available(
    update_callback=None,
) -> Tuple[bool, Optional[str]]:
    r"""Ensure Java (JDK) is available, downloading it if necessary.

    Checks if Java is already installed on the system. If not, downloads
    Eclipse Temurin (Adoptium) JDK 21 LTS for the current platform and
    extracts it to ``~/.camel/runtimes/java/``.

    Args:
        update_callback: Optional callback function to receive status
            updates.

    Returns:
        Tuple[bool, Optional[str]]: (success, java_home_path) where
            java_home_path is the JAVA_HOME directory, or None if Java
            is not available.
    """
    # Check if Java is already available
    existing_java = shutil.which("java")
    if existing_java is not None:
        try:
            result = subprocess.run(
                ["java", "-version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # java -version outputs to stderr
            version_output = result.stderr.strip() or result.stdout.strip()
            if result.returncode == 0:
                info = f"Java is already available: {version_output}"
                if update_callback:
                    update_callback(f"{info}\n")
                return True, os.path.dirname(
                    os.path.dirname(existing_java)
                )
        except Exception:
            pass

    # Java not found, attempt auto-install
    if update_callback:
        update_callback(
            f"Java not found, installing Adoptium Temurin JDK "
            f"{_JAVA_VERSION} LTS...\n"
        )

    try:
        os_name, arch = _get_platform_info()
    except RuntimeError as e:
        if update_callback:
            update_callback(f"Cannot auto-install Java: {e}\n")
        return False, None

    # Map arch names for Adoptium API
    adoptium_arch = "x64" if arch == "amd64" else arch
    # Map OS names for Adoptium API
    adoptium_os = "mac" if os_name == "darwin" else os_name

    # Construct Adoptium API URL
    url = (
        f"https://api.adoptium.net/v3/binary/latest/"
        f"{_JAVA_VERSION}/ga/{adoptium_os}/{adoptium_arch}/"
        f"jdk/hotspot/normal/eclipse"
    )

    java_runtime_dir = os.path.join(_RUNTIMES_DIR, "java")
    archive_type = "zip" if os_name == "windows" else "tar.gz"

    # Check if already downloaded by looking for java executable
    # in any subdirectory (Adoptium extracts to a versioned dir)
    java_home = _find_java_home(java_runtime_dir, os_name)
    if java_home:
        info = f"Java JDK is already installed at {java_home}"
        if update_callback:
            update_callback(f"{info}\n")
        return True, java_home

    success = _download_and_extract_runtime(
        url=url,
        target_dir=java_runtime_dir,
        archive_type=archive_type,
        update_callback=update_callback,
    )

    if success:
        java_home = _find_java_home(java_runtime_dir, os_name)
        if java_home:
            if update_callback:
                update_callback(
                    f"Adoptium Temurin JDK {_JAVA_VERSION} installed "
                    f"successfully at {java_home}\n"
                )
            return True, java_home

    if update_callback:
        update_callback(
            "Failed to install Java. "
            "If needed, please install it manually.\n"
        )
    return False, None


def _find_java_home(
    java_runtime_dir: str, os_name: str
) -> Optional[str]:
    r"""Find the JAVA_HOME directory within the runtime directory.

    Adoptium extracts to a versioned directory like
    ``jdk-21.0.x+y/``. This helper scans for it.

    Args:
        java_runtime_dir (str): The parent directory where Java was
            extracted.
        os_name (str): The operating system name ('linux', 'darwin',
            'windows').

    Returns:
        Optional[str]: The path to JAVA_HOME, or None if not found.
    """
    if not os.path.exists(java_runtime_dir):
        return None

    java_executable = "java.exe" if os_name == "windows" else "java"

    for entry in os.listdir(java_runtime_dir):
        entry_path = os.path.join(java_runtime_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        # On macOS, the structure is jdk-xxx/Contents/Home/bin/java
        if os_name == "darwin":
            java_path = os.path.join(
                entry_path, "Contents", "Home", "bin", java_executable
            )
            if os.path.exists(java_path):
                return os.path.join(entry_path, "Contents", "Home")

        # On Linux/Windows, the structure is jdk-xxx/bin/java
        java_path = os.path.join(entry_path, "bin", java_executable)
        if os.path.exists(java_path):
            return entry_path

    return None
