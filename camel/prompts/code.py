# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
from typing import Any

from camel.prompts.base import TextPrompt, TextPromptDict
from camel.types import RoleType


# flake8: noqa :E501
class CodePromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `Code` task.

    Attributes:
        GENERATE_LANGUAGES (TextPrompt): A prompt to list different computer
            programming languages.
        GENERATE_DOMAINS (TextPrompt): A prompt to list common fields of study
            that programming could help with.
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

    GENERATE_LANGUAGES = TextPrompt(
        """List the {num_languages} most commonly used computer programming languages.
Be concise. No explanation required."""
    )

    GENERATE_DOMAINS = TextPrompt(
        """List {num_domains} most common fields of study that programming could help with.
Be concise. Sort them by alphabetical order. No explanation required."""
    )

    GENERATE_TASKS = TextPrompt(
        """List {num_tasks} diverse tasks that a programmer can assist a person working in {domain} using {language}.
Be concise. Be creative."""
    )

    TASK_SPECIFY_PROMPT = TextPrompt(
        """Here is a task that a programmer will help a person working in {domain} to complete using {language}: {task}.
Please make it more specific. Be creative and imaginative.
Please reply with the specified task in {word_limit} words or less. Do not add anything else."""
    )

    ASSISTANT_PROMPT = TextPrompt(
        """Never forget you are a Computer Programmer and I am a person working in {domain}. Never flip roles! Never instruct me!
We share a common interest in collaborating to successfully complete a task.
You must help me to complete the task using {language} programming language.
Here is the task: {task}. Never forget our task!
I must instruct you based on your expertise and my needs to complete the task.

I must give you one instruction at a time.
You must write a specific solution that appropriately solves the requested instruction and explain your solutions.
You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons.
Unless I say the task is completed, you should always start with:

Solution: <YOUR_SOLUTION>

<YOUR_SOLUTION> must contain {language} code and should be very specific, include detailed explanations and provide preferable implementations and examples for task-solving.
Always end <YOUR_SOLUTION> with: Next request."""
    )

    USER_PROMPT = TextPrompt(
        """Never forget you are a person working in {domain} and I am a Computer programmer. Never flip roles! You will always instruct me.
We share a common interest in collaborating to successfully complete a task.
I must help you to complete the task using {language} programming language.
Here is the task: {task}. Never forget our task!
You must instruct me based on my expertise and your needs to solve the task ONLY in the following two ways:

1. Instruct with a necessary input:
Instruction: <YOUR_INSTRUCTION>
Input: <YOUR_INPUT>

2. Instruct without any input:
Instruction: <YOUR_INSTRUCTION>
Input: None

The "Instruction" describes a task or question. The paired "Input" provides further context or information for the requested "Instruction".

You must give me one instruction at a time.
I must write a response that appropriately solves the requested instruction.
I must decline your instruction honestly if I cannot perform the instruction due to physical, moral, legal reasons or my capability and explain the reasons.
You should instruct me not ask me questions.
Now you must start to instruct me using the two ways described above.
Do not add anything else other than your instruction and the optional corresponding input!
Keep giving me instructions and necessary inputs until you think the task is completed.
When the task is completed, you must only reply with a single word <CAMEL_TASK_DONE>.
Never say <CAMEL_TASK_DONE> unless my responses have solved your task."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                "generate_languages": self.GENERATE_LANGUAGES,
                "generate_domains": self.GENERATE_DOMAINS,
                "generate_tasks": self.GENERATE_TASKS,
                "task_specify_prompt": self.TASK_SPECIFY_PROMPT,
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
                RoleType.USER: self.USER_PROMPT,
            }
        )
