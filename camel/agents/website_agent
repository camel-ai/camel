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
import re
import subprocess
from termcolor import colored
from typing import Any, List, Dict, Tuple, Optional, Union

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.configs import ChatGPTConfig
from camel.typing import ModelType, RoleType


class WebsiteAgent(ChatAgent):
    r"""An agent that constructs a website based on user's prompt.
    
    Attributes:
        DEFAULT_WORD_LIMIT (int): The default word limit for the task prompt.

    Args:
        model (ModelType): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any): The configuration for the model.
            (default: :obj:`None`)
        word_limit (int): The word limit for the task prompt.
            (default: :obj:`50`)
        output_language (str, optional): The language to be output by the
        agent. (default: :obj:`None`)
    """
    DEFAULT_WORD_LIMIT = 50

    def __init__(
        self,
        system_message: BaseMessage,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
    ) -> None:
    
        model_config = model_config or ChatGPTConfig(temperature=0.1)
        system_message = BaseMessage(
            role_name="GPT-4",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content=system_message,
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

    def parse_response(
        self, 
        response: str,
    ) -> List[Tuple[str, str]]:
        
        # Get all ``` blocks and preceding filenames
        regex = r"(\S+)\n\s*```[^\n]*\n(.+?)```"
        matches = re.finditer(regex, response, re.DOTALL)

        files = []
        for match in matches:
            # Strip the filename of any non-allowed characters and convert / to \
            path = re.sub(r'[<>"|?*]', "", match.group(1))

            # Remove leading and trailing brackets
            path = re.sub(r"^\[(.*)\]$", r"\1", path)

            # Remove leading and trailing backticks
            path = re.sub(r"^`(.*)`$", r"\1", path)

            # Remove trailing ]
            path = re.sub(r"\]$", "", path)

            # Get the code
            code = match.group(2)

            # Add the file to the list
            files.append((path, code))

        # Get all the text before the first ``` block
        readme = response.split("```")[0]
        files.append(("README.md", readme))

        # Return the files
        return files

    def to_files(
        self, 
        response: BaseMessage, 
        workspace,
    ) -> None:
        # response = response.msg.content
        workspace["all_output.txt"] = response.msg.content

        files = self.parse_response(response.msg.content)
        for file_name, file_content in files:
            workspace[file_name] = file_content
        
        
    def execute_entrypoint(
        self, 
        workspace,
    ) -> None:
        command = workspace["run.sh"]
        print(command)

        print("Do you want to execute this code?")
        print()
        print(command)
        print()
        print('If yes, press enter. Otherwise, type "no"')
        print()
        if input() not in ["", "y", "yes"]:
            print("Ok, not executing the code.")
            return []
        print("Executing the code...")
        print()
        print(
            colored(
                "Note: If it does not work as expected, consider running the code"
                + " in another way than above.",
                "green",
            )
        )
        print()
        print("You can press ctrl+c *once* to stop the execution.")
        print()

        p = subprocess.Popen("bash run.sh", shell=True, cwd=workspace.path)
        try:
            p.wait()
        except KeyboardInterrupt:
            print()
            print("Stopping execution.")
            print("Execution stopped.")
            p.kill()
            print()
