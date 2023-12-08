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
from io import BytesIO

from camel.agents.output_agent import OutputAgent
from camel.functions.base_io_functions import HtmlFile


def main() -> None:
    # Use one html file output from mulit agent as example
    with open("examples/output_agent/multi_agent_output_Supply_Chain_en.html",
              "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.html"
        html_file = HtmlFile.from_bytes(file)
    normal_string = html_file.docs[0]['page_content']

    # Initialize the OutputAgent
    output_agent = OutputAgent(model_type=None, model_config=None)

    # Generate the detailed instruction
    instruction = output_agent.generate_detailed_instruction(
        text=normal_string)
    print(instruction)


if __name__ == "__main__":
    main()
