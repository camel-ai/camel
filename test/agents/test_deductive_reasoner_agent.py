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
import pytest
from mock import patch

from camel.agents import ChatAgent, ChatAgentResponse
from camel.agents.deductive_reasoner_agent import DeductiveReasonerAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.typing import ModelType, RoleType


@patch.object(ChatAgent, 'step')
@pytest.mark.parametrize("model_type", [None, ModelType.GPT_3_5_TURBO])
def test_deductive_reasoner_agent(mock_step, model_type):
    mock_content = generate_mock_content()
    mock_msg = BaseMessage(role_name="Deductive Reasoner",
                           role_type=RoleType.ASSISTANT, meta_dict=None,
                           content=mock_content)

    # Mock the step function
    mock_step.return_value = ChatAgentResponse(msgs=[mock_msg],
                                               terminated=False, info={})

    starting_state = "I was walking down the street in New York with a Anna."
    target_state = "I remind Anna to pay attention to personal safety."
    model_config_description = ChatGPTConfig()

    # Construct deductive reasoner agent
    deductivereasoneragent = \
        DeductiveReasonerAgent(model=model_type,
                               model_config=model_config_description)

    # Generate the conditions and quality dictionary based on the mock step
    # function
    conditions_and_quality = \
        deductivereasoneragent.deduce_conditions_and_quality(
            starting_state=starting_state, target_state=target_state)

    expected_dict = generate_expected_content()
    print(f"conditions_and_quality: {conditions_and_quality}")

    assert conditions_and_quality == expected_dict


# Generate mock content for the deductive reasoner agent
def generate_mock_content():
    return """- Characterization and comparison of $A$ and $B$:
$A$ represents the state of walking down the street in New York with Anna, while $B$ represents the state of reminding Anna to pay attention to personal safety.

- Historical & Empirical Analysis:
None

- Logical Deduction of Conditions ($C$) (multiple conditions can be deduced):
    condition 1:
        Anna must be present and engaged in the conversation.
    condition 2:
        There must be a potential safety risk or hazard in the environment.
    condition 3:
        The speaker must have knowledge or awareness of the safety risk.
    condition 4:
        The speaker must have a desire or intention to ensure Anna's personal safety.

- Quality Assessment ($Q$) (do not use symbols):
    The quality of the transition can be assessed based on the effectiveness of the reminder in ensuring Anna's personal safety and the efficiency of the communication process.

- Iterative Evaluation:
None"""  # noqa: E501


# Generate expected dictionary of conditions and quality
def generate_expected_content():
    return {
        "conditions": {
            "condition 1":
            "Anna must be present and engaged in the conversation.",
            "condition 2":
            "There must be a potential safety risk or hazard in the " +
            "environment.",
            "condition 3":
            "The speaker must have knowledge or awareness of the safety " +
            "risk.",
            "condition 4":
            "The speaker must have a desire or intention to ensure Anna's" +
            "personal safety."
        },
        "quality":
        ("The quality of the transition can be assessed based on the " +
         "effectiveness of the reminder in ensuring Anna's personal safety" +
         "and the efficiency of the communication process.")
    }
