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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.tasks import Task
from camel.toolkits.task_planning_toolkit import TaskPlanningToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Initialize the ThinkingToolkit
task_planning_toolkit = TaskPlanningToolkit()
tools = task_planning_toolkit.get_tools()

# Set up the ChatAgent with thinking capabilities
sys_prompt = TextPrompt(
    """You are a helpful assistant that can decompose a task or 
    re_plan a task when it's already decomposed into subTasks and its subTasks
    are not relevant or aligned with the goal of the main task.
    Please use the tools to decompose or re_plan the task."""
)
user_prompt = TextPrompt(
    """Here is the main task:
        - ID: {task_id}
        - Content: {task_content}

        Here are the current subtasks:
        {subtasks_str}"""
)

# Example: Task Decompose with TaskPlanning Toolkit
main_task = Task(content="Write a research paper on AI ethics", id="1")

agent = ChatAgent(sys_prompt, model=model, tools=tools)

response = agent.step(main_task.content)

print("Final result of decomposed task:\n", response.msgs[0].content)
print("\nTool calls:")
print(str(response.info['tool_calls'])[:1000])

"""
Example: Problem Solving with TaskPlanning Toolkit
===============================================================================
Final result of decomposed task:
 The task of writing a research paper on AI ethics has been decomposed into the
 following sub-tasks:

1. **Conduct a literature review on AI ethics**  
   - Gather and analyze existing research and publications on AI ethics.

2. **Identify key ethical issues in AI**  
   - Highlight major ethical concerns such as bias, privacy, accountability,
   and transparency.

3. **Analyze case studies of AI ethics violations**  
   - Examine real-world examples where AI ethics were compromised.

4. **Develop a framework for ethical AI practices**  
   - Propose guidelines or principles for ethical AI development and
   deployment.

5. **Write the introduction section of the paper**  
   - Introduce the topic, its significance, and outline the paper's structure.

6. **Write the methodology section of the paper**  
   - Describe the research methods used to gather and analyze data.

7. **Write the findings and analysis section of the paper**
   - Present the results of the literature review, case studies, and framework
   development.

8. **Write the conclusion and recommendations section of the paper**
   - Summarize key findings and suggest future directions or policy
   recommendations.

9. **Revise and edit the paper for clarity and coherence**
   - Ensure the paper is well-structured, free of errors, and communicates
   ideas effectively.

Would you like to proceed with any of these sub-tasks or modify the plan?

Tool calls:
[
    ToolCallingRecord(
        tool_name='decompose_task',
        args={
            'original_task_content': 'Write a research paper on AI ethics',
            'sub_task_contents': [
                'Conduct a literature review on AI ethics',
                'Identify key ethical issues in AI',
                'Analyze case studies of AI ethics violations',
                'Develop a framework for ethical AI practices',
                'Write the introduction section of the paper',
                'Write the methodology section of the paper',
                'Write the findings and analysis section of the paper',
                'Write the conclusion and recommendations section of the
                    paper',
                'Revise and edit the paper for clarity and coherence'
            ]
        },
        result=[
            Task(
                content='Conduct a literature review on AI ethics',
                id='96f3ea4b-6831-44c3-8fd3-c49680f7edaa.0',
                state=<TaskState.OPEN: 'OPEN'>,
                type=None,
                parent=Task(
                    content='Write a research paper on AI ethics',
                    id='96f3ea4b-6831-44c3-8fd3-c49680f7edaa',
                    state=<TaskState.OPEN: 'OPEN'>,
                    type=None,
                    parent=None,
                    subtasks=[...]
                ),
                subtasks=[],
                result='',
                failure_count=0,
                additional_info=None
            )
        ]
    )
]
===============================================================================

"""

# Example: Task Re-plan with TaskPlanning Toolkit
main_task.subtasks = [
    Task(content="do homework", id="1.1"),
    Task(content="go to school", id="1.2"),
]
subtasks_str = "\n".join(
    [f"- ID: {st.id}, Content: {st.content}" for st in main_task.subtasks]
)

user_msg = user_prompt.format(
    task_id=main_task.id,
    task_content=main_task.content,
    subtasks_str=subtasks_str,
)
response = agent.step(user_msg)
print("Final result of re_plan task:\n", response.msgs[0].content)
print("\nTool calls:")
print(str(response.info['tool_calls'])[:1000])

"""
Examples: Problem Solving with TaskPlanning Toolkit
===============================================================================

Final result of re_plan task:
 The subtasks for the main task **"Write a research paper on AI ethics"** have
    been successfully replanned. Here are the updated subtasks:

1. **Conduct a literature review on AI ethics to gather relevant sources.**
2. **Identify key ethical issues in AI, such as bias, privacy, and
    accountability.**
3. **Develop a thesis statement or central argument for the paper.**
4. **Outline the structure of the paper, including introduction, body, and
    conclusion.**
5. **Write the introduction, providing background and stating the thesis.**
6. **Write the body sections, each addressing a key ethical issue.**
7. **Write the conclusion, summarizing findings and suggesting future
    directions.**
8. **Revise and edit the paper for clarity, coherence, and academic rigor.**
9. **Format the paper according to academic standards (e.g., APA, MLA).**

These subtasks are now aligned with the goal of writing a comprehensive
    research paper on AI ethics. Let me know if you'd like to proceed with
    any specific subtask or make further adjustments!

Tool calls:
[
    ToolCallingRecord(
        tool_name='replan_tasks',
        args={
            'original_task_id': '1',
            'original_task_content': 'Write a research paper on AI ethics',
            'sub_task_contents': [
                'Conduct a literature review on AI ethics to gather relevant
                    sources.',
                'Identify key ethical issues in AI, such as bias, privacy, and
                    accountability.',
                'Develop a thesis statement or central argument for the
                    paper.',
                'Outline the structure of the paper, including introduction,
                    body, and conclusion.',
                'Write the introduction, providing background and stating the
                    thesis.',
                'Write the body sections, each addressing a key ethical
                    issue.',
                'Write the conclusion, summarizing findings and suggesting
                    future directions.',
                'Revise and edit the paper for clarity, coherence, and
                    academic rigor.',
                'Format the paper according to academic standards (e.g., APA,
                    MLA).'
            ]
        },
        result=[
            Task(
                content='Conduct a literature review on AI ethics to gather
                    relevant sources.',
                id='1.0',
                state=<TaskState.OPEN: 'OPEN'>,
                type=None,
                parent=Task(
                    content='Write a research paper on AI ethics',
                    id='1',
                    state=<TaskState.OPEN: 'OPEN'>,
                    type=None,
                    parent=None,
                    subtasks=[...]
                ),
                subtasks=[],
                result='',
                failure_count=0,
                additional_info=None
            )
        ]
    )
]
===============================================================================
"""
