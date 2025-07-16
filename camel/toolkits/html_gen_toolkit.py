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

# Enables postponed evaluation of annotations (for string-based type hints)
from __future__ import annotations

import os
from typing import List, Optional

from camel.logger import get_logger
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class HtmlGenToolkit(BaseToolkit):
    r"""A toolkit for generating HTML content.
    The toolkit uses language models to generate HTML content.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        workspace: str = "./",
    ):
        r"""Initialize the HtmlGenToolkit.

        Args:
            model (Optional[BaseModelBackend]): The model backend to use for
                HTML generation tasks. This model should support generating
                HTML content. If None, a default model will be created using
                ModelFactory. (default: :obj:`None`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            workspace (Optional[str]): The workspace to use for the generation.
                (default: :obj:`.`)
        """
        from camel.agents.chat_agent import ChatAgent

        super().__init__(timeout=timeout)
       
        self.workspace = workspace
        self.plan_generated = False
        
    def generate_plan(self,plan:str) -> str:
        r"""Generates a plan for the html generation.

        Args:
            plan (str): The plan for the html generation.
              this plan will be used by agent to generate the html content,
              you need to consider the following factors:
              - the size of the html
              - the number of the html
              - the content of the html
              - the structure of the html
              - the style of the html
              - the layout of the html
              - some other factors you think is important
              - when you need to generate serveral html files, you need to plan
              a final html file, and the final html file should be a viewer html file.
              if user don't define the size of the html, default size is 16:9	(1280 * 720)
        Returns:
            str: The plan for the html generation.
        """
        self.plan_generated = True
        return plan


    def generate_one_page_html(self, content: str, filename: str) -> str:
        r"""Generates HTML content for one page html.This function should 
        be called after the plan is generated. And this function will generate
        the html content based on the plan, will generate the html file one by one.

        Args:
            content (str): The content of the html generation,you need to 
              make good use of the layout of the entire page to make the 
              HTML page as beautiful as possible.

            filename (str): The filename of the html file.

        Returns:
            str: HTML content for one page html.
        """
        if not self.plan_generated:
            raise ValueError("Plan not generated, please generate plan first")
        # save to file
        with open(os.path.join(self.workspace, filename), "w") as f:
            f.write(content)
        result = (
            f"Content successfully written to file: {filename}"
            f"The content is: {content}"
        )
        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
            functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.generate_one_page_html),
            FunctionTool(self.generate_plan),
        ]
