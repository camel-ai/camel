from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import WeatherToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_TURBO,
)


class ResponseFormat(BaseModel):
    weather: str
    time: str


agent = ChatAgent(model=model, tools=[WeatherToolkit().get_weather_data])

resp = agent.step(
    "What's the current weather in New York?",
    response_format=ResponseFormat,
)
print(resp.msg.content)


# resp = agent.step(
#     "Format your last response.",
#     response_format=ResponseFormat,
# )
# print(resp.msg.content)
