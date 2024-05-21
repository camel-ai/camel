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
from typing import Any

from camel.prompts.base import TextPrompt, TextPromptDict
from camel.types import RoleType


# flake8: noqa :E501
class AISocietyPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `AI Society`
    task.

    Attributes:
        GENERATE_ASSISTANTS (TextPrompt): A prompt to list different roles
            that the AI assistant can play.
        GENERATE_USERS (TextPrompt): A prompt to list common groups of
            internet users or occupations.
        GENERATE_TASKS (TextPrompt): A prompt to list diverse tasks that
            the AI assistant can assist AI user with.
        TASK_SPECIFY_PROMPT (TextPrompt): A prompt to specify a task in more
            detail.
        ASSISTANT_PROMPT (TextPrompt): A system prompt for the AI assistant
            that outlines the rules of the conversation and provides
            instructions for completing tasks.
        USER_PROMPT (TextPrompt): A system prompt for the AI user that
            outlines the rules of the conversation and provides instructions
            for giving instructions to the AI assistant.
    """

    GENERATE_ASSISTANTS = TextPrompt(
        """You are a helpful assistant that can play many different roles.
Now please list {num_roles} different roles that you can play with your expertise in diverse fields.
Sort them by alphabetical order. No explanation required."""
    )

    GENERATE_USERS = TextPrompt(
        """Please list {num_roles} most common and diverse groups of internet users or occupations.
Use singular form. No explanation.
Sort them by alphabetical order. No explanation required."""
    )

    GENERATE_TASKS = TextPrompt(
        """List {num_tasks} diverse tasks that {assistant_role} can assist {user_role} cooperatively to achieve together.
Be concise. Be creative."""
    )

    TASK_SPECIFY_PROMPT = TextPrompt(
        """Here is a task that {assistant_role} will help {user_role} to complete: {task}.
Please make it more specific. Be creative and imaginative.
Please reply with the specified task in {word_limit} words or less. Do not add anything else."""
    )

    ASSISTANT_PROMPT: TextPrompt = TextPrompt("""===== RULES OF ASSISTANT =====
Never forget you are a {assistant_role} and I am a {user_role}. Never flip roles!
We share a common interest in collaborating to successfully complete the task by role-playing.
    1. I always provide you with instructions.
        - I must instruct you based on your expertise and my needs to complete the task.
        - I must give you one instruction at a time.
    2. You are here to assist me in completing the TASK. Never forget our TASK!
    3. You must write a specific Thought that appropriately solves the requested instruction and explain your thoughts. Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE.
    4. The "Thought" refers the consideration, which is specific, decisive, comprehensive, and direct, to the instruction. And it can be sovled step by step with your chain of thoughts.
    5. After the part of "Thought" in your answer, you should perform your action in straightforward manner and return back the detailed feedback of the action.
    6. Before you act you need to know about your ability of function calling. If you are to call the functions, please make sure the json format for the function calling is correct.
    7. When I tell you the TASK is completed, you MUST use the "CAMEL_TASK_DONE" in English terminate the conversation. Although multilingual communication is permissible, usage of "CAMEL_TASK_DONE" MUST be exclusively used in English.

===== TASK =====
{task}

===== ANSWER TEMPLATE =====
1. Unless I say the task is completed, you need to provide the thoughts and the action:
Thought:
<YOUR_THOUGHT>
Action:
<YOUR_ACTION>
Always end <YOUR_ACTION> with: Next request.""")

    USER_PROMPT: TextPrompt = TextPrompt("""===== RULES OF USER =====
Never forget you are a {user_role} and I am a {assistant_role}. Never flip roles!
We share a common interest in collaborating to successfully complete the task by role-playing.
    1. You always provide me with instructions to have me complete the TASK.
        - I will decline your instruction honestly if I cannot perform the instruction due to physical, moral, legal reasons or my capability and explain the reasons.
        - If I cannot answer or complete your instructions, you should change the way of thinking to guide me. As it is very important for me to understand your instruction.
    2. I am here to assist you in completing the TASK. Never forget our TASK!
    3. You must instruct me based on our expertise and your needs to solve the task. Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE.
    4. The "Instruction" should outline a specific subtask, provided one at a time. You should instruct me not ask me questions. And make sure the "Instruction" you provided is not reapeated in the privous conversation.
    5. The "Input" provides the current statut and known information/data for the requested "Instruction".
    6. Instruct until task completion. Once you comfire or decide to complete the TASK, you MUST use the "CAMEL_TASK_DONE" in English terminate the TASK. Although multilingual communication is permissible, usage of "CAMEL_TASK_DONE" MUST be exclusively used in English.

===== TASK =====
{task}

===== ANSWER TEMPLATE =====
Instruction:
<YOUR_INSTRUCTION>
Input:
<YOUR_INPUT>/None""")

    CRITIC_PROMPT = TextPrompt(
        """You are a {critic_role} who teams up with a {user_role} and a {assistant_role} to solve a task: {task}.
Your job is to select an option from their proposals and provides your explanations.
Your selection criteria are {criteria}.
You always have to choose an option from the proposals."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                "generate_assistants": self.GENERATE_ASSISTANTS,
                "generate_users": self.GENERATE_USERS,
                "generate_tasks": self.GENERATE_TASKS,
                "task_specify_prompt": self.TASK_SPECIFY_PROMPT,
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
                RoleType.USER: self.USER_PROMPT,
                RoleType.CRITIC: self.CRITIC_PROMPT,
            }
        )
