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

from camel.agents import ChatAgent, insight_agent
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

    def run(
        self,
        task_prompt: Union[str, TextPrompt],
    ) -> Union[str, TextPrompt]:
        r"""Initiate multi rounds of interaction
        with the user to clarify the task.

        Args:
            task_prompt (Union[str, TextPrompt]):
                The prompt that needs to be clarified.

        Returns:
            Union[str, TextPrompt]: The clarified task prompt.
        """
        question_answer_pairs = {}

        clarify_prompt_base = TextPrompt(
            "You are a task clarifier agent, and your role is to clarify " +
            "the task by interacting with users over multiple rounds. " +
            "You will generate context-aware questions that target " +
            "ambiguities or generalities in the user's task prompt: " +
            f"{task_prompt}.\n" +
            "Your interaction with the user should be limited to one " +
            "question at a time. This should follow the format: " +
            "Q:\n<Your Question Here>\n" +
            "Remember, you are not required to provide answers to the user, " +
            "so avoid including any response or answer in your question. " +
            "Your focus should be solely on crafting a clarifying " +
            "question based on the task prompt.\n" +
            "Refer to previous question and answer pairs for context, " +
            "but do not include any answers in your output.\n" +
            "If you are not satisfied with the user's answer, you can " +
            "'follow up' with the user, but the number of times you can " +
            "'follow up' is limited. The limit depends on the user's answer " +
            "and their intention. If you are satisfied, proceed to the next " +
            "question.\n")

        print(f"The input task prompt is: {task_prompt}\n")

        while True:
            # Concatenate the base prompt with the formatted Q&A pairs
            qa_pairs_formatted = "\n".join(
                f"Q: {q}\nA: {a}" for q, a in question_answer_pairs.items())
            clarify_prompt = clarify_prompt_base + qa_pairs_formatted

            task_msg = BaseMessage.make_user_message(
                role_name="Task Clarifier", content=clarify_prompt)

            response = self.step(task_msg)

            if response.terminated:
                raise RuntimeError("The clarification of the task failed.\n" +
                                   f"Error:\n{response.info}")
            msg = response.msg

            if "Nothing more to clarify." in msg.content:
                print("Nothing more to clarify.")
                break
            question = msg.content

            print(f"\n{question}")
            print('(answer in text and press Enter, or "c" to move on)\n')
            print("Answer: ")
            answer = input()

            question_answer_pairs[question] = answer

            if not answer or answer == "c":
                print("Nothing more to clarify.\n")
                return question_answer_pairs

        return question_answer_pairs


if __name__ == "__main__":
    task_prompt = "Develop a trading bot for stock market"
    task_clarify_agent = TaskClarifyAgent()
    clarify_dict = task_clarify_agent.run(task_prompt=task_prompt)
    print(f"Clarified question answer pairs: {clarify_dict}\n")
    insight_agent = insight_agent.InsightAgent()
    insights_str = insight_agent.run(clarify_dict)
    print(f"Insights: {insights_str}")
