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
import urllib.parse

import agentops

from camel.agents.chat_agent import ChatAgent
from camel.loaders import Firecrawl
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType

agentops.init(default_tags=['Workforce Twitter Creator'])

from camel.toolkits import (  # noqa: E402
    TWITTER_FUNCS,
    FunctionTool,
    SearchToolkit,
)


def write_tweet(
    workforce: Workforce, additional_content: str, direct_post: bool
) -> None:
    if direct_post:
        human_task = Task(
            content=(
                "Get the infomation on the PR and do reseach on what tool was "
                "used, then write a tweet based on it that is accurate to "
                "what the pr is and finally post it."
            ),
            additional_info=additional_content,
            id='0',
        )
        task = workforce.process_task(human_task)
        print(f"Final Result: {task.result}")
    else:
        human_task = Task(
            content=(
                "Get the infomation on the PR and do reseach on what tool was "
                "used, then write a tweet based on it that is accurate to "
                "what the pr is. No need to post it on twitter, only return "
                "the tweet."
            ),
            additional_info=additional_content,
            id='0',
        )

        task = workforce.process_task(human_task)

        # URL encode the text
        encoded_text = urllib.parse.quote(task.result)

        print(
            "Click here to make a post!\n"
            f"https://x.com/intent/post?text={encoded_text}"
        )


def main():
    firecrawl = Firecrawl()

    response = firecrawl.crawl(url="https://devpost.com/software/aigremment")

    hackathon_content = response["data"][1]["markdown"]

    print(hackathon_content)

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
        You are an expert social media manager. Your task is to take the information I give you and turn it into a tweet. You must follow this tweet format and rules:
    
        - Start by addressing a challenge related to the hackathon (e.g., "Making posts about your hackathon projects is a slow process...").
        - Mention the solution you built, highlighting the CAMEL-AI hackathon.
        - Include the technologies used, mentioning CAMEL-AI, MistralAI, and Firecrawl.
        - Include a call to action (e.g., "See more: [link]").
        - Use 1-2 appropriate emojis that match the tone and context.
    
        Your ouput should look like these , try and follow this structure exactly:
    
        Tweet to hackathon, output Example 1:
            "Making posts about your hackathon projects is a slow process... 😓
        
            So I built a multi-agent system at the 🐫 @CAMELAIOrg hackathon to turn any hackathon into a tweet".
        
            See more: https://devpost.com/software/tweettohackathon "
    
        Find best product, output Example 2:
            "It always takes forever to find a good product... ⏳
        
            So I built a multi-agent system at the 🐫 @CAMELAIOrg hackathon that can search the web for the best products "CAMEL-AI", "MistralAI", & "Firecrawl".
        
            See more: https://devpost.com/software/ "
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
            role_name="proof checker agent",
            content="You check tweets and make them more funny",
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

    workforce = Workforce('Tweet Writing Group')

    workforce.add_single_agent_worker(
        "Proof checker agent, an agent that can check for grammer "
        "and spelling mistkes in tweets",
        worker=proof_checker_agent,
    ).add_single_agent_worker(
        "An agent that can write tweets based on a report",
        worker=tweet_writer_agent,
    ).add_single_agent_worker(
        "An agent who can do online searches for information",
        worker=tool_research_agent,
    ).add_single_agent_worker(
        "An agent who can interact with Twitter on user's behalf",
        worker=twitter_agent,
    )

    write_tweet(workforce, hackathon_content, direct_post=False)

    agentops.end_session("Success")


if __name__ == "__main__":
    main()
