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
import textwrap

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.tasks import Task
from camel.toolkits import SEARCH_FUNCS
from camel.types import ModelPlatformType, ModelType
from camel.workforce import Workforce


def make_judge_system_message(
    persona: str, example_feedback: str, criteria: str
) -> BaseMessage:
    msg_content = textwrap.dedent(
        f"""\
        You are a judge in a hackathon.
        This is your persona: {persona}
        Here is an example feedback that you will give: {example_feedback}
        When evaluating projects, you must use the following criteria:
        {criteria}
        """
    )
    return BaseMessage.make_assistant_message(
        role_name="Judge",
        content=msg_content,
    )


def main():
    vc_persona = (
        'You are a venture capitalist who is obsessed with how projects can '
        'be scaled into "unicorn" companies. You peppers your speech with '
        'buzzwords like "disruptive," "synergistic," and "market penetration."'
        ' You do not concerned with technical details or innovation unless '
        'it directly impacts the business model.'
    )

    vc_example_feedback = (
        '"Wow, this project is absolutely disruptive in the blockchain-enabled'
        ' marketplace! I can definitely see synergistic applications in the '
        'FinTech ecosystem. The scalability is through the roof—this is '
        'revolutionary!'
    )

    vc_criteria = textwrap.dedent(
        """\
        ### **Applicability to Real-World Usage (1-4 points)**
        - **4**: The project directly addresses a significant real-world problem with a clear, scalable application.
        - **3**: The solution is relevant to real-world challenges but requires more refinement for practical or widespread use.
        - **2**: Some applicability to real-world issues, but the solution is not immediately practical or scalable.
        - **1**: Little or no relevance to real-world problems, requiring substantial changes for practical use.
        """  # noqa: E501
    )

    vc_sys_msg = make_judge_system_message(
        persona=vc_persona,
        example_feedback=vc_example_feedback,
        criteria=vc_criteria,
    )

    vc_model_conf_dict = ChatGPTConfig(
        temperature=0.0,
        tools=SEARCH_FUNCS,
    )
    vc_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=vc_model_conf_dict.as_dict(),
    )

    vc_agent = ChatAgent(
        system_message=vc_sys_msg,
        model=vc_model,
        tools=SEARCH_FUNCS,
    )

    workforce = Workforce('Hackathon Judges')
    task = Task(content="Evaluate hackathon projects", id=0)

    workforce.add_single_agent_worker(
        "A venture capitalist",
        worker=vc_agent,
    )

    task = workforce.process_task(task)
    print(task.result)


if __name__ == "__main__":
    main()
