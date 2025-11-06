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
import platform
import re
import unicodedata

MAX_FILENAME_LENGTH = 255
WINDOWS_RESERVED = {
    'CON',
    'PRN',
    'AUX',
    'NUL',
    'COM1',
    'COM2',
    'COM3',
    'COM4',
    'LPT1',
    'LPT2',
    'LPT3',
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

    # Handle Windows reserved names
    if platform.system() == "Windows" and url_name.upper() in WINDOWS_RESERVED:
        url_name = f"_{url_name}"

    return url_name[:max_length]
