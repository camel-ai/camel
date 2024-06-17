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

import os
from enum import Enum
from typing import Optional

JINA_ENDPOINT = "https://r.jina.ai/"


class JinaURLReader:
    r"""URL Reader provided by Jina AI. The output is cleaner and more
    LLM-friendly than the URL Reader of UnstructuredIO. Can be configured to
    replace the UnstructuredIO URL Reader in the pipeline.

    Attributes:
        headers (Dict[str, str]): Headers to be passed when requesting,
            including all the configurations.

    References:
        https://jina.ai/reader
    """

    class ReturnFormat(Enum):
        DEFAULT = "default"
        MARKDOWN = "markdown"
        HTML = "html"
        TEXT = "text"
        SCREENSHOT = "screenshot"

    def __init__(
            self,
            api_key: Optional[str] = None,
            return_format: Optional[ReturnFormat] = ReturnFormat.DEFAULT,
            json_response: Optional[bool] = False,
            timeout: Optional[int] = 10,
            **kwargs: str,
    ) -> None:
        r"""
        Initializes an instance of the JinaURLReader according to the provided
        configurations.

        Args:
            api_key (Optional[str]): The API key for Jina AI. If not
                provided, the reader will have a lower rate limit.
            return_format (Optional[ReturnFormat]): The level of detail
                of the returned content. Defaults to ``ReturnFormat.DEFAULT``,
                which is optimized for LLMs.
            json_response (Optional[bool]): Whether to return the response
                in JSON format. Defaults to False.
            timeout (Optional[int]): The maximum time in seconds to wait for
                the page to be rendered. Defaults to 10.
            **kwargs (str): Additional keyword arguments, including proxies,
                cookies, etc. It should align with the HTTP Header field and
                value pairs listed in the reference.

        Notes:
             See https://jina.ai/reader for additional configurations.
        """

        api_key = api_key or os.getenv('JINA_API_KEY')
        if not api_key:
            print(
                "[JinaURLReader] JINA_API_KEY not set. This will result in a "
                "low rate limit of Jina URL Reader. Get API key here: "
                "https://jina.ai/reader."
            )

        # if the following field not provided, it will be None
        api_field = f"Bearer {api_key}" if api_key else None
        json_field = "application/json" if json_response else None

        raw_headers = {
            "Authorization": api_field,
            "X-Return-Format": return_format.value,
            "Accept": json_field,
            "X-Timeout": str(timeout),
            **kwargs,
        }

        # eliminate None values
        self.headers = {k: v for k, v in raw_headers.items() if v}

    def read_content(self, url: str) -> str:
        r"""Reads the content of a URL and returns it as a LLM-friendly string.

        Args:
            url (str): The URL to read.

        Returns:
            str: The content of the URL.
        """

        import requests

        full_url = f"{JINA_ENDPOINT}{url}"
        try:
            resp = requests.get(full_url, headers=self.headers)
        except Exception as e:
            raise Exception(
                f"[JinaURLReader] Failed to read content from {url}"
            ) from e

        return resp.text
