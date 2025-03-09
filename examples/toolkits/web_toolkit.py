from camel.models import ModelFactory
from camel.types import ModelType, ModelPlatformType
from camel.toolkits import FunctionTool, WebToolkit
from camel.agents import ChatAgent

model = ModelFactory.create(
    model_type=ModelType.GPT_4O,
    model_platform=ModelPlatformType.OPENAI
)

web_tool = WebToolkit(
    headless=True,
    web_agent_model=model,
    planning_agent_model=model
    )

tool_list = [
    FunctionTool(web_tool.browser_simulation)
]

agent = ChatAgent(
    "You are a helpful assistant.",
    model=model,
    tools=tool_list
)

question = "What is the date of birth of Mercedes Sosa? Please find it on the Wikipedia page: https://en.wikipedia.org/wiki/Mercedes_Sosa"

resp = agent.step(question)
print(resp.msgs[0].content)
"""
===============================================================================
Mercedes Sosa was born on 9 July 1935.
===============================================================================
"""
