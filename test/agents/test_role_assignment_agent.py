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
import pytest
from mock import patch

from camel.agents import ChatAgent, RoleAssignmentAgent
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import RoleType


@patch.object(ChatAgent, 'step')
@pytest.mark.parametrize("num_roles", [1, 2, 3])
def test_role_assignment_agent(mock_step, num_roles):
    mock_content = generate_mock_content(num_roles)
    mock_msg = BaseMessage(
        role_name="Role Assigner",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content=mock_content,
    )

    # Mock the step function
    mock_step.return_value = ChatAgentResponse(
        msgs=[mock_msg], terminated=False, info={}
    )

    task_prompt = "Develop a trading bot for the stock market."

    # Construct role assignment agent
    role_description_agent = RoleAssignmentAgent()

    # Generate the role description dictionary based on the mock step function
    role_description_dict = role_description_agent.run(task_prompt, num_roles)

    expected_dict = generate_expected_dict(num_roles)

    assert role_description_dict == expected_dict


# Generate mock content according to the number of roles
def generate_mock_content(num_roles):
    assert num_roles <= 3
    roles_with_descriptions = [
        ("Trading Strategist", "Design trading strategies. End."),
        ("Data Scientist", "Analyze market data. End."),
        ("Software Developer", "Implement trading algorithms. End."),
    ]

    content = []
    for i in range(num_roles):
        role_name, role_desc = roles_with_descriptions[i]
        content.append(
            f"Domain expert {i + 1}: {role_name}\n"
            f"Associated competencies, characteristics, duties and workflows: "
            f"{role_desc}. End."
        )

    return "\n".join(content)


# Generate expected dictionary according to the number of roles
def generate_expected_dict(num_roles):
    assert num_roles <= 3
    roles_with_descriptions = {
        "Trading Strategist": "Design trading strategies.",
        "Data Scientist": "Analyze market data.",
        "Software Developer": "Implement trading algorithms.",
    }

    return {
        key: roles_with_descriptions[key]
        for key in list(roles_with_descriptions.keys())[:num_roles]
    }
