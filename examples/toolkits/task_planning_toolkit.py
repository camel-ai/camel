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
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.tasks import Task
from camel.toolkits.task_planning_toolkit import TaskPlanningToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Initialize the ThinkingToolkit
task_planning_toolkit = TaskPlanningToolkit()
tools = task_planning_toolkit.get_tools()

# Set up the ChatAgent with thinking capabilities
sys_prompt = TextPrompt(
    """You are a helpful assistant that can decompose a task or 
    re-plan a task when it's already decomposed into sub-tasks and its 
    sub-tasks are not relevant or aligned with the goal of the main task.
    Please use the tools to decompose or re-plan the task."""
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

user_msg = user_prompt.format(
    task_id=main_task.id,
    task_content=main_task.content,
)

agent = ChatAgent(sys_prompt, model=model, tools=tools)

response = agent.step(user_msg)

print("Final result of decomposed task:\n", response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

"""
Example: Problem Solving with TaskPlanning Toolkit
===============================================================================
Final result of decomposed task:
 Here is the main task and its decomposed subtasks:

### Main Task:
- **ID:** 1
- **Content:** Write a research paper on AI ethics

### Subtasks:
1. **ID:** 1.0 - Research the history of AI ethics
2. **ID:** 1.1 - Identify key ethical issues in AI
3. **ID:** 1.2 - Review existing literature on AI ethics
4. **ID:** 1.3 - Conduct interviews with experts in the field
5. **ID:** 1.4 - Draft the paper outline
6. **ID:** 1.5 - Write the introduction
7. **ID:** 1.6 - Write the body sections
8. **ID:** 1.7 - Write the conclusion
9. **ID:** 1.8 - Edit and proofread the paper
10. **ID:** 1.9 - Prepare for submission

These subtasks are aligned with the goal of writing a research paper on AI 
ethics. If you need any further adjustments or additional tasks, feel free to 
ask!

Tool calls:
[ToolCallingRecord(tool_name='decompose_task', args={'original_task_content': 
'Write a research paper on AI ethics', 'sub_task_contents': ['Research the 
history of AI ethics', 'Identify key ethical issues in AI', 'Review existing 
literature on AI ethics', 'Conduct interviews with experts in the field', 
'Draft the paper outline', 'Write the introduction', 'Write the body 
sections', 'Write the conclusion', 'Edit and proofread the paper', 'Prepare 
for submission'], 'original_task_id': '1'}, result=[Task(id='1.0', 
content='Research the history of AI ethics', state='OPEN'), Task(id='1.1', 
content='Identify key ethical issues in AI', state='OPEN'), Task(id='1.2', 
content='Review existing literature on AI ethics', state='OPEN'), Task(id='1.
3', content='Conduct interviews with experts in the field', state='OPEN'), Task
(id='1.4', content='Draft the paper outline', state='OPEN'), Task(id='1.5', 
content='Write the introduction', state='OPEN'), Task(id='1.6', content='Write 
the body sections', state='OPEN'), Task(id='1.7', content='Write the 
conclusion', state='OPEN'), Task(id='1.8', content='Edit and proofread the 
paper', state='OPEN'), Task(id='1.9', content='Prepare for submission', 
state='OPEN')], tool_call_id='call_WYeAEByDSR6PtlDiC5EmiTjZ')]
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
print(response.info['tool_calls'])

"""
Examples: Problem Solving with TaskPlanning Toolkit
===============================================================================
Final result of re_plan task:
 The main task is to write a research paper on AI ethics, and the irrelevant 
 subtasks have been replaced with the following relevant subtasks:

1. **Research the history of AI ethics** (ID: 1.0)
2. **Identify key ethical issues in AI** (ID: 1.1)
3. **Review existing literature on AI ethics** (ID: 1.2)
4. **Conduct interviews with experts in the field** (ID: 1.3)
5. **Draft the paper outline** (ID: 1.4)
6. **Write the introduction** (ID: 1.5)
7. **Write the body sections** (ID: 1.6)
8. **Write the conclusion** (ID: 1.7)
9. **Edit and proofread the paper** (ID: 1.8)

These subtasks are now aligned with the goal of completing the research paper 
on AI ethics.

Tool calls:
[ToolCallingRecord(tool_name='replan_tasks', args={'original_task_content': 
'Write a research paper on AI ethics', 'sub_task_contents': ['Research the 
history of AI ethics', 'Identify key ethical issues in AI', 'Review existing 
literature on AI ethics', 'Conduct interviews with experts in the field', 
'Draft the paper outline', 'Write the introduction', 'Write the body 
sections', 'Write the conclusion', 'Edit and proofread the paper'], 
'original_task_id': '1'}, result=[Task(id='1.0', content='Research the history 
of AI ethics', state='OPEN'), Task(id='1.1', content='Identify key ethical 
issues in AI', state='OPEN'), Task(id='1.2', content='Review existing 
literature on AI ethics', state='OPEN'), Task(id='1.3', content='Conduct 
interviews with experts in the field', state='OPEN'), Task(id='1.4', 
content='Draft the paper outline', state='OPEN'), Task(id='1.5', 
content='Write the introduction', state='OPEN'), Task(id='1.6', content='Write 
the body sections', state='OPEN'), Task(id='1.7', content='Write the 
conclusion', state='OPEN'), Task(id='1.8', content='Edit and proofread the 
paper', state='OPEN')], tool_call_id='call_37UsfFNonx7rbmGWeJePbmbo')]
===============================================================================
"""
