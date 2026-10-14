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

_CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE = (
    "Cannot 'cd' outside of the working directory in safe mode. "
    "Allowed root: '{working_dir}'. "
    "To modify files there, copy them (for example with `cp`) "
    "into '{working_dir}' first."
)
_MULTIPLE_CD_IN_CHAIN_MESSAGE = (
    "Multiple 'cd'/'pushd' commands chained with shell operators "
    "(;, &&, ||, |, &) are not allowed in safe mode, because the "
    "runtime execution flow cannot be determined statically. "
    "Please run each directory change as a separate command. "
    "For example, instead of 'cd subdir && cd ..', run 'cd subdir' "
    "first, then run subsequent commands separately."
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


_INTERPRETERS = re.compile(
    r'(?:python(?:\d+(?:\.\d+)*)?|pypy\d*|node(?:js)?|perl|ruby|'
    r'php|lua\d*|bash|sh|zsh|dash|ksh|ash|fish|csh|tcsh|'
    r'cmd|powershell|pwsh)',
    re.IGNORECASE,
)
_EXECUTION_WRAPPERS = {
    'env',
    'command',
    'exec',
    'eval',
    'source',
    'xargs',
    'nohup',
    'nice',
    'timeout',
    'setsid',
    'start',
    'call',
    'time',
    'builtin',
    'busybox',
}


def _parse_safe_segments(command: str) -> List[List[str]]:
    r"""Parse simple commands without discarding quoted command names.

    Only statically checkable shell syntax is accepted. This is deliberately
    not a general shell parser: expansion, redirects, subshells and malformed
    operators fail closed. Quoted operator characters remain literal data.
    """
    windows = platform.system() == 'Windows'
    if '\x00' in command or (windows and any(c in command for c in '%!^')):
        raise ValueError('Dynamic shell syntax is blocked for safety.')
    segments = []
    current = []
    quote = None
    index = 0
    while index < len(command):
        char = command[index]
        if char == '$' and quote is not None:
            raise ValueError('Quoted variable syntax is blocked for safety.')
        if char == '~' and quote is None and not windows:
            raise ValueError('Tilde expansion is blocked for safety.')
        if char == '\\' and not windows and quote != "'":
            if index + 1 >= len(command) or command[index + 1] in '\r\n':
                raise ValueError(
                    'Shell line continuation is blocked for safety.'
                )
            if command[index + 1] == '$':
                raise ValueError(
                    'Escaped variable syntax is blocked for safety.'
                )
            current.extend(command[index : index + 2])
            index += 2
            continue
        if char == quote:
            quote = None
        elif quote is None and (char == '"' or (char == "'" and not windows)):
            quote = char
        elif quote != "'":
            if char == '`' or command[index : index + 2] in {
                '$(',
                '${',
                '<(',
                '>(',
            }:
                raise ValueError(
                    'Command substitution or parameter expansion '
                    'is blocked for safety.'
                )
            if quote is None:
                if char in '\r\n(){}<>*?[]':
                    raise ValueError(
                        'Dynamic shell syntax or redirection '
                        'is blocked for safety.'
                    )
                if char in ';&|':
                    if not ''.join(current).strip():
                        raise ValueError(
                            'Empty command segment is blocked for safety.'
                        )
                    segments.append(''.join(current))
                    current = []
                    if command[index : index + 2] in {'&&', '||'}:
                        index += 1
                    index += 1
                    continue
        current.append(char)
        index += 1
    if quote is not None:
        raise ValueError('Unclosed shell quote is blocked for safety.')
    if not ''.join(current).strip():
        raise ValueError('Empty command segment is blocked for safety.')
    segments.append(''.join(current))
    parsed = []
    for segment in segments:
        tokens = shlex.split(segment, posix=not windows)
        if windows:
            tokens = [
                t[1:-1] if t.startswith('"') and t.endswith('"') else t
                for t in tokens
            ]
        if not tokens:
            raise ValueError('Empty command is blocked for safety.')
        parsed.append(tokens)
    return parsed


def _check_segments(
    segments: List[List[str]], allowed_commands: Optional[Set[str]]
) -> Tuple[bool, str]:
    allowed = (
        {cmd.lower() for cmd in allowed_commands}
        if allowed_commands is not None
        else None
    )
    for tokens in segments:
        executable = tokens[0]
        # Do not basename() this token: a qualified executable can bypass
        # both an allowlist and the default dangerous-command list.
        if not re.fullmatch(r'[A-Za-z_][\w.-]*', executable, re.ASCII):
            return (
                False,
                'Path-qualified or dynamic executables '
                'are blocked for safety.',
            )
        name = executable.lower()
        if platform.system() == 'Windows':
            name = name.rstrip('.')
        if name.endswith(('.bat', '.cmd', '.com')):
            return False, 'Executable script wrappers are blocked for safety.'
        name = name.removesuffix('.exe')
        if name in _EXECUTION_WRAPPERS:
            return False, f"Command '{name}' is blocked for safety."
        if _INTERPRETERS.fullmatch(name) and tokens[1:] not in [
            ['--version'],
            ['-V'],
            ['--help'],
            ['-h'],
        ]:
            return (
                False,
                f"Interpreter execution '{name}' is blocked for safety.",
            )
        if allowed is not None:
            if executable.lower() not in allowed:
                return (
                    False,
                    f"Command '{executable}' is not in "
                    'the allowed commands list.',
                )
        elif name in DANGEROUS_COMMANDS:
            return False, f"Command '{name}' is blocked for safety."
        # Variable expansion cannot be statically checked for arbitrary
        # programs. Directory changes are resolved against working_dir below.
        if name not in {'cd', 'pushd'} and any('$' in arg for arg in tokens):
            return False, 'Dynamic shell arguments are blocked for safety.'
    return True, ''


def check_command_safety(
    command: str,
    allowed_commands: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    r"""Check every simple command before shell execution.

    Interpreters and execution wrappers cannot be enabled by the allowlist
    (except interpreter version/help queries). This is a conservative command
    filter, not isolation from the behavior of an allowed program.
    """
    try:
        segments = _parse_safe_segments(command)
    except ValueError as exc:
        return False, str(exc)
    return _check_segments(segments, allowed_commands)


def _inside_workdir(path: str, working_dir: str) -> bool:
    r"""Resolve symlinks and drive boundaries before testing containment."""
    try:
        return (
            os.path.commonpath([working_dir, os.path.realpath(path)])
            == working_dir
        )
    except (ValueError, OSError):
        return False


def sanitize_command(
    command: str,
    use_docker_backend: bool = False,
    safe_mode: bool = True,
    working_dir: Optional[str] = None,
    allowed_commands: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    r"""Validate simple commands and local path arguments before execution.

    General shell expansion/redirection and arbitrary interpreter execution
    require safe_mode=False. Simple chains remain supported only when every
    command passes validation. Docker paths are not resolved on the host.
    """
    if not safe_mode:
        return True, command
    try:
        segments = _parse_safe_segments(command)
    except ValueError as exc:
        return False, str(exc)
    is_safe, reason = _check_segments(segments, allowed_commands)
    if not is_safe:
        return False, reason
    if use_docker_backend or not working_dir:
        if any('$' in arg for segment in segments for arg in segment):
            return (
                False,
                'Directory expansion requires a local working directory.',
            )
        return True, command

    root = os.path.realpath(working_dir)
    directory_changes = [
        s for s in segments if s[0].lower() in {'cd', 'pushd'}
    ]
    if len(directory_changes) > 1:
        return False, _MULTIPLE_CD_IN_CHAIN_MESSAGE

    # A preceding conditional cd may or may not succeed. Check subsequent
    # paths against every possible working directory, not only the root.
    bases = {root}
    for segment in segments:
        name, *args = segment
        if name.lower() in {'cd', 'pushd'}:
            if args[:1] == ['--']:
                args = args[1:]
            if len(args) != 1 or args[0] == '-':
                return False, _CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE.format(
                    working_dir=root
                )
            target = os.path.expandvars(args[0])
            if '$' in target or not _inside_workdir(
                os.path.join(root, target), root
            ):
                return False, _CD_OUTSIDE_WORKDIR_MESSAGE_TEMPLATE.format(
                    working_dir=root
                )
            bases.add(os.path.realpath(os.path.join(root, target)))
            continue
        for arg in args:
            # Handle ordinary operands and common --option=path forms.
            if arg.startswith('-'):
                if '=' not in arg:
                    continue
                arg = arg.split('=', 1)[1]
            if re.match(r'https?://', arg):
                continue
            target = arg
            for base in bases:
                if not _inside_workdir(os.path.join(base, target), root):
                    return (
                        False,
                        'Path argument is outside of the working directory '
                        'in safe mode.',
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
