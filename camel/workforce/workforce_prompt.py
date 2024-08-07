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
2. The system message that will be sent to the agent, enclosed within the <system></system> tags.
3. The description of the workforce, enclosed within the <description></description> tags.

Also, all of the info should be enclosed within a <workforce> tag. For example:

<workforce>
<role>programmer</role>
<system>You are a python programmer.</system>
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
    """You need to process the task. It is recommended that tools be actively called when needed.
The content of the task is:

{content}

The type of the task is:

{type}

To process this task, here is some information on several dependent tasks:

{dependency_task_info}

You must return the result of the given task. The result should be enclosed within the <result></result> tags, for example:

<result>Today, you requested information about the current weather conditions. The weather today in New York City is partly cloudy with a high of 75°F (24°C) and a low of 59°F (15°C). There is a 10 percent chance of rain with winds coming from the northeast at 5 mph. Humidity levels are at 60%. It's a perfect day to spend some time outdoors, perhaps in one of the city's beautiful parks.</result>

if you are not able to process the task, you need to return <failed></failed> tags.
"""
)


ROLEPLAY_PROCESS_TASK_PROMPT = TextPrompt(
    """You need to process the task. It is recommended that tools be actively called when needed.
The content of the task is:

{content}

The type of the task is:

{type}

To process this task, here is some information on several dependent tasks:

{dependency_task_info}

You must return the result of the given task.

"""
)

# TODO: improve prompt quality
ROLEPLAY_SUMMERIZE_PROMPT = TextPrompt(
    """You need to process the task.
The content of the task is:

{content}

The type of the task is:

{type}

To process this task, here are the chat history of AI user and AI assistant:

{chat_history}

You must summerize the chat history of the return the result of the given task. The result should be enclosed within the <result></result> tags, for example:

<result>Today, you requested information about the current weather conditions. The weather today in New York City is partly cloudy with a high of 75°F (24°C) and a low of 59°F (15°C). There is a 10 percent chance of rain with winds coming from the northeast at 5 mph. Humidity levels are at 60%. It's a perfect day to spend some time outdoors, perhaps in one of the city's beautiful parks.</result>

if you are not able to process the task, you need to return <failed></failed> tags.
"""
)
