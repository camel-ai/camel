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

r"""Java runtime auto-installation utilities.

This module provides functionality to detect, download, and configure
the Java (JDK) runtime. If Java is not already available on the
system, Eclipse Temurin (Adoptium) JDK 21 LTS is downloaded and
extracted to ``~/.camel/runtimes/java/``.
"""

import os
import shutil
import subprocess
from typing import Optional

from camel.logger import get_logger

from .runtime_utils import (
    ADOPTIUM_DOWNLOAD_URL_TEMPLATE,
    JAVA_VERSION,
    RUNTIMES_DIR,
    ArchiveType,
    RuntimeDownloadError,
    RuntimeExtractionError,
    RuntimeInstallError,
    SupportedOS,
    UpdateCallback,
    download_and_extract_runtime,
    get_platform_info,
)

logger = get_logger(__name__)


def ensure_java_available(
    update_callback: UpdateCallback = None,
) -> Optional[str]:
    r"""Ensure Java (JDK) is available, downloading if necessary.

    Checks if Java is already installed on the system. If not,
    downloads Eclipse Temurin (Adoptium) JDK 21 LTS for the current
    platform and extracts it to ``~/.camel/runtimes/java/``.

    Args:
        update_callback (Callable[[str], None], optional): Callback
            function to receive status updates.
            (default: :obj:`None`)

    Returns:
        Optional[str]: The JAVA_HOME directory path, or ``None``
            if Java could not be made available.
    """
    # Check if Java is already available on PATH
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
            version_output = (
                result.stderr.strip() or result.stdout.strip()
            )
            if result.returncode == 0:
                info = (
                    f"Java is already available: "
                    f"{version_output}"
                )
                if update_callback:
                    update_callback(f"{info}\n")
                return os.path.dirname(
                    os.path.dirname(existing_java)
                )
        except Exception:
            pass

    # Java not found, attempt auto-install
    if update_callback:
        update_callback(
            f"Java not found, installing Adoptium Temurin "
            f"JDK {JAVA_VERSION} LTS...\n"
        )

    try:
        os_name, arch = get_platform_info()
    except RuntimeError as e:
        if update_callback:
            update_callback(
                f"Cannot auto-install Java: {e}\n"
            )
        return None

    # Map arch/OS names for Adoptium API
    adoptium_arch = "x64" if arch == "amd64" else arch
    adoptium_os = "mac" if os_name == "darwin" else os_name

    # Construct Adoptium API URL from template
    url = ADOPTIUM_DOWNLOAD_URL_TEMPLATE.format(
        version=JAVA_VERSION,
        os_name=adoptium_os,
        arch=adoptium_arch,
    )

    java_runtime_dir = os.path.join(RUNTIMES_DIR, "java")
    archive_type: ArchiveType = (
        "zip" if os_name == "windows" else "tar.gz"
    )

    # Check if already downloaded
    java_home = _find_java_home(java_runtime_dir, os_name)
    if java_home:
        info = (
            f"Java JDK is already installed at {java_home}"
        )
        if update_callback:
            update_callback(f"{info}\n")
        return java_home

    try:
        download_and_extract_runtime(
            url=url,
            target_dir=java_runtime_dir,
            archive_type=archive_type,
            update_callback=update_callback,
        )
    except (
        RuntimeDownloadError,
        RuntimeExtractionError,
        RuntimeInstallError,
    ) as e:
        logger.error(f"Failed to install Java: {e}")
        if update_callback:
            update_callback(f"Failed to install Java: {e}\n")
        return None

    java_home = _find_java_home(java_runtime_dir, os_name)
    if java_home:
        if update_callback:
            update_callback(
                f"Adoptium Temurin JDK {JAVA_VERSION} installed "
                f"successfully at {java_home}\n"
            )
        return java_home

    if update_callback:
        update_callback(
            "Failed to install Java. "
            "If needed, please install it manually.\n"
        )
    return None


def _find_java_home(
    java_runtime_dir: str, os_name: SupportedOS
) -> Optional[str]:
    r"""Find the JAVA_HOME directory within the runtime directory.

    Adoptium extracts to a versioned directory like
    ``jdk-21.0.x+y/``. This helper scans for it.

    Args:
        java_runtime_dir (str): The parent directory where Java was
            extracted.
        os_name (SupportedOS): The operating system name.

    Returns:
        Optional[str]: The path to JAVA_HOME, or None if not found.
    """
    if not os.path.exists(java_runtime_dir):
        return None

    java_executable = (
        "java.exe" if os_name == "windows" else "java"
    )

    for entry in os.listdir(java_runtime_dir):
        entry_path = os.path.join(java_runtime_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        # On macOS, the structure is
        # jdk-xxx/Contents/Home/bin/java
        if os_name == "darwin":
            java_path = os.path.join(
                entry_path,
                "Contents",
                "Home",
                "bin",
                java_executable,
            )
            if os.path.exists(java_path):
                return os.path.join(
                    entry_path, "Contents", "Home"
                )

        # On Linux/Windows, the structure is jdk-xxx/bin/java
        java_path = os.path.join(
            entry_path, "bin", java_executable
        )
        if os.path.exists(java_path):
            return entry_path

    return None
