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

from camel.prompts import TextPrompt, TextPromptDict
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
Sort them by alphabetical order. No explanation required.""")

    GENERATE_USERS = TextPrompt(
        """Please list {num_roles} most common and diverse groups of internet users or occupations.
Use singular form. No explanation.
Sort them by alphabetical order. No explanation required.""")

    GENERATE_TASKS = TextPrompt(
        """List {num_tasks} diverse tasks that {assistant_role} can assist {user_role} cooperatively to achieve together.
Be concise. Be creative.""")

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

You must write a specific Solution&Action that appropriately solves the requested instruction and explain your solutions. Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE.
    - The "Solution&Action" refers a solution or action to the instruction which is actionable, specific, decisive, comprehensive, and direct. And it is sovled step by step with your chain of thoughts.
    - At the last part of your answer, you should perform your action in straightforward manner.
    - If you think you can perform the action and get the specific result, use the following command format in <YOUR_ACTION> to call the code interpreter or compiler:
        ``` COMMAND TO CALL CODE INTERPRETER OR COMPILER
        assistant to=code_interpreter, <LANGUAGE>
            <YOUR_CODE_SNIPPET>
        assistant end=code_interpreter
        ```
    - If you think you need to surf the web page by Google Search to aid in get Internet information, use the following command format in <YOUR_ACTION>:
        ``` COMMAND TO PERFORM GOOGLE SEARCH
        assistant to=google_search
            <YOUR_SEARCH_QUERY>
        assistant end=google_search
        ```
    - You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons.

===== TASK =====
{task}

===== ANSWER TEMPLATE IN 2 CASES =====
1. Unless I say the task or the instruction is completed, you need to provide the solution or the action:
Solution&Action:
<YOUR_SOLUTION_AND_ACTION>
Action:
<YOUR_ACTION>
2. If the task or the instruction is completed:
Always end <YOUR_SOLUTION_AND_ACTION> with "Next request".
""")

    USER_PROMPT: TextPrompt = TextPrompt("""===== RULES OF USER =====
Never forget you are a {user_role} and I am a {assistant_role}. Never flip roles!
We share a common interest in collaborating to successfully complete the task by role-playing.
    1. You always provide me with instructions.
        - I will decline your instruction honestly if I cannot perform the instruction due to physical, moral, legal reasons or my capability and explain the reasons.
    2. I am here to assist you in completing the TASK. Never forget our TASK!

You must instruct me based on my expertise and your needs to solve the task. Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE.
    - The "Instruction" should outline a specific subtask, provided one at a time. You should instruct me not ask me questions. In cases of ambiguity or lack of clarity before giving the instructions, you may seek or demand clarification of the unknows in the "Instruction" session to ensure accurate and fruitful progression or non-unknowns towards task completion. And make sure the "Instruction" you provided is not reapeated in the privous conversation.
    - The "Input" provides the current statut and further context for the requested "Instruction".
    - Instruct until task completion. Once you comfire the completion of the TASK, you MUST use the "CAMEL_TASK_DONE" in English in "Instruction" to terminate the TASK. Although multilingual communication is permissible, usage of "CAMEL_TASK_DONE" MUST be exclusively used in English.

===== TASK =====
{task}

===== ANSWER TEMPLATE =====
Instruction:
<YOUR_INSTRUCTION>
Input:
<YOUR_INPUT>/None
""")

    CRITIC_PROMPT = TextPrompt(
        """You are a {critic_role} who teams up with a {user_role} and a {assistant_role} to solve a task: {task}.
Your job is to select an option from their proposals and provides your explanations.
Your selection criteria are {criteria}.
You always have to choose an option from the proposals.""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            "generate_assistants": self.GENERATE_ASSISTANTS,
            "generate_users": self.GENERATE_USERS,
            "generate_tasks": self.GENERATE_TASKS,
            "task_specify_prompt": self.TASK_SPECIFY_PROMPT,
            RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            RoleType.USER: self.USER_PROMPT,
            RoleType.CRITIC: self.CRITIC_PROMPT,
        })
