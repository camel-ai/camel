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

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AsyncBrowserToolkit,
    FileWriteToolkit,
    TerminalToolkit,
    PyAutoGUIToolkit,
)
from camel.configs import ChatGPTConfig
import os
from camel.types import ModelPlatformType, ModelType
from camel.logger import get_logger, set_log_file, set_log_level

# Set logging
set_log_file("product_research.log")
logger = get_logger(__name__)
set_log_level(level="DEBUG")
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)

models = {
    "user": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    ),
    "assistant": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    ),
    "research": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    ),
    "browsing": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    ),
    "planning": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    ),
    "analyst": ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
    ),
}

def main():
    tools_list = [
        *AsyncBrowserToolkit(
            headless=False,  # Set to True for headless mode (e.g., on remote servers)
            web_agent_model=models["browsing"],
            planning_agent_model=models["planning"],
        ).get_tools(),
        *PyAutoGUIToolkit().get_tools(),
        *TerminalToolkit(working_dir=workspace_dir).get_tools(),
        *FileWriteToolkit(output_dir="./").get_tools(),
    ]

    # Set up market researcher agent
    market_researcher = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Market Researcher",
            content=(
                "You are an expert market researcher who can analyze products and markets. "
                "You focus on gathering comprehensive information about products, "
                "including features, pricing, target audience, and market positioning. "
                "Your analysis is thorough, unbiased, and based on factual information."
            ),
        ),
        model=models["research"],
        tools=tools_list,
    )

    # Set up competitive analyst agent
    competitive_analyst = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Competitive Analyst",
            content=(
                "You are a competitive analyst who specializes in comparing products "
                "and identifying strengths, weaknesses, opportunities, and threats. "
                "You create detailed comparison matrices and provide insights on "
                "competitive advantages and disadvantages. Your analysis is objective "
                "and based on concrete product features and market data."
            ),
        ),
        model=models["analyst"],
        tools=tools_list,
    )

    # Set up technical evaluator agent
    technical_evaluator = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Technical Evaluator",
            content=(
                "You are a technical expert who evaluates products from a technical perspective. "
                "You analyze technical specifications, performance metrics, architecture, "
                "and implementation details. You can evaluate code repositories, "
                "technical documentation, and engineering decisions to provide a deep "
                "technical assessment of products."
            ),
        ),
        model=models["research"],
        tools=tools_list,
    )

    # Set up report compiler agent
    report_compiler = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Report Compiler",
            content=(
                "You are a professional report compiler who creates well-organized, "
                "clear, and comprehensive product research reports. You excel at "
                "synthesizing information from multiple sources into a cohesive document "
                "with executive summaries, detailed analyses, visual comparisons, and "
                "actionable recommendations. You format documents professionally using markdown."
            ),
        ),
        model=models["analyst"],
        tools=tools_list,
    )

    # Create a coordinator model for the workforce
    coordinator_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    )

    # Create a workforce for product research
    workforce = Workforce(
        'product research',
        coordinator_agent_kwargs={"model": coordinator_model},
        task_agent_kwargs={"model": coordinator_model},
    )

    # Add specialized workers to the workforce
    workforce.add_single_agent_worker(
        "Market Researcher",
        worker=market_researcher,
    ).add_single_agent_worker(
        "Competitive Analyst", 
        worker=competitive_analyst
    ).add_single_agent_worker(
        "Technical Evaluator", 
        worker=technical_evaluator
    ).add_single_agent_worker(
        "Report Compiler", 
        worker=report_compiler
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            "Please give me a product research report comparing Manus vs OWL. "
            "The official URLs are https://manus.im and https://github.com/camel-ai/owl. "
            "The report should include: "
            "1. Executive summary "
            "2. Product overview for each "
            "3. Feature comparison "
            "4. Technical evaluation "
            "5. Market positioning "
            "6. Strengths and weaknesses "
            "7. Recommendations "
            "\nFormat the report in pdf "
            "Finally, open the PDF with a suitable local application."
            "and then scroll the pdf page to the end."
        ),
        id='product_comparison_001'
    )

    task = workforce.process_task(human_task)

    print('Final Result of Product Research Task:\n', task.result)


if __name__ == "__main__":
    main()
