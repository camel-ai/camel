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
from typing import Any, Dict, List, Optional

import requests

from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelPlatformType, ModelType


class OpenAIAgentToolkit(BaseToolkit):
    r"""A toolkit for OpenAI's agent tools including web search.

    Args:
        model (Optional[BaseModelBackend], optional): The model to use for
            responses. If None, defaults to gpt-4o-mini.
        api_key (Optional[str], optional): OpenAI API key. If not provided,
            will attempt to use OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
        api_key: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.model = model or ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )

    def _call_responses_api(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        model: str = "gpt-4o-mini",
    ) -> Dict[str, Any]:
        """Call the OpenAI Responses API with the given query and tools.

        Args:
            query (str): The query to send.
            tools (List[Dict[str, Any]]): The tools to use.
            model (str, optional): The model to use. Defaults to "gpt-4o-mini".

        Returns:
            Dict[str, Any]: The API response.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {"model": model, "tools": tools, "input": query}

        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=data,
                timeout=60.0,
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise ValueError(f"API call failed: {e!s}")

    def _extract_output_text(self, response: Dict[str, Any]) -> str:
        """Extract text output from the response.

        Args:
            response (Dict[str, Any]): The API response.

        Returns:
            str: The extracted text.
        """
        for output in response.get("output", []):
            if output.get("type") == "message":
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        return content.get("text", "")

        return "No text output found."

    def web_search(self, query: str) -> str:
        r"""Perform a web search using OpenAI's web search tool.

        Args:
            query (str): The search query.

        Returns:
            str: The search result.
        """
        try:
            response = self._call_responses_api(
                query=query, tools=[{"type": "web_search_preview"}]
            )

            return self._extract_output_text(response)

        except Exception as e:
            return f"Web search failed: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available tools.

        Returns:
            List[FunctionTool]: List of function tools.
        """
        return [
            FunctionTool(self.web_search),
        ]
