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
from mock import patch

from camel.agents import ChatAgent
from camel.agents.deductive_reasoner_agent import DeductiveReasonerAgent
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import RoleType


@patch.object(ChatAgent, 'step')
def test_deductive_reasoner_agent(mock_step):
    mock_content = generate_mock_content()
    mock_msg = BaseMessage(
        role_name="Deductive Reasoner",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content=mock_content,
    )

    # Mock the step function
    mock_step.return_value = ChatAgentResponse(
        msgs=[mock_msg], terminated=False, info={}
    )

    starting_state = "I was walking down the street in New York with a Anna."
    target_state = "I remind Anna to pay attention to personal safety."

    # Construct deductive reasoner agent
    deductive_reasoner_agent = DeductiveReasonerAgent()

    # Generate the conditions and quality dictionary based on the mock step
    # function
    conditions_and_quality = (
        deductive_reasoner_agent.deduce_conditions_and_quality(
            starting_state=starting_state, target_state=target_state
        )
    )

    expected_dict = generate_expected_content()

    assert conditions_and_quality == expected_dict


# Generate mock content for the deductive reasoner agent
def generate_mock_content():
    return """- Characterization and comparison of $A$ and $B$:
$A$ is an empty website, while $B$ is a website with search capabilities.

- Historical & Empirical Analysis:
None

- Logical Deduction of Conditions ($C$) (multiple conditions can be deduced):
    condition 1:
        The website needs to have a search bar.
    condition 2:
        The website needs to have a database of indexed content.
    condition 3:
        The website needs to have a search algorithm or function implemented.
    condition 4:
        The website needs to have a user interface that allows users to input
        search queries.
    condition 5:
        The website needs to have a backend system that processes search
        queries and retrieves relevant results.

- Entity/Label Recognition of Conditions:
["Website search bar", "Indexed content database", "Search algorithm/
function", "User interface for search queries", "Backend system for query
processing"]

- Quality Assessment ($Q$) (do not use symbols):
    The transition from $A$ to $B$ would be considered efficient if the search
    capabilities are implemented with minimal resource usage.
    The transition would be considered effective if the website successfully
    provides accurate search results.
    Safety and risks should be assessed to ensure user privacy and data
    security during the transition.
    Feedback mechanisms should be incorporated to continuously improve the
    search capabilities based on user feedback.

- Iterative Evaluation:
None"""


# Generate expected dictionary of conditions and quality
def generate_expected_content():
    return {
        "conditions": {
            "condition 1": "The website needs to have a search bar.",
            "condition 2": (
                "The website needs to have a database of indexed content."
            ),
            "condition 3": (
                "The website needs to have a search algorithm or function "
                "implemented."
            ),
            "condition 4": (
                "The website needs to have a user interface that allows users "
                "to input\n        search queries."
            ),
            "condition 5": (
                "The website needs to have a backend system that processes "
                "search\n        queries and retrieves relevant results."
            ),
        },
        "labels": [
            "Website search bar",
            "Indexed content database",
            "Search algorithm/\nfunction",
            "User interface for search queries",
            "Backend system for query\nprocessing",
        ],
        "evaluate_quality": (
            "The transition from $A$ to $B$ would be considered efficient if "
            "the search\n    capabilities are implemented with minimal "
            "resource usage.\n    The transition would be considered "
            "effective if the website successfully\n    provides accurate "
            "search results.\n    Safety and risks should be assessed to"
            " ensure user privacy and data\n    security during the "
            "transition.\n    Feedback mechanisms should be incorporated "
            "to continuously improve the\n    search capabilities based on"
            " user feedback."
        ),
    }
