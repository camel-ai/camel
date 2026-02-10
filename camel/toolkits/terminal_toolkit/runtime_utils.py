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

r"""Shared utilities, constants, and types for runtime auto-installation.

This module provides common infrastructure used by the Go and Java
runtime installers, including platform detection, binary download
and extraction, and shared type definitions.
"""

import hashlib
import os
import platform
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from typing import Callable, Literal, Optional

from camel.logger import get_logger

logger = get_logger(__name__)

# ── Type Aliases ─────────────────────────────────────────────────────

SupportedOS = Literal["linux", "darwin", "windows"]
SupportedArch = Literal["amd64", "arm64"]
ArchiveType = Literal["tar.gz", "zip"]
UpdateCallback = Optional[Callable[[str], None]]

# ── Constants ────────────────────────────────────────────────────────

GO_VERSION = "1.23.6"
JAVA_VERSION = "21"
RUNTIMES_DIR = os.path.join(
    os.path.expanduser("~"), ".camel", "runtimes"
)

# ── URL Templates ────────────────────────────────────────────────────

GO_DOWNLOAD_URL_TEMPLATE = (
    "https://go.dev/dl/go{version}.{os_name}-{arch}.{ext}"
)
GO_CHECKSUM_URL_TEMPLATE = (
    "https://go.dev/dl/go{version}.{os_name}-{arch}.{ext}.sha256"
)
ADOPTIUM_DOWNLOAD_URL_TEMPLATE = (
    "https://api.adoptium.net/v3/binary/latest/"
    "{version}/ga/{os_name}/{arch}/jdk/hotspot/normal/eclipse"
)

# ── Architecture & OS Mappings ───────────────────────────────────────

_MACHINE_TO_ARCH: dict[str, SupportedArch] = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}

_SUPPORTED_OS_SET: set[str] = {"linux", "darwin", "windows"}


# ── Exceptions ───────────────────────────────────────────────────────


class RuntimeDownloadError(Exception):
    r"""Raised when a runtime binary download fails."""


class RuntimeExtractionError(Exception):
    r"""Raised when extracting a downloaded runtime archive fails."""


class RuntimeInstallError(Exception):
    r"""Raised when a runtime installation fails for any reason."""


# ── Platform Detection ───────────────────────────────────────────────


def get_platform_info() -> tuple[SupportedOS, SupportedArch]:
    r"""Detect the current OS and architecture for binary downloads.

    Returns:
        tuple[SupportedOS, SupportedArch]: A tuple of (os_name, arch)
            suitable for constructing download URLs.

    Raises:
        RuntimeError: If the OS or architecture is unsupported.
    """
    os_name = platform.system().lower()
    if os_name not in _SUPPORTED_OS_SET:
        raise RuntimeError(
            f"Unsupported operating system: {os_name}"
        )

    machine = platform.machine().lower()
    arch = _MACHINE_TO_ARCH.get(machine)
    if arch is None:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    return os_name, arch  # type: ignore[return-value]


# ── Download & Extraction ────────────────────────────────────────────


def download_and_extract_runtime(
    url: str,
    target_dir: str,
    archive_type: ArchiveType = "tar.gz",
    checksum_url: Optional[str] = None,
    update_callback: UpdateCallback = None,
) -> None:
    r"""Download and extract a runtime binary archive.

    Args:
        url (str): URL of the archive to download.
        target_dir (str): Directory to extract the archive into.
        archive_type (ArchiveType): Type of archive, either
            ``'tar.gz'`` or ``'zip'``.
            (default: :obj:`tar.gz`)
        checksum_url (str, optional): URL to a SHA256 checksum file
            for verification. (default: :obj:`None`)
        update_callback (Callable[[str], None], optional): Callback
            function to receive status updates.
            (default: :obj:`None`)

    Raises:
        RuntimeDownloadError: If the download fails.
        RuntimeExtractionError: If the archive extraction fails.
        RuntimeInstallError: If the installation fails for any
            other reason.
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
            _verify_checksum(tmp_file, checksum_url, update_callback)

        # Extract the archive
        if update_callback:
            update_callback(f"Extracting to {target_dir}...\n")

        if archive_type == "tar.gz":
            with tarfile.open(tmp_file, 'r:gz') as tar:
                tar.extractall(path=target_dir)
        else:
            with zipfile.ZipFile(tmp_file, 'r') as zf:
                zf.extractall(path=target_dir)

    except urllib.error.URLError as e:
        raise RuntimeDownloadError(
            f"Failed to download from {url}: {e}"
        ) from e
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        raise RuntimeExtractionError(
            f"Failed to extract archive: {e}"
        ) from e
    except (RuntimeDownloadError, RuntimeExtractionError):
        raise
    except Exception as e:
        raise RuntimeInstallError(
            f"Runtime installation failed: {e}"
        ) from e
    finally:
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass


def _verify_checksum(
    file_path: str,
    checksum_url: str,
    update_callback: UpdateCallback = None,
) -> None:
    r"""Verify the SHA256 checksum of a downloaded file.

    Args:
        file_path (str): Path to the file to verify.
        checksum_url (str): URL to the SHA256 checksum file.
        update_callback (Callable[[str], None], optional): Callback
            function to receive status updates.
            (default: :obj:`None`)
    """
    try:
        if update_callback:
            update_callback("Verifying checksum...\n")

        req = urllib.request.Request(
            checksum_url,
            headers={"User-Agent": "camel-ai/runtime-installer"},
        )
        with urllib.request.urlopen(req) as response:
            checksum_data = response.read().decode('utf-8')

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()

        if actual_hash not in checksum_data:
            raise RuntimeDownloadError(
                "Checksum verification failed! "
                "Download may be corrupted."
            )

        if update_callback:
            update_callback("Checksum verified successfully.\n")
    except RuntimeDownloadError:
        raise
    except Exception as e:
        logger.warning(f"Checksum verification skipped: {e}")
        if update_callback:
            update_callback(
                f"Warning: Checksum verification skipped: "
                f"{e}\n"
            )
