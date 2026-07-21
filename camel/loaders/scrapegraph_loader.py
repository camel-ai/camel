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

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from camel.loaders.base_loader import BaseLoader


class ScrapeGraphAILoader(BaseLoader):
    r"""ScrapeGraphAI Loader adhering to the unified BaseLoader interface."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        user_prompt: str = "Extract the main content from this page.",
        **kwargs: Any,
    ) -> None:
        if config:
            api_key = config.get('api_key', api_key)
            self.user_prompt = config.get('user_prompt', user_prompt)
        else:
            self.user_prompt = user_prompt

        super().__init__(config=config)

        try:
            from scrapegraph_py import Client  # type: ignore[attr-defined]
        except ImportError:
            try:
                from scrapegraph_py import (  # type: ignore[attr-defined]
                    client as Client,
                )
            except ImportError:
                try:
                    from scrapegraph_py.client import (  # type: ignore[attr-defined]
                        Client,
                    )
                except ImportError:
                    from scrapegraph_py.client import (  # type: ignore[attr-defined]
                        client as Client,
                    )

        if hasattr(Client, "Client"):
            Client = Client.Client
        elif hasattr(Client, "client"):
            Client = Client.client
        elif hasattr(Client, "SmartScraperGraph"):
            Client = Client.SmartScraperGraph

        self._api_key = api_key or os.environ.get("SCRAPEGRAPH_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Please set SCRAPEGRAPH_API_KEY environment variable "
                "or pass api_key."
            )

        self.client = Client(api_key=self._api_key)

    @property
    def supported_formats(self) -> set[str]:
        return {"url", "http", "https", "html"}

    def _load_single(
        self, source: Union[str, Path], **kwargs: Any
    ) -> Dict[str, Any]:
        website_url = str(source)
        try:
            response = self.client.smartscraper(
                website_url=website_url,
                user_prompt=self.user_prompt,
                **kwargs,
            )
            return {"content": response, "source": website_url}
        except Exception as e:
            raise RuntimeError(
                f"Failed to perform scrape on {website_url}: {e}"
            )

    def close(self) -> None:
        r"""Close the ScrapeGraphAI client connection."""
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            self.client.close()
