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

        clarify_prompt_base = """You are a task clarifier agent, and you should obey the RULES OF TASK CLARIFICATION.
==== RULES OF TASK CLARIFICATION ====
1. Contextual Interaction: Engage with the user over multiple rounds, focusing each interaction on clarifying ambiguities or generalities in the user's TASK.
2. Adaptive Questioning: Generate context-aware questions that address specific uncertainties in the TASK. If the user's response is non-informative (e.g., 'null'), acknowledge this and adapt your next question to gently guide the user back towards providing the needed information.
3. Single-Question Focus: Limit your interaction to one clarifying question at a time, ensuring it is directly related to the TASK and tailored to the user's previous response.
4. Non-Answer Handling: If the user's response does not provide the required clarification (like responding with 'null'), your follow-up question should:
- Acknowledge the user's previous response (or lack of it).
- Reframe or simplify the original question, or ask a related but simpler question that might indirectly lead to the necessary clarification.
- Maintain focus on the original task's ambiguities or generalities.
5. Avoid Providing Answers: Your role is not to provide answers or solutions but to facilitate clarity through your questions.
6. Template Adherence with Flexibility: Follow the structured "ANSWER TEMPLATE" for your responses, filling in the blanks appropriately based on the user's input. This template allows for acknowledgment of non-informative responses and rephrasing of follow-up questions to stay on track with the task clarification.
7. Limited Follow-Ups: You can follow up if the user's response is not satisfactory, but the number of follow-ups is limited. Be mindful of the user's intention and the clarity of their responses.
8. Use Reference Material Wisely: Refer to the "QUESTION_ANSWER PAIR" for guidance, but ensure your questions are unique and not repetitive.

===== TASK =====
{task_prompt}

===== ANSWER TEMPLATE =====
Q:\n<BLANK, your question>"""  # noqa: E501
        clarify_prompt_base = TextPrompt(clarify_prompt_base)
        clarify_prompt_base = clarify_prompt_base.format(
            task_prompt=task_prompt)

        print("clarify_prompt_base: ", clarify_prompt_base)

        print(f"The input task prompt is: {task_prompt}\n")

        while True:
            # Concatenate the base prompt with the formatted Q&A pairs
            qa_pairs_formatted = (
                "===== QUESTION_ANSWER PAIRS =====\n" +
                "\n".join(f"Q: {q}\nA: {a}"
                          for q, a in question_answer_pairs.items()))
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

        insight = insight_agent.InsightAgent()
        insights_str = insight.run(clarify_dict)

        return insights_str


if __name__ == "__main__":
    task_prompt = "Develop a trading bot for stock market"
    task_clarify_agent = TaskClarifyAgent()
    clarify_dict = task_clarify_agent.run(task_prompt=task_prompt)
    print(f"Clarified question answer pairs: {clarify_dict}\n")
