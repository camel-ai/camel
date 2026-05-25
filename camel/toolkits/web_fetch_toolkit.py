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

import html
import re
from typing import TYPE_CHECKING, List, Optional, Union
from urllib.parse import urlparse

import httpx

from camel.logger import get_logger
from camel.models import BaseModelBackend, ModelManager
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = get_logger(__name__)

_ALLOWED_SCHEMES = ("http", "https")


class WebFetchToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""Toolkit for fetching a web page and summarizing it for a prompt."""

    def __init__(
        self,
        default_model: Optional[BaseModelBackend] = None,
        timeout: Optional[float] = None,
        request_timeout: float = 20.0,
    ) -> None:
        super().__init__(timeout=timeout)
        RegisteredAgentToolkit.__init__(self)
        self.default_model = default_model
        self.request_timeout = request_timeout
        self._summary_agent: Optional["ChatAgent"] = None
        self._summary_agent_model: Optional[
            Union[BaseModelBackend, ModelManager]
        ] = None
        self._summary_agent_language: Optional[str] = None

    def _error_message(self, message: str) -> str:
        logger.warning(message)
        return f"Error: {message}"

    def _resolve_model(
        self,
    ) -> Optional[Union[BaseModelBackend, ModelManager]]:
        if self._agent is not None:
            return self._agent.model_backend
        return self.default_model

    def _extract_text(self, content_type: str, body: str) -> str:
        if "html" not in content_type.lower():
            return body.strip()

        body = re.sub(
            r"(?is)<(script|style|noscript).*?>.*?</\1>",
            " ",
            body,
        )
        body = re.sub(r"(?s)<!--.*?-->", " ", body)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = html.unescape(body)
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n\s*\n+", "\n\n", body)
        return body.strip()

    def _get_summary_agent(self) -> Optional["ChatAgent"]:
        from camel.agents import ChatAgent

        model = self._resolve_model()
        if model is None:
            return None

        output_language = (
            self._agent.output_language if self._agent is not None else None
        )

        # Reuse cached agent only if model and language haven't changed
        if (
            self._summary_agent is not None
            and self._summary_agent_model is model
            and self._summary_agent_language == output_language
        ):
            self._summary_agent.reset()
            return self._summary_agent

        self._summary_agent = ChatAgent(
            system_message=(
                "You analyze fetched web pages and answer the user's prompt "
                "using only the provided page content."
            ),
            model=model,
            output_language=output_language,
        )
        self._summary_agent_model = model
        self._summary_agent_language = output_language
        return self._summary_agent

    def web_fetch_and_analyze(
        self, url: str, prompt: str, max_chars: int = 0
    ) -> str:
        r"""Fetch a URL and answer a prompt about its content.

        Args:
            url (str): URL to fetch.
            prompt (str): Instruction describing what to extract or analyze
                from the fetched page.
            max_chars (int): Maximum number of characters of page content to
                use. When set to 0 (default) the full page is sent to the
                summarizer. If the summarizer fails because the content is
                too long, retry with a smaller value.

        Returns:
            str: AI-processed summary or answer derived from the page content.
        """
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            return self._error_message(
                f"URL scheme '{parsed.scheme}' is not allowed. "
                f"Only {_ALLOWED_SCHEMES} are supported."
            )

        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.request_timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; CAMEL WebFetchToolkit/1.0)"
                    )
                },
            ) as client:
                http_response = client.get(url)
        except httpx.HTTPError as exc:
            return self._error_message(f"Failed to fetch {url}: {exc}")
        except Exception as exc:
            return self._error_message(
                f"Unexpected WebFetch request failure for {url}: {exc}"
            )

        if http_response.is_error:
            return self._error_message(
                f"Failed to fetch {url}: HTTP {http_response.status_code}"
            )

        page_text = self._extract_text(
            http_response.headers.get("content-type", ""),
            http_response.text,
        )
        if not page_text:
            return self._error_message(f"No readable content found at {url}")

        total_chars = len(page_text)
        if max_chars > 0:
            page_text = page_text[:max_chars]

        try:
            summary_agent = self._get_summary_agent()
        except Exception as exc:
            return self._error_message(
                f"Failed to create WebFetch summary agent: {exc}"
            )
        if summary_agent is None:
            return self._error_message(
                "WebFetchToolkit requires a registered parent agent or "
                "default_model."
            )

        try:
            agent_response = summary_agent.step(
                "Analyze the following fetched page content.\n\n"
                f"URL: {url}\n"
                f"User prompt: {prompt}\n\n"
                "Page content:\n"
                f"{page_text}"
            )
        except Exception as exc:
            return self._error_message(
                f"WebFetch summarizer failed for {url} "
                f"(page has {total_chars} chars). "
                f"You may retry with a smaller max_chars value. "
                f"Original error: {exc}"
            )
        if not agent_response.msgs:
            return self._error_message(
                "WebFetch summarizer returned no messages."
            )
        return agent_response.msgs[0].content

    def get_tools(self) -> List[FunctionTool]:
        return [FunctionTool(self.web_fetch_and_analyze)]
