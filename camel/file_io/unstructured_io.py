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

from typing import Any, Dict, List, Union

import pandas as pd


class UnstructuredModules:
    UNSTRUCTURED_MIN_VERSION = "0.10.30"  # Define the minimum version

    def ensure_unstructured_version(self, min_version: str) -> None:
        r"""Validates that the installed 'Unstructured' library version
        satisfies the specified minimum version requirement. This function is
        essential for ensuring compatibility with features that depend on a
        certain version of the 'Unstructured' package.

        Args:
            min_version (str): The minimum version required,
            specified in 'major.minor.patch' format.

        Raises:
            ImportError: If the 'Unstructured' package
            is not available in the environment.
            ValueError: If the current 'Unstructured'
            version is older than the required minimum version.

        Notes:
            Uses the 'packaging.version' module to parse
            and compare version strings.
        """
        from packaging import version

        try:
            from unstructured.__version__ import __version__

        except ImportError as e:
            raise ImportError("unstructured package is not installed.") from e

        # Use packaging.version to compare versions
        min_ver = version.parse(min_version)
        installed_ver = version.parse(__version__)

        if installed_ver < min_ver:
            raise ValueError(f"unstructured>={min_version} required, "
                             f"you have {__version__}.")

    def parse_file_or_url(self, input_path: str) -> Any:
        r"""Loads a file or a URL and parses its contents as unstructured data.

        Args:
            input_path (str): Path to the file or URL to be parsed.
        Returns:
            Any: The result of parsing the file or URL, could be a dict,
            list, etc., depending on the content.

        Raises:
            FileNotFoundError: If the file does not exist
            at the path specified.
            Exception: For any other issues during file or URL parsing.

        Notes:
            By default we use the basic "unstructured" library,
            If you are processing document types beyond the basics,
            you can install the necessary extras like:
            pip install "unstructured[docx,pptx]"
            Available document types:
            "csv", "doc", "docx", "epub", "image", "md", "msg", "odt",
            "org", "pdf", "ppt", "pptx", "rtf", "rst", "tsv", "xlsx"

        References:
            https://unstructured-io.github.io/unstructured/
        """
        import os
        from urllib.parse import urlparse

        # Check installed unstructured version
        self.ensure_unstructured_version(self.UNSTRUCTURED_MIN_VERSION)

        # Check if the input is a URL
        parsed_url = urlparse(input_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        if is_url:
            # Handling URL
            from unstructured.partition.html import partition_html

            try:
                elements = partition_html(url=input_path)
                return elements
            except Exception as e:
                raise Exception("Failed to parse the URL.") from e

        else:
            # Handling file
            from unstructured.partition.auto import partition

            # Check if the file exists
            if not os.path.exists(input_path):
                raise FileNotFoundError(
                    f"The file {input_path} was not found.")

            # Read the file
            try:
                with open(input_path, "rb") as f:
                    elements = partition(file=f)
                    return elements  # Returning the parsed elements
            except Exception as e:
                raise Exception(
                    "Failed to parse the unstructured file.") from e

    def clean_text_data(self, text: str, options: Dict[str, Any]) -> str:
        r"""Cleans text data using a variety of cleaning functions provided by
        the 'unstructured' library.

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

        Raises:
            AttributeError: If a cleaning option does not correspond to a
            valid cleaning function in 'unstructured'.

        Notes:
            The 'options' dictionary keys must correspond to valid cleaning
            brick names from the 'unstructured' library.
            Each brick's parameters must be provided in a nested dictionary
            as the value for the key.

        References:
            https://unstructured-io.github.io/unstructured/
        """
        # Check installed unstructured version
        self.ensure_unstructured_version(self.UNSTRUCTURED_MIN_VERSION)

        from unstructured.cleaners.core import (
            bytes_string_to_string,
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
        )
        from unstructured.cleaners.translate import translate_text

        cleaning_functions = {
            "clean_extra_whitespace": clean_extra_whitespace,
            "clean_bullets": clean_bullets,
            "clean_ordered_bullets": clean_ordered_bullets,
            "clean_postfix": clean_postfix,
            "clean_prefix": clean_prefix,
            "clean_dashes": clean_dashes,
            "clean_trailing_punctuation": clean_trailing_punctuation,
            "clean_non_ascii_chars": clean_non_ascii_chars,
            "group_broken_paragraphs": group_broken_paragraphs,
            "remove_punctuation": remove_punctuation,
            "replace_unicode_quotes": replace_unicode_quotes,
            "bytes_string_to_string": bytes_string_to_string,
            "translate_text": translate_text,
        }

        cleaned_text = text
        for func_name, params in options.items():
            if func_name in cleaning_functions:
                cleaned_text = cleaning_functions[func_name](cleaned_text,
                                                             **params)
            else:
                raise ValueError(
                    f"'{func_name}' is not a valid function in 'unstructured'."
                )

        return cleaned_text

    def extract_data_from_text(self, extract_type: str, text: str,
                               **kwargs) -> Any:
        r"""Extracts various types of data from text using functions from
        unstructured.cleaners.extract.

        Args:
            text (str): Text to extract data from.
            extract_type (str): Type of data to extract
            (e.g., 'datetime', 'email', 'ip', etc.).
            **kwargs: Additional keyword arguments for specific
            extraction functions.

        Returns:
            Any: The extracted data, type depends on extract_type.

        References:
            https://unstructured-io.github.io/unstructured/
        """
        # Check installed unstructured version
        self.ensure_unstructured_version(self.UNSTRUCTURED_MIN_VERSION)

        from unstructured.cleaners.extract import (
            extract_datetimetz,
            extract_email_address,
            extract_ip_address,
            extract_ip_address_name,
            extract_mapi_id,
            extract_ordered_bullets,
            extract_text_after,
            extract_text_before,
            extract_us_phone_number,
        )

        extraction_functions = {
            "extract_datetimetz": extract_datetimetz,
            "extract_email_address": extract_email_address,
            "extract_ip_address": extract_ip_address,
            "extract_ip_address_name": extract_ip_address_name,
            "extract_mapi_id": extract_mapi_id,
            "extract_ordered_bullets": extract_ordered_bullets,
            "extract_text_after": extract_text_after,
            "extract_text_before": extract_text_before,
            "extract_us_phone_number": extract_us_phone_number,
        }

        if extract_type not in extraction_functions:
            raise ValueError(f"Unsupported extract_type: {extract_type}")

        return extraction_functions[extract_type](text, **kwargs)

    def stage_elements(self, stage_type: str, elements: List[Any],
                       **kwargs) -> Union[str, List[Dict], pd.DataFrame]:
        r"""Stages elements for various platforms based on the
        specified staging type.

        This function applies multiple staging utilities to format data
        for different NLP annotation and machine learning tools. It uses
        the 'unstructured.staging' module's functions for operations like
        converting to CSV, DataFrame, dictionary, or formatting for
        specific platforms like Prodigy, etc.

        Args:
            stage_type (str): Type of staging to perform. Supported types:
                            'csv', 'dataframe', 'dict', 'prodigy',
                            'baseplate', 'datasaur', 'label_box', 'weaviate'.
            elements (List[Any]): List of Element objects to be staged.
            **kwargs: Additional keyword arguments specific to
            the staging type.

        Returns:
            Union[str, List[Dict], pd.DataFrame]: Staged data in the
            format appropriate for the specified staging type.

        Raises:
            ValueError: If the staging type is not supported or
            a required argument is missing.
        References:
            https://unstructured-io.github.io/unstructured/
        """
        # Check installed unstructured version
        self.ensure_unstructured_version(self.UNSTRUCTURED_MIN_VERSION)

        from unstructured.staging import (
            argilla,
            base,
            baseplate,
            datasaur,
            label_box,
            label_studio,
            prodigy,
            weaviate,
        )

        staging_functions = {
            "convert_to_csv":
            base.convert_to_csv,
            "convert_to_dataframe":
            base.convert_to_dataframe,
            "convert_to_dict":
            base.convert_to_dict,
            "dict_to_elements":
            base.dict_to_elements,
            "stage_csv_for_prodigy":
            lambda els, **kw: prodigy.stage_csv_for_prodigy(
                els, kw.get('metadata', [])),
            "stage_for_prodigy":
            lambda els, **kw: prodigy.stage_for_prodigy(
                els, kw.get('metadata', [])),
            "stage_for_argilla":
            lambda els, **kw: argilla.stage_for_argilla(els, **kw),
            "stage_for_baseplate":
            baseplate.stage_for_baseplate,
            "stage_for_datasaur":
            lambda els, **kw: datasaur.stage_for_datasaur(
                els, kw.get('entities', [])),
            "stage_for_label_box":
            lambda els, **kw: label_box.stage_for_label_box(els, **kw),
            "stage_for_label_studio":
            lambda els, **kw: label_studio.stage_for_label_studio(els, **kw),
            "stage_for_weaviate":
            weaviate.stage_for_weaviate,
        }

        if stage_type not in staging_functions:
            raise ValueError(f"Unsupported stage type: {stage_type}")

        return staging_functions[stage_type](elements, **kwargs)

    def chunk_elements(self, chunk_type: str, elements: List[Any],
                       **kwargs) -> List[Dict]:
        r"""Chunks elements by titles.

        Args:
            elements (List[Any]): List of Element objects to be chunked.
            **kwargs: Additional keyword arguments for chunking.

        Returns:
            List[Dict]: List of chunked sections.

        References:
            https://unstructured-io.github.io/unstructured/
        """
        # Check installed unstructured version
        self.ensure_unstructured_version(self.UNSTRUCTURED_MIN_VERSION)

        from unstructured.chunking.title import chunk_by_title

        chunking_functions = {
            "chunk_by_title": chunk_by_title,
        }

        if chunk_type not in chunking_functions:
            raise ValueError(f"Unsupported chunk type: {chunk_type}")

        # Format chunks into a list of dictionaries (or your preferred format)
        return chunking_functions[chunk_type](elements, **kwargs)
