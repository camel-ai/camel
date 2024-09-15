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
import argparse

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, GithubToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated


def write_weekly_pr_summary(repo_name, model=None):
    prompt = """
    You need to write a summary of the pull requests that were merged in the
    last week.
    You can use the provided github function retrieve_pull_requests to 
    retrieve the list of pull requests that were merged in the last week.
    The maximum amount of PRs to analyze is 3.
    You have to pass the number of days as the first parameter to
    retrieve_pull_requests and state='closed' as the second parameter.
    The function will return a list of pull requests with the following
    properties: title, body, and diffs.
    Diffs is a list of dictionaries with the following properties: filename,
    diff.
    You will have to look closely at each diff to understand the changes that
    were made in each pull request.
    Output a twitter post that describes recent changes in the project and
    thanks the contributors.

    Here is an example of a summary for one pull request:
    📢 We've improved function calling in the 🐪 CAMEL-AI framework!
    This update enhances the handling of various docstring styles and supports
    enum types, ensuring more accurate and reliable function calls. 
    Thanks to our contributor Jiahui Zhang for making this possible.
    """
    print(Fore.YELLOW + f"Final prompt:\n{prompt}\n")

    toolkit = GithubToolkit(repo_name=repo_name)
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Marketing Manager",
        content=f"""
        You are an experienced marketing manager responsible for posting
        weekly updates about the status 
        of an open source project {repo_name} on the project's blog.
        """,
    )
    assistant_model_config_dict = ChatGPTConfig(
        tools=[FunctionTool(toolkit.retrieve_pull_requests)], temperature=0.0
    ).as_dict()

    assistant_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=assistant_model_config_dict,
    )

    agent = ChatAgent(
        assistant_sys_msg,
        model=assistant_model,
        tools=[FunctionTool(toolkit.retrieve_pull_requests)],
    )
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)

    if len(assistant_response.msgs) > 0:
        print_text_animated(
            Fore.GREEN + f"Agent response:\n{assistant_response.msg.content}\n"
        )


def solve_issue(
    repo_name,
    issue_number,
    model=None,
) -> None:
    prompt = f"""
    You need to solve the issue with number: {issue_number}
    For this you will have to use the provided github function to retrieve
    that issue. You will get all the necessary parameters to later create a
    pull request.

    When you have the issue, please follow the instruction and make the 
    necessary changes to the source code provided. Once you have made the 
    changes, you will need to use another provided github function to create a 
    pull request that updates the file on the provided file path in the 
    repository {repo_name}.
    The new_content property of the function should be the corrected source 
    code.
    Return response of this function as the output of this task.
    """
    print(Fore.YELLOW + f"Final prompt:\n{prompt}\n")

    toolkit = GithubToolkit(repo_name=repo_name)
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Software Engineer",
        content="""You are an experienced software engineer who 
        specializes on data structures and algorithms tasks.""",
    )
    assistant_model_config_dict = ChatGPTConfig(
        tools=toolkit.get_tools(),
        temperature=0.0,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_3_5_TURBO,
        model_config_dict=assistant_model_config_dict,
    )

    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
        tools=toolkit.get_tools(),
    )
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)

    if len(assistant_response.msgs) > 0:
        print_text_animated(
            Fore.GREEN + f"Agent response:\n{assistant_response.msg.content}\n"
        )


def main(model=None) -> None:
    parser = argparse.ArgumentParser(description='Enter repo name.')
    parser.add_argument('repo_name', type=str, help='Name of the repository')
    args = parser.parse_args()

    repo_name = args.repo_name
    write_weekly_pr_summary(repo_name=repo_name, model=model)


if __name__ == "__main__":
    main()
