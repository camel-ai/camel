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

from camel.agents.chat_agent import ChatAgent, ChatAgentResponse
from camel.agents.multi_agent import MultiAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType


@patch.object(ChatAgent, 'step')
@pytest.mark.parametrize("model_type", [None, ModelType.GPT_3_5_TURBO])
@pytest.mark.parametrize(
    "num_roles, role_names",
    [
        (
            1,
            ["Trading Strategist"],
        ),
        (2, ["Trading Strategist", "Data Scientist"]),
        (3, ["Trading Strategist", "Data Scientist", "Software Developer"]),
    ],
)
def test_multi_agent(mock_step, model_type, num_roles, role_names):
    mock_content = generate_mock_content(num_roles, role_names)
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
    model_config_description = ChatGPTConfig()

    # Construct role assignment agent
    role_description_agent = MultiAgent(
        model_type=model_type, model_config=model_config_description
    )

    # Generate the role description dictionary based on the mock step function
    role_description_dict = role_description_agent.run_role_with_description(
        task_prompt=task_prompt, num_roles=num_roles
    )

    expected_dict = generate_expected_dict(num_roles, role_names)

    print(f"expected_dict:\n{expected_dict}")
    assert role_description_dict == expected_dict


# Generate mock content according to the number of roles and role names
def generate_mock_content(num_roles, role_names):
    if len(role_names) != num_roles:
        raise ValueError(
            f"Length of role_names ({len(role_names)}) "
            f"does not equal to num_roles ({num_roles})."
        )
    role_descriptions = [
        "Design trading strategies.",
        "Analyze market data.",
        "Implement trading algorithms.",
    ]
    roles_with_descriptions = [
        (role_name, role_desc)
        for role_name, role_desc in zip(role_names, role_descriptions)
    ]

    content = []
    for i in range(num_roles):
        role_name, role_desc = roles_with_descriptions[i]
        content.append(
            f"Domain expert {i + 1}: {role_name}\n"
            f"Associated competencies, characteristics, and duties:\n"
            f"{role_desc}\nEnd."
        )

    return "\n".join(content)


# Generate expected dictionary according to the number of roles and role names
def generate_expected_dict(num_roles, role_names):
    if len(role_names) != num_roles:
        raise ValueError(
            f"Length of role_names ({len(role_names)}) "
            f"does not equal to num_roles ({num_roles})."
        )
    role_descriptions = [
        "Design trading strategies.",
        "Analyze market data.",
        "Implement trading algorithms.",
    ]
    roles_with_descriptions = {
        role_name: role_desc
        for role_name, role_desc in zip(role_names, role_descriptions)
    }

    return {
        key: roles_with_descriptions[key]
        for key in list(roles_with_descriptions.keys())[:num_roles]
    }
