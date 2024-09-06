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
from camel.prompts import TextPrompt

# ruff: noqa: E501
CREATE_NODE_PROMPT = TextPrompt(
    """You need to use the given information to create a new workforce for solving the category of tasks of the given one.
The content of the given task is:

{content}

Following is the information of the existing workforces. The format is <ID>: <description>.

{child_nodes_info}

You must return the following information:
1. The role of the agent working in the workforce, e.g. "programmer", "researcher", "product owner". This should be enclosed within the <role></role> tags.
2. The system message that will be sent to the agent, enclosed within the <sys_msg></sys_msg> tags.
3. The description of the workforce, enclosed within the <description></description> tags.

Also, all of the info should be enclosed within a <workforce> tag. For example:

<workforce>
<role>programmer</role>
<sys_msg>You are a python programmer.</sys_msg>
<description>a python programmer.</description>
</workforce>

You should ensure that the workforce created is capable of solving all the tasks in the same category as the given one, don't make it too specific.
Also, there should be no big overlap between the new workforce and the existing ones.
The information returned should be concise and clear. Each pair of tag can only appear once.
"""
)

ASSIGN_TASK_PROMPT = TextPrompt(
    """You need to assign the task to a workforce.
The content of the task is:

{content}

Following is the information of the existing workforces. The format is <ID>: <description>.

{child_nodes_info}

You must return the ID of the workforce that you think is most capable of doing the task. The ID should be enclosed within the <id></id> tags, for example:

<id>1</id>
"""
)

PROCESS_TASK_PROMPT = TextPrompt(
    """You need to process one given task.
Here are results of some prerequisite tasks that you can refer to:

==============================
{dependency_tasks_info}
==============================

The content of the task that you need to do is:

==============================
{content}
==============================

You must return the result of the given task. The result should be enclosed within the <result></result> tags, for example:

==============================
<result>The weather today in New York City is partly cloudy with a high of 75°F (24°C) and a low of 59°F (15°C).</result>
==============================

If you think you are not capable of COMPLETELY finish the task, you need to return <failed></failed> tags.
"""
)


ROLEPLAY_PROCESS_TASK_PROMPT = TextPrompt(
    """You need to process the task. It is recommended that tools be actively called when needed.
Here are results of some prerequisite tasks that you can refer to:

{dependency_task_info}

The content of the task that you need to do is:

{content}

You must return the result of the given task.
"""
)

ROLEPLAY_SUMMARIZE_PROMPT = TextPrompt(
    """For this scenario, the roles of the user is {user_role} and role of the assistant is {assistant_role}.
Here is the content of the task they are trying to solve:

{task_content}

Here is their chat history on the task:

==============================
{chat_history}
==============================

Now you should summarize the scenario and return the result of the task.
The result should be enclosed within the <result></result> tags, for example:

<result>The weather today in New York City is partly cloudy with a high of 75°F (24°C) and a low of 59°F (15°C).</result>

You should keep important details and remove unnecessary information.
If you think you are not capable of COMPLETELY finish the task, you need to return <failed></failed> tags.
"""
)

WF_TASK_DECOMPOSE_PROMPT = r"""You need to split the given task into 
subtasks according to the workers available in the group.
The content of the task is:

==============================
{content}
==============================

Following are the available workers, given in the format <ID>: <description>.

==============================
{child_nodes_info}
==============================

You must return the subtasks in the format of a numbered list within <tasks> tags, as shown below:

<tasks>
<task>Subtask 1</task>
<task>Subtask 2</task>
</tasks>

Though it's not a must, you should try your best effort to make each subtask 
achievable for a worker. The tasks should be clear and concise.
"""
