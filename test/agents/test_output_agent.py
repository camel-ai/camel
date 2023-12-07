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
# # =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# # Licensed under the Apache License, Version 2.0 (the “License”);
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an “AS IS” BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.
# # =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest
from mock import patch

from camel.agents import ChatAgent
from camel.agents.output_agent import OutputAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import ModelType, RoleType


# Helper function to generate mock content
def generate_mock_content():
    return "Sample instruction for testing."


# The actual test case
@pytest.mark.parametrize("model_type", [None, ModelType.GPT_3_5_TURBO])
def test_generate_detailed_instruction(model_type):
    mock_content = generate_mock_content()
    mock_msg = BaseMessage(role_name="Output Agent",
                           role_type=RoleType.ASSISTANT, meta_dict=None,
                           content=mock_content)

    # Construct the mock step function response
    mock_step_response = ChatAgentResponse(msgs=[mock_msg], terminated=False,
                                           info={})

    # Setup the patch for the ChatAgent's step method
    with patch.object(ChatAgent, 'step', return_value=mock_step_response):
        content = "Sample content for testing."
        model_config = ChatGPTConfig()

        # Construct the output agent
        output_agent = OutputAgent(model_type=model_type,
                                   model_config=model_config)

        # Generate the detailed instruction based on the mock step function
        instruction = output_agent.generate_detailed_instruction(content)

        expected_instruction = generate_mock_content()

        assert instruction == expected_instruction
