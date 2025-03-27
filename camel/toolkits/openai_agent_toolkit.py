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
from typing import List, Optional

from openai import OpenAI

from camel.logger import get_logger
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelPlatformType, ModelType
from camel.utils import api_keys_required

logger = get_logger(__name__)


class OpenAIAgentToolkit(BaseToolkit):
    r"""Toolkit for accessing OpenAI's agent tools including web search and
    file search.

    Provides access to OpenAI's web search and file search capabilities
    through the Responses API, allowing agents to retrieve information from
    the web and search through uploaded files.
    """

    @api_keys_required(
        [
            (None, "OPENAI_API_KEY"),
        ]
    )
    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
        api_key: Optional[str] = None,
    ) -> None:
        r"""Initialize the OpenAI agent toolkit.

        Args:
            model (BaseModelBackend): The OpenAI model to use for responses.
                If None, defaults to gpt-4o-mini. (default: :obj:`None`)
            api_key (str): OpenAI API key. If not provided, will attempt to
                use OPENAI_API_KEY environment variable. (default: :obj:`None`)
        """
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )

    def web_search(self, query: str) -> str:
        r"""Perform a web search using OpenAI's web search tool.

        Args:
            query (str): The search query.

        Returns:
            str: The search result or error message.
        """
        try:
            response = self.client.responses.create(
                model=str(self.model.model_type),
                tools=[{"type": "web_search_preview"}],
                input=query,
            )
            return response.output_text

        except Exception as e:
            logger.error(f"Web search failed: {e!s}")
            return f"Web search failed: {e!s}"

    def file_search(
        self,
        query: str,
        vector_store_id: str,
    ) -> str:
        r"""Search through files using OpenAI's file search tool.

        Args:
            query (str): The search query.
            vector_store_id (str): The vector store ID to search in.

        Returns:
            str: The search result or error message.
        """
        if not vector_store_id.strip():
            logger.error("Empty vector store ID provided.")
            return "Empty vector store ID provided, it cannot be empty."

        try:
            response = self.client.responses.create(
                model=str(self.model.model_type),
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store_id],
                    }
                ],
                input=query,
            )
            return response.output_text

        except Exception as e:
            logger.error(f"File search failed: {e!s}")
            return f"File search failed: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Retrieve available toolkit functions as FunctionTool objects.

        Returns:
            List[FunctionTool]: Collection of FunctionTool objects representing
                the available search functions in this toolkit.
        """
        return [
            FunctionTool(self.web_search),
            FunctionTool(self.file_search),
        ]
