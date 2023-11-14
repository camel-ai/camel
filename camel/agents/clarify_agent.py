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
from typing import Any, Optional, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType


class TaskClarifyAgent(ChatAgent):
    r"""An agent that specify the initial task by interacting with the user.
    Args:
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="Task Clarifier",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You can ask questions to users for task clarification.",
        )
        super().__init__(system_message, model, model_config)

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def run(
        self,
        task_prompt: Union[str, TextPrompt],
        model: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> str:
        r"""Initiate multi rounds of interaction
        with the user to clarify the task.
        Args:
            task_prompt (Union[str, TextPrompt]):
                The prompt that needs to be clarified.
            model (ModelType, optional):
                The type of model to use for the agent.
                (default: :obj:`ModelType.GPT_3_5_TURBO`)
            model_config (Any, optional): The configuration for the model.
                (default: :obj:`None`)
        Returns:
            str: The clarified prompt.
        """

        clarify_prompt = TextPrompt(
            "You are a task clarifier agent, and you are going to clarify " +
            "the task with the user by interacting with users " +
            "for multiple rounds.\n" +
            "You can generate context aware questions that " +
            "target the ambiguities or generalities in the task prompt: " +
            f"{task_prompt}\n. Please remember you only interact with " +
            "the user with one question at a time.\n")

        clarify_messages = []
        print(f"The input task prompt is: {task_prompt}\n")
        # specified_agent = TaskSpecifyAgent()
        question_answer_pairs = {}

        while True:
            task_msg = BaseMessage.make_user_message(
                role_name="Task Clarifier", content=clarify_prompt)

            task_response = self.step(task_msg)

            if "Nothing more to clarify." in task_response.msgs[0].content:
                print("Nothing more to clarify.")
                break

            question = task_response.msgs[-1].content
            print(f"\n{question}")
            print('(answer in text and press Enter, or "c" to move on)\n')
            print("Answer: ")
            answer = input()
            if not answer or answer == "c":
                print("Nothing more to clarify.\n")
                # print(f"Clarified task prompt:{clarify_messages}")

                for i in range(0, len(clarify_messages), 2):
                    question = clarify_messages[i].content
                    answer = clarify_messages[i + 1].content
                    question_answer_pairs[question] = answer

                # print(f"Question-answer pairs: {question_answer_pairs}")
                # clarified_prompt = specified_agent.run(question_answer_pairs,
                #                                        task_prompt)
                # print(f"Clarified task prompt: {clarified_prompt}")
                return question_answer_pairs

            question_msg = BaseMessage.make_user_message(
                role_name="Task Classifier", content=f"{question}")
            self.submit_message(question_msg)
            clarify_messages.append(question_msg)

            answer_msg = BaseMessage.make_user_message(
                role_name="Human Explainer", content=f"{answer}")
            self.submit_message(answer_msg)
            clarify_messages.append(answer_msg)

        for i in range(0, len(clarify_messages), 2):
            question = clarify_messages[i].content
            answer = clarify_messages[i + 1].content
            question_answer_pairs[question] = answer

        # clarified_prompt = specified_agent.run(question_answer_pairs,
        #                                        task_prompt)
        # print(f"Clarified task prompt: {clarified_prompt}")
        return question_answer_pairs


if __name__ == "__main__":
    task_prompt = "Develop a trading bot for stock market"
    task_clarify_agent = TaskClarifyAgent()
    clarify_dict = task_clarify_agent.run(task_prompt=task_prompt)
    print(f"Clarified question answer pairs: {clarify_dict}")
