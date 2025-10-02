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
import shutil
import subprocess
from typing import Optional, Tuple

from camel.logger import get_logger

logger = get_logger(__name__)


def find_command(
    cmd_base: str,
    windows_variants: Optional[list] = None,
    unix_variant: Optional[str] = None,
) -> Optional[str]:
    """Find command across platforms."""
    is_windows = platform.system() == 'Windows'

    if is_windows and windows_variants:
        for variant in windows_variants:
            if shutil.which(variant):
                return variant
    else:
        variant = unix_variant or cmd_base
        if shutil.which(variant):
            return variant

    if shutil.which(cmd_base):
        return cmd_base
    return None


def create_command_not_found_error(
    command: str, error: Optional[Exception] = None
) -> RuntimeError:
    base_msg = f"{command} is not installed or not in PATH. "
    if command in ['npm', 'node']:
        base_msg += (
            f"Please install Node.js{' and npm' if command == 'npm' else ''} "
            f"from https://nodejs.org/ to use the hybrid browser toolkit."
        )
        if not error:
            base_msg += (
                " If already installed, ensure the Node.js installation "
                "directory (e.g., C:\\Program Files\\nodejs on Windows) is "
                "in your system PATH."
            )
    if error:
        base_msg += f" Error details: {error!s}"
    return RuntimeError(base_msg)


def create_npm_command_error(command: str, error: Exception) -> RuntimeError:
    return RuntimeError(
        f"Failed to run {command}: {error!s}. "
        f"Please ensure npm is properly installed and in PATH."
    )


async def check_and_install_dependencies(ts_dir: str) -> Tuple[str, str]:
    """Check Node.js/npm and install dependencies if needed.

    Returns:
        Tuple of (npm_cmd, node_cmd) that can be used for running commands
    """
    is_windows = platform.system() == 'Windows'
    use_shell = is_windows

    npm_cmd = find_command('npm', windows_variants=['npm.cmd', 'npm.exe'])
    if not npm_cmd:
        raise create_command_not_found_error('npm')

    try:
        npm_check = subprocess.run(
            [npm_cmd, '--version'],
            capture_output=True,
            text=True,
            shell=use_shell,
        )
        if npm_check.returncode != 0:
            raise RuntimeError(
                f"npm command failed with error: {npm_check.stderr}. "
                "Please ensure Node.js and npm are properly installed."
            )
    except (FileNotFoundError, OSError) as e:
        raise create_command_not_found_error('npm', e)

    node_cmd = find_command('node', windows_variants=['node.exe'])
    if not node_cmd:
        raise create_command_not_found_error('node')

    try:
        node_check = subprocess.run(
            [node_cmd, '--version'],
            capture_output=True,
            text=True,
            shell=use_shell,
        )
        if node_check.returncode != 0:
            raise RuntimeError(
                f"node command failed with error: {node_check.stderr}. "
                "Please ensure Node.js is properly installed."
            )
    except (FileNotFoundError, OSError) as e:
        raise create_command_not_found_error('node', e)

    node_modules_path = os.path.join(ts_dir, 'node_modules')
    if not os.path.exists(node_modules_path):
        logger.warning("Node modules not found. Running npm install...")
        try:
            install_result = subprocess.run(
                [npm_cmd, 'install'],
                cwd=ts_dir,
                capture_output=True,
                text=True,
                shell=use_shell,
            )
            if install_result.returncode != 0:
                logger.error(f"npm install failed: {install_result.stderr}")
                raise RuntimeError(
                    f"Failed to install npm dependencies: {install_result.stderr}\n"  # noqa:E501
                    f"Please run 'npm install' in {ts_dir} manually."
                )
        except (FileNotFoundError, OSError) as e:
            raise create_npm_command_error("npm install", e)
        logger.info("npm dependencies installed successfully")

    dist_dir = os.path.join(ts_dir, 'dist')
    if not os.path.exists(dist_dir) or not os.listdir(dist_dir):
        logger.info("Building TypeScript...")
        try:
            build_result = subprocess.run(
                [npm_cmd, 'run', 'build'],
                cwd=ts_dir,
                capture_output=True,
                text=True,
                shell=use_shell,
            )
            if build_result.returncode != 0:
                logger.error(f"TypeScript build failed: {build_result.stderr}")
                raise RuntimeError(
                    f"TypeScript build failed: {build_result.stderr}"
                )
            logger.info("TypeScript build completed successfully")
        except (FileNotFoundError, OSError) as e:
            raise create_npm_command_error("npm run build", e)
    else:
        logger.info("TypeScript already built, skipping build")

    playwright_marker = os.path.join(ts_dir, '.playwright_installed')
    if not os.path.exists(playwright_marker):
        logger.info("Installing Playwright browsers...")
        npx_cmd = find_command('npx', windows_variants=['npx.cmd', 'npx.exe'])
        if not npx_cmd:
            logger.warning(
                "npx not found. Skipping Playwright browser installation. "
                "Users may need to run 'npx playwright install' manually."
            )
        else:
            try:
                playwright_install = subprocess.run(
                    [npx_cmd, 'playwright', 'install'],
                    cwd=ts_dir,
                    capture_output=True,
                    text=True,
                    shell=use_shell,
                )
                if playwright_install.returncode == 0:
                    logger.info("Playwright browsers installed successfully")
                    with open(playwright_marker, 'w') as f:
                        f.write('installed')
                else:
                    logger.warning(
                        f"Playwright browser installation failed: "
                        f"{playwright_install.stderr}"
                    )
                    logger.warning(
                        "Users may need to run 'npx playwright install' "
                        "manually"
                    )
            except (FileNotFoundError, OSError) as e:
                logger.warning(
                    f"Failed to install Playwright browsers: {e!s}. "
                    f"Users may need to run 'npx playwright install' "
                    f"manually"
                )

    return npm_cmd, node_cmd
