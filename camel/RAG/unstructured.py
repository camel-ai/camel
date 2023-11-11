# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from typing import Any


def ensure_unstructured_version(min_version: str) -> None:
    r"""Validates that the installed 'Unstructured' library version satisfies
    the specified minimum version requirement. This function is essential for
    ensuring compatibility with features that depend on a certain version of
    the 'Unstructured' package.

    Args:
        min_version (str): The minimum version required,
        specified in 'major.minor.patch' format.

    Raises:
        ImportError: If the 'Unstructured' package
         is not available in the environment.
        ValueError: If the current 'Unstructured'
        version is older than the required minimum version.

    Example:
        >>> ensure_unstructured_version("1.2.0")F
        # This will raise an ImportError if 'Unstructured'
        #  is not installed, or a ValueError if the version is < 1.2.0.

    Notes:
        Uses the 'packaging.version' module to parse
        and compare version strings.
    """
    from packaging import version

    try:
        from unstructured.__version__ import __version__ as installed_version
    except ImportError as e:
        raise ImportError("unstructured package is not installed.") from e

    # Use packaging.version to compare versions
    min_ver = version.parse(min_version)
    installed_ver = version.parse(installed_version)

    if installed_ver < min_ver:
        raise ValueError(f"unstructured>={min_version} required, "
                         f"you have {installed_version}.")


def parse_file(file_path: str) -> Any:
    r"""Loads a file and parses its contents as unstructured data.

    Args:
        file_path (str): Path to the file to be parsed.
    Returns:
        Any: The result of parsing the file, could be a dict,
        list, etc., depending on the file's content.

    Raises:
        FileNotFoundError: If the file does not exist at the path specified.
        Exception: For any other issues during file parsing.
    """
    import os

    from unstructured.partition.auto import partition

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found.")

    # Read the file based on the format
    try:
        with open(f"{file_path}", "rb") as f:
            elements = partition(file=f)
            return elements  # Returning the parsed elements
    except Exception as e:
        raise Exception("Failed to parse the unstructured file.") from e


# example code
# path = '/Users/enrei/anaconda3/envs/Earth/camel/camel/
# functions/1911 Census Occupation Data Classification.pdf'
# elements = parse_file(path)

# text_chunks = [" ".join(str(el).split()) for el in elements]
# print(text_chunks)


def clean_text_data(text: str, options: dict) -> str:
    r"""Cleans text data using a variety of cleaning functions provided by the
    'unstructured' library.

    This function applies multiple text cleaning
    utilities to sanitize and prepare text data
    for NLP tasks. It uses the 'unstructured'
    library's cleaning bricks for operations like
    replacing unicode quotes, removing extra whitespace,
    dashes, non-ascii characters, and more.

    Args:
        text (str): The text to be cleaned.
        options (dict): A dictionary specifying which
        cleaning options to apply. The keys should match
        the names of the cleaning functions, and the
        values should be dictionaries containing the
        parameters for each function.

    Returns:
        str: The cleaned text.

    Example:
        >>> options = {
            'replace_unicode_quotes': {},
            'clean_extra_whitespace': {},
            'clean_dashes': {},
            'clean_non_ascii_chars': {}
        }
        >>> text = "Some dirty text â\x80\x99 with extra spaces and dashes."
        >>> clean_text_data(text, options)
        # This will return the text cleaned according to the specified options.

    Raises:
        AttributeError: If a cleaning option does not correspond to a
        valid cleaning function in 'unstructured'.

    Notes:
        The 'options' dictionary keys must correspond to valid cleaning
        brick names from the 'unstructured' library.
        Each brick's parameters must be provided in a nested dictionary
        as the value for the key.
    """
    from unstructured.cleaners.core import (
        bytes_string_to_string,
        clean,
        clean_bullets,
        clean_dashes,
        clean_extra_whitespace,
        clean_non_ascii_chars,
        clean_ordered_bullets,
        clean_postfix,
        clean_prefix,
        clean_trailing_punctuation,
        group_broken_paragraphs,
        remove_punctuation,
        replace_unicode_quotes,
        translate_text,
    )

    # Map of available cleaning functions for dynamic access
    cleaning_functions = {
        "replace_unicode_quotes": replace_unicode_quotes,
        "clean_extra_whitespace": clean_extra_whitespace,
        "clean_dashes": clean_dashes,
        "clean_non_ascii_chars": clean_non_ascii_chars,
        "bytes_string_to_string": bytes_string_to_string,
        "clean": clean,
        "clean_bullets": clean_bullets,
        "clean_ordered_bullets": clean_ordered_bullets,
        "clean_postfix": clean_postfix,
        "clean_prefix": clean_prefix,
        "clean_trailing_punctuation": clean_trailing_punctuation,
        "group_broken_paragraphs": group_broken_paragraphs,
        "remove_punctuation": remove_punctuation,
        "translate_text": translate_text,
    }

    cleaned_text = text
    for func_name, params in options.items():
        if func_name in cleaning_functions:
            cleaned_text = cleaning_functions[func_name](cleaned_text,
                                                         **params)
        else:
            raise AttributeError(
                f"'{func_name}' is not a valid function in 'unstructured'.")

    return cleaned_text
