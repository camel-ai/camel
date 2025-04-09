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

from zhipuai import ZhipuAI

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)


@MCPServer()
class ZhiPuToolkit(BaseToolkit):
    r"""A toolkit using  the agent on Zhipu AI platform."""

    @api_keys_required(
        [
            ("api_key", 'ZHIPUAI_API_KEY'),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ):
        r"""Initialize the ZhiPuToolkit.

        Args:
            api_key (Optional[str]): The api key to use for the Zhipu platform.
                (default: :obj:`None`)
            url (Optional[str]): The url to use for the Zhipu platform.
                (default: :obj:`None`)
        """
        api_key = api_key or os.environ.get("ZHIPUAI_API_KEY")
        url = url or os.environ.get(
            "ZHIPUAI_API_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"
        )
        self.client = ZhipuAI(api_key=api_key, base_url=url)
        self.file_ids: List[str] = []
        self.conversation_id: Optional[str] = None

    def _call_the_agent(
        self,
        prompt: str,
        assistant_id: str,
        file_path: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        r"""Call the agent to get the result.

        Args:
            prompt (str): The prompt to call the agent.
            assistant_id (str): The assistant id to call the agent.
            file_path (Optional[str]): The path of the file to upload.
                (default: :obj:`None`)
            conversation_id (Optional[str]): The conversation id of session.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        if file_path:
            try:
                resp = self.client.files.create(
                    file=open(file_path, 'rb'), purpose='assistant'
                )
                file_id = resp.id
                self.file_ids.append(file_id)
                attachments = [
                    {"file_id": file_id} for file_id in self.file_ids
                ]
            except Exception as e:
                logger.error(f"Upload file failed: {e}")
                return f"Upload file failed: {e!s}"
        else:
            attachments = None
        try:
            response = self.client.assistant.conversation(
                assistant_id=assistant_id,
                conversation_id=conversation_id,
                model="glm-4-assistant",
                messages=[
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
                stream=True,
                attachments=attachments,
                metadata=None,
            )
            result = ""
            # Parse according to the Zhipu message format
            for resp in response:
                if hasattr(resp, 'choices') and resp.choices:
                    choice = resp.choices[0]
                    if hasattr(choice, 'delta'):
                        if (
                            hasattr(choice.delta, 'tool_calls')
                            and choice.delta.tool_calls
                        ):
                            for tool_call in choice.delta.tool_calls:
                                for attr in dir(tool_call):
                                    if not attr.startswith('_'):
                                        attr_value = getattr(tool_call, attr)
                                        if (
                                            hasattr(attr_value, 'outputs')
                                            and attr_value.outputs
                                        ):
                                            for (
                                                output_item
                                            ) in attr_value.outputs:
                                                result += str(output_item)
                        if hasattr(choice.delta, 'content'):
                            result += str(choice.delta.content)
                        self.conversation_id = resp.conversation_id

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Call the agent failed: {e!s}"

        return result

    def draw_mindmap(
        self, prompt: str, file_path: Optional[str] = None
    ) -> str:
        r"""Generates mindmap with prompt.

        Args:
            prompt (str): The prompt to write the mindmap.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        return self._call_the_agent(
            prompt=prompt,
            assistant_id="664dd7bd5bb3a13ba0f81668",
            file_path=file_path,
        )

    def draw_flowchart(
        self, prompt: str, file_path: Optional[str] = None
    ) -> str:
        r"""Draw a flowchart with a prompt.

        Args:
            prompt (str): The prompt for drawing the flowchart.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        return self._call_the_agent(
            prompt=prompt,
            assistant_id="664dd7bd5bb3a13ba0f81668",
            file_path=file_path,
        )

    def data_analysis(
        self, prompt: str, file_path: Optional[str] = None
    ) -> str:
        r"""Analyze data and provide charting capabilities. Also,
        it can complete file processing tasks through simple coding.

        Args:
            prompt (str): The prompt for data analysis.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        return self._call_the_agent(
            prompt=prompt,
            assistant_id="65a265419d72d299a9230616",
            file_path=file_path,
        )

    def ai_drawing(self, prompt: str, file_path: Optional[str] = None) -> str:
        r"""Draw a picture with a prompt.

        Args:
            prompt (str): The prompt for drawing.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        return self._call_the_agent(
            prompt=prompt,
            assistant_id="66437ef3d920bdc5c60f338e",
            file_path=file_path,
        )

    def ai_search(self, prompt: str, file_path: Optional[str] = None) -> str:
        r"""Search the internet for information and answer questions.

        Args:
            prompt (str): The prompt for searching the internet.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        return self._call_the_agent(
            prompt=prompt,
            assistant_id="659e54b1b8006379b4b2abd6",
            file_path=file_path,
        )

    def ppt_generation(
        self, prompt: str, file_path: Optional[str] = None
    ) -> str:
        r"""Generate a ppt with a prompt.

        Args:
            prompt (str): The prompt for generating the ppt.
            file_path (Optional[str]): The path of the reference file.
                (default: :obj:`None`)
        Returns:
            str: The result of the agent.
        """
        self._call_the_agent(
            prompt=prompt,
            assistant_id="65d2f07bb2c10188f885bd89",
            file_path=file_path,
        )
        return self._call_the_agent(
            prompt='生成PPT',
            assistant_id="65d2f07bb2c10188f885bd89",
            file_path=file_path,
            conversation_id=self.conversation_id,
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
            in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.draw_mindmap),
            FunctionTool(self.draw_flowchart),
            FunctionTool(self.data_analysis),
            FunctionTool(self.ai_drawing),
            FunctionTool(self.ai_search),
            FunctionTool(self.ppt_generation),
        ]
