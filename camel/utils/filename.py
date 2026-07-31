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
import platform
import re
import unicodedata

MAX_FILENAME_LENGTH = 255
# The full set Windows reserves, per the naming rules for files and
# directories. COM5-COM9 and LPT4-LPT9 were missing, so `sanitize_filename`
# handed them back unchanged.
WINDOWS_RESERVED = {
    'CON',
    'PRN',
    'AUX',
    'NUL',
    'COM1',
    'COM2',
    'COM3',
    'COM4',
    'COM5',
    'COM6',
    'COM7',
    'COM8',
    'COM9',
    'LPT1',
    'LPT2',
    'LPT3',
    'LPT4',
    'LPT5',
    'LPT6',
    'LPT7',
    'LPT8',
    'LPT9',
}


def sanitize_filename(
    url_name: str,
    default: str = "index",
    max_length: int = MAX_FILENAME_LENGTH,
) -> str:
    r"""Sanitize a URL path into a safe filename that is safe for
    most platforms.

    Args:
        url_name (str): The URL path to sanitize.
        default (str): Default name if sanitization results in empty string.
            (default: :obj:`"index"`)
        max_length (int): Maximum length of the filename.
            (default: :obj:`MAX_FILENAME_LENGTH`)

    Returns:
        str: A sanitized filename safe for most platforms.
    """
    if max_length < 1:
        raise ValueError(
            f"`max_length` must be greater than " f"0, got {max_length}"
        )

    if not url_name:
        return default

    # Normalize Unicode characters by removing characters
    # such as accents and special characters:
    # café☕.txt -> cafe.txt
    url_name = unicodedata.normalize('NFKD', url_name)
    url_name = url_name.encode('ASCII', 'ignore').decode('ASCII')

    # Replace special characters such as:
    # Separators: my/file:name*.txt -> my_file_name.txt etc.
    url_name = re.sub(r'[\\/:*?"<>|.]', '_', url_name)
    url_name = re.sub(r'_+', '_', url_name)  # Collapse multiple underscores
    url_name = url_name.strip('_')  # Remove leading/trailing underscores

    # Handle empty result if all characters are invalid:
    if not url_name:
        return default

    # Truncate first. Checking reserved names before truncating let the cut
    # itself produce one: `sanitize_filename("nullify", max_length=3)` returned
    # "nul", and writing to that path silently goes to the null device -- the
    # open succeeds, `os.path.exists` reports True, and no file appears.
    url_name = url_name[:max_length]

    # Trailing spaces are stripped by the filesystem, so the caller's returned
    # name would not be the name on disk. `_` above already covers the dot.
    url_name = url_name.rstrip(' ')

    if not url_name:
        return default

    # Handle Windows reserved names. Prefixing grows the name by one, so
    # truncate again to honour max_length.
    if platform.system() == "Windows" and url_name.upper() in WINDOWS_RESERVED:
        url_name = f"_{url_name}"[:max_length]

    return url_name
