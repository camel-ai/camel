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
import sys
sys.path.append("..")   

from camel.toolkits import (
    SearchToolkit,
    AsyncBrowserToolkit,
    FunctionTool
)
from camel.models import ModelFactory
from camel.types import(
    ModelPlatformType,
    ModelType
)
from camel.societies.workforce import Workforce
from camel.tasks import Task
from dotenv import load_dotenv

load_dotenv("../.env")

from camel.agents import ChatAgent

def test():
    
    web_agent_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0},
    )
    
    planning_agent_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0},
    )
    
    web_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0},
    )
        

    search_toolkit = SearchToolkit()
    browser_simulator_toolkit = AsyncBrowserToolkit(headless=True, cache_dir="tmp/browser", web_agent_model=web_agent_model, planning_agent_model=planning_agent_model)

    web_agent = ChatAgent(
"""
You are a helpful assistant that can search the web, simulate browser actions, and provide relevant information to solve the given task.
""",
        model=web_model,
        tools=[
            FunctionTool(browser_simulator_toolkit.browse_url)  
        ]
    )
      
    task_agent_kwargs = {
        "model": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0},
        )
    }
    
    coordinator_agent_kwargs = {
        "model": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0},
        )
    }
    
    workforce = Workforce(
        "Gaia Workforce",
        task_agent_kwargs=task_agent_kwargs,
        coordinator_agent_kwargs=coordinator_agent_kwargs,
    )
    
    workforce.add_single_agent_worker(
        "An agent that can search the web, simulate browser actions, and provide relevant information to solve the given task.",
        worker=web_agent,
    )
     
    question = r"According to Girls Who Code, how long did it take in years for the percentage of computer scientists that were women to change by 13% from a starting point of 37%? Here are the urls: https://www.girlswhocode.com/about-us/"
    task = Task(
        content=question,
        id="0",
    )
    
    task_result = workforce.process_task(task)
    print(task_result.result)
    
    """
    ==========================================================================
    The final answer to the root task cannot be determined from the information gathered in the related tasks. The attempts to find the specific data regarding the time it took for the percentage of computer scientists that were women to change from 37% to 13% were unsuccessful due to interruptions and lack of access to detailed information. To obtain this information, it is recommended to search directly on a search engine or consult reliable sources such as academic publications, government reports, or reputable news articles that discuss trends in computer science education and workforce demographics.
    ==========================================================================
    """
    


if __name__ == "__main__":
    test()

