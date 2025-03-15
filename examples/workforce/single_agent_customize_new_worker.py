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

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import GoogleMapsToolkit, WeatherToolkit
from camel.types import ModelPlatformType, ModelType


# Define a mock funtion as an external tool
def get_place_reviews(landmark: str) -> str:
    r"""It is a function to get place reviews for a landmark.
    Args:
        landmark (str): The name of the landmark.

    Returns:
        str: Reviews of the landmark.
    """
    mock_result = f"The reviews of {landmark} are great!"
    return mock_result


def main():
    # Set up traveler agent
    traveler_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Traveler",
            content="You can ask questions about your travel plans",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    # Set up a model for the new worker
    new_worker_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    workforce = Workforce(
        description='A travel group',
        new_worker_tools=[
            *WeatherToolkit().get_tools(),
            *GoogleMapsToolkit().get_tools(),
        ],
        new_worker_external_tools=[get_place_reviews],
        new_worker_agent_kwargs={"model": new_worker_model},
    )

    workforce.add_single_agent_worker("A traveler", worker=traveler_agent)

    # specify the task to be solved
    human_task = Task(
        content=("What was the exact weather in New York City now?"),
        id='0',
    )

    task = workforce.process_task(human_task)

    print('Final Result of Original task:\n', task.result)


if __name__ == "__main__":
    main()
