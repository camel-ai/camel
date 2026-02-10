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

r"""Go runtime auto-installation utilities.

This module provides functionality to detect, download, and configure
the Go programming language runtime. If Go is not already available
on the system, it is downloaded from the official Go website and
extracted to ``~/.camel/runtimes/go/``.
"""

import os
import shutil
import subprocess
from typing import Optional

from camel.logger import get_logger

from .runtime_utils import (
    GO_CHECKSUM_URL_TEMPLATE,
    GO_DOWNLOAD_URL_TEMPLATE,
    GO_VERSION,
    RUNTIMES_DIR,
    ArchiveType,
    RuntimeDownloadError,
    RuntimeExtractionError,
    RuntimeInstallError,
    UpdateCallback,
    download_and_extract_runtime,
    get_platform_info,
)

logger = get_logger(__name__)


def ensure_go_available(
    update_callback: UpdateCallback = None,
) -> Optional[str]:
    r"""Ensure Go is available, downloading it if necessary.

    Checks if Go is already installed on the system. If not, downloads
    the official Go binary for the current platform and extracts it to
    ``~/.camel/runtimes/go/``.

    Args:
        update_callback (Callable[[str], None], optional): Callback
            function to receive status updates.
            (default: :obj:`None`)

    Returns:
        Optional[str]: The path to the Go ``bin`` directory that
            should be added to PATH, or ``None`` if Go could not
            be made available.
    """
    # Check if Go is already available on PATH
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
                info = (
                    f"Go is already available: {version_info}"
                )
                if update_callback:
                    update_callback(f"{info}\n")
                return os.path.dirname(existing_go)
        except Exception:
            pass

    # Go not found, attempt auto-install
    if update_callback:
        update_callback(
            f"Go not found, installing Go {GO_VERSION}...\n"
        )

    try:
        os_name, arch = get_platform_info()
    except RuntimeError as e:
        if update_callback:
            update_callback(
                f"Cannot auto-install Go: {e}\n"
            )
        return None

    # Construct download URL from template
    ext: ArchiveType = (
        "zip" if os_name == "windows" else "tar.gz"
    )
    url = GO_DOWNLOAD_URL_TEMPLATE.format(
        version=GO_VERSION, os_name=os_name, arch=arch, ext=ext,
    )
    checksum_url = GO_CHECKSUM_URL_TEMPLATE.format(
        version=GO_VERSION, os_name=os_name, arch=arch, ext=ext,
    )

    go_runtime_dir = os.path.join(RUNTIMES_DIR, "go")

    # Check if already downloaded
    go_bin_dir = os.path.join(go_runtime_dir, "go", "bin")
    go_executable = (
        "go.exe" if os_name == "windows" else "go"
    )
    if os.path.exists(os.path.join(go_bin_dir, go_executable)):
        info = (
            f"Go {GO_VERSION} is already installed at "
            f"{go_runtime_dir}"
        )
        if update_callback:
            update_callback(f"{info}\n")
        return go_bin_dir

    try:
        download_and_extract_runtime(
            url=url,
            target_dir=go_runtime_dir,
            archive_type=ext,
            checksum_url=checksum_url,
            update_callback=update_callback,
        )
    except (
        RuntimeDownloadError,
        RuntimeExtractionError,
        RuntimeInstallError,
    ) as e:
        logger.error(f"Failed to install Go: {e}")
        if update_callback:
            update_callback(f"Failed to install Go: {e}\n")
        return None

    if os.path.exists(os.path.join(go_bin_dir, go_executable)):
        if update_callback:
            update_callback(
                f"Go {GO_VERSION} installed successfully at "
                f"{go_runtime_dir}\n"
            )
        return go_bin_dir

    if update_callback:
        update_callback(
            "Failed to install Go. "
            "If needed, please install it manually.\n"
        )
    return None
