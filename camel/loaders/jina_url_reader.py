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
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from warnings import warn

from camel.types.enums import JinaReturnFormat

from .base_loader import BaseLoader

JINA_ENDPOINT = "https://r.jina.ai/"


class JinaURLLoader(BaseLoader):
    r"""URL Loader provided by Jina AI. The output is cleaner and more
    LLM-friendly than the URL Reader of UnstructuredIO. Can be configured to
    replace the UnstructuredIO URL Reader in the pipeline.

    Args:
        api_key (Optional[str], optional): The API key for Jina AI. If not
            provided, the reader will have a lower rate limit. Defaults to
            None. (default: :obj:`None`)
        return_format (ReturnFormat, optional): The level of detail
            of the returned content, which is optimized for LLMs. For
            now screenshots are not supported. Defaults to
            ReturnFormat.DEFAULT. (default: :obj:`ReturnFormat.DEFAULT`)
        json_response (bool, optional): Whether to return the response
            in JSON format. Defaults to False. (default: :obj:`False`)
        timeout (int, optional): The maximum time in seconds to wait for
            the page to be rendered. Defaults to 30. (default: :obj:`30`)
        **kwargs (Any): Additional keyword arguments, including proxies,
            cookies, etc. It should align with the HTTP Header field and
            value pairs listed in the reference. (default: :obj:`None`)

    References:
        https://jina.ai/reader
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        return_format: JinaReturnFormat = JinaReturnFormat.DEFAULT,
        json_response: bool = False,
        timeout: int = 30,
    ) -> None:
        super().__init__()

        api_key = api_key or os.getenv('JINA_API_KEY')
        if not api_key:
            warn(
                "JINA_API_KEY not set. This will result in a low rate limit "
                "of Jina URL Reader. Get API key here: https://jina.ai/reader."
            )

        # if the following field not provided, it will be None
        api_field = f"Bearer {api_key}" if api_key else None
        json_field = "application/json" if json_response else None

        raw_headers = {
            "Authorization": api_field,
            "X-Return-Format": return_format.value,
            "Accept": json_field,
            "X-Timeout": str(timeout),
        }

        # eliminate None values
        self._headers = {k: v for k, v in raw_headers.items() if v}
        self.timeout = timeout

    def _load_single(
        self,
        source: Union[str, Path],
    ) -> Any:
        r"""Load content from a single URL.

        Args:
            source: The URL to load content from.
            (default: :obj:`None`)

        Returns:
            Any: The loaded data with at least

        Raises:
            ValueError: If the URL is invalid or the request fails.
        """
        import requests

        source_str = str(source)
        if not source_str.startswith(('http://', 'https://')):
            source_str = f"https://{source_str}"

        try:
            response = requests.get(
                JINA_ENDPOINT,
                params={"url": str(source)},
                headers=self._headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise ValueError(
                f"Failed to read content from {source}: {e}"
            ) from e

    def load(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
    ) -> Dict[str, Any]:
        r"""Load content from one or more URLs.

        Args:
            source: A single URL or a list of URLs to load.
            (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the loaded data with
               the source key.

        Raises:
            ValueError: If any URL is invalid or the request fails.
        """
        if isinstance(source, (str, Path)):
            content = self._load_single(source)
            return {str(source): content}
        elif isinstance(source, list):
            result = {}
            for url in source:
                content = self._load_single(url)
                result[str(url)] = content
            return result
        else:
            raise TypeError(f"Expected str, Path, or list, got {type(source)}")

    @property
    def supported_formats(self) -> set[str]:
        r"""Get the set of supported URL schemes.

        Returns:
            set[str]: The set of supported URL schemes.
        """
        return {"http", "https"}
