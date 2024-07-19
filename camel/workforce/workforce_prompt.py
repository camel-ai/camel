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
CREATE_WF_PROMPT = TextPrompt(
    """You need to use the given information to create a new workforce for solving the category of tasks of the given one.
The content of the given task is:

{content}

Following is the information of the existing workforces. The format is <ID>: <description>.

{workforces_info}

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

{workforces_info}

You must return the ID of the workforce that you think is most capable of doing the task. The ID should be enclosed within the <id></id> tags, for example:

<id>1</id>
"""
)
