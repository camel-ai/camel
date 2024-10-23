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

import agentops

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType
from camel.workforce import Workforce

agentops.init(default_tags=['Workforce Twitter Creator'])

from camel.toolkits import (  # noqa: E402
    TWITTER_FUNCS,
    FunctionTool,
    SearchToolkit,
)


def main():
    # firecrawl = Firecrawl()
    #
    # response = firecrawl.crawl(url="https://github.com/camel-ai/camel/pull/877")
    #
    # pr_content = (response["data"][0]["markdown"])

    pr_content = textwrap.dedent(
        """\
        ## Description

        Enhance the workforce component, containing a better interface and performance.

        ## Motivation and Context

        Close #796.

        ## Implemented Tasks

        - [x] use structured output feature supported by CAMEL
        - [x] auto tool selection when creating new worker
        - [x] more user-friendly interface https://github.com/camel-ai/camel/pull/713#discussion_r1691233380
        - [x] enhance ROLEPLAY_SUMMERIZE_PROMPT https://github.com/camel-ai/camel/pull/713#discussion_r1691257385
        - [x] task decompose only necessary when the original task can't be easily finished https://github.com/camel-ai/camel/pull/713#discussion_r1691189447
        - [x] Better exit mechanism and error handing, like when a specific agent node fails to operate, output a warning or exit directly.
        - [ ] integrate with agentops to track the progress
        """  # noqa: E501
    )

    search_toolkit = SearchToolkit()
    search_tools = [
        FunctionTool(search_toolkit.search_google),
        FunctionTool(search_toolkit.search_duckduckgo),
    ]

    # Tool Reseacher Agent
    tool_research_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tool Reseacher Agent",
            content="You need to understand what feature is being added and "
            "then search online for information about it the content "
            "of the pr",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.MISTRAL,
            model_type=ModelType.MISTRAL_LARGE,
        ),
        tools=search_tools,
    )

    # Tweet writer
    twitter_writer_prompt = textwrap.dedent(
        """\
        You are an expert social media manager. Your task is to take the information I give you and turn it into a tweet. You must follow this tweet format, rules, content structure, and recipe I have given you as a file to make sure all the tweets are written the same. Make sure you follow this system when making the tweet.

        **Content Structure**:
        1. **What:** What we have done, Example: "We've just integrated the Wolfram_Alpha into the CAMEL framework."
        2. **Why:** Explain why this is good, example: "By doing so, we are providing all agents with a powerful tool for obtaining expert-level answers to a wide range of queries."
        3. **Who:** Explain which contributor did it, example: "Thanks to our contributor Ziyi Yang for working on this."
        4. **CTA:** Show them where they can see more, example: "Explore more here: https://github.com/camel-ai/camel/pull/494."

        **Content Rules you must follow**:
        1. Always start the tweet with "We've just".
        2. Always mention CAMEL-AI fully the first time it appears in the tweet.
        3. Double-check your answers before sending back to me and use web searching if I send you a link.

        Here are some examples  of how the output might look:

        Input: "Togther AI, https://github.com/camel-ai/camel/pull/843"

        Output:
        "📢 We've integrated Together AI into the 🐫 CAMEL framework!
        Their decentralized cloud services empower developers and researchers at organizations of all sizes to train, fine-tune, and deploy generative AI models.
        Thanks to our contributor Wendong-Fangfor this implementation. 🤝 Explore more here: https://github.com/camel-ai/camel/pull/843"

        Input: "Integrate together ai, https://github.com/camel-ai/camel/pull/843"

        Output:
        "📢 We've integrated Together AI into the 🐫 CAMEL framework!
        Their decentralized cloud services empower developers and researchers at organizations of all sizes to train, fine-tune, and deploy generative AI models.
        Thanks to our contributor Wendong-Fang for this implementation. 🤝 Explore more here: https://github.com/camel-ai/camel/pull/843"


        Input: "Integrate Reka model, https://github.com/camel-ai/camel/pull/845"

        Output:
        "📢 We've integrated Reka AI's models into the🐫 CAMEL framework!

        Efficient, natively multimodal models trained on thousands of GPUs. From Reka Core, which rivals industry giants, to Edge for on-device use and Flash for speed, Each model is designed for specific needs and is competitive across key metrics.

        Thanks to our contributor omni_georgio for working on this.🤝 Explore more here: https://github.com/camel-ai/camel/pull/845"
        """  # noqa: E501
    )
    tweet_writer_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Tweet writer",
            content=twitter_writer_prompt,
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.MISTRAL,
            model_type=ModelType.MISTRAL_LARGE,
        ),
    )

    # Proof checker agent
    proof_checker_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Proof checker agent",
            content="You are going to check for grammer and spelling mistkes"
            " in tweets. Also make sure to not exceed the max length of 280 "
            "characters. If it's too long, you need to shorten it.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.MISTRAL,
            model_type=ModelType.MISTRAL_LARGE,
        ),
    )

    # Twitter agent
    twitter_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Twitter Agent",
            content="You are an agent that can interact with Twitter.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.MISTRAL,
            model_type=ModelType.MISTRAL_LARGE,
        ),
        tools=TWITTER_FUNCS,
    )

    workforce = Workforce('PR Tweet Writing Group')

    workforce.add_single_agent_worker(
        "Proof checker agent, an agent that can check for grammer "
        "and spelling mistkes in tweets",
        worker=proof_checker_agent,
    ).add_single_agent_worker(
        "An agent that can write tweets based on a report",
        worker=tweet_writer_agent,
    ).add_single_agent_worker(
        "An agent who can do online searches to find out more "
        "infomation about a pr",
        worker=tool_research_agent,
    ).add_single_agent_worker(
        "An agent who can interact with Twitter on user's behalf",
        worker=twitter_agent,
    )

    human_task = Task(
        content=(
            "Get the infomation on the PR and do reseach on what tool was used"
            " Then create a tweet based on it that is accurate to what the pr "
            "is and finally post it."
        ),
        additional_info=pr_content,
        id='0',
    )

    task = workforce.process_task(human_task)

    print('Final Result of Original task:\n', task.result)

    agentops.end_session("Success")


if __name__ == "__main__":
    main()
