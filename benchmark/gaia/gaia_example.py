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
from benchmark.gaia import GAIABenchmark
from camel.agents import ChatAgent
from camel.messages import BaseMessage

task_prompt = """
        You are a general AI assistant. I will ask you a question. Report your 
        thoughts, and finish your answer with the following template: 
        FINAL ANSWER: [YOUR FINAL ANSWER].
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a 
        comma separated list of numbers and/or strings.
        If you are asked for a number, don't use comma to write your number 
        neither use units such as $ or percent sign unless specified otherwise.
        If you are asked for a string, don't use articles, neither 
        abbreviations (e.g. for cities), and write the digits in plain text 
        unless specified otherwise.
        If you are asked for a comma separated list, apply the above rules 
        depending of whether the element to be put in the list is a number or 
        a string.
        """.strip()
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content=task_prompt,
)
gaia = GAIABenchmark()
gaia.download()
agent = ChatAgent(system_message=sys_msg)
scores = gaia.eval(agent, ['all'], "validation")
print(scores)
