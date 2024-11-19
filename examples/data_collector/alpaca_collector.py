from camel.agents.chat_agent import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.data_collector import AlpacaDataCollector
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.types.enums import ModelPlatformType, ModelType, OpenAIBackendRole


model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Tools calling operator",
        content="You are a helpful assistant",
    ),
    model=model,
)

usr_msg = BaseMessage.make_user_message(
    role_name="User",
    content="When is the release date of the video game Portal?",
)

collector = AlpacaDataCollector().inject(agent).start()

# Automatically record the message
resp = agent.step(usr_msg)

print(collector.convert())

collector.reset()

# Manually record the message
collector.step(usr_msg, OpenAIBackendRole.USER)
collector.step(resp, OpenAIBackendRole.ASSISTANT)

print(collector.convert())

"""
{'instructions': 'You are a helpful assistant', 'input': 'When is the release date of the video game Portal?', 'output': 'The video game Portal was released on October 10, 2007, as part of the game bundle "The Orange Box," which also included Half-Life 2 and its episodes.'}
{'instructions': 'You are a helpful assistant', 'input': 'When is the release date of the video game Portal?', 'output': 'The video game Portal was released on October 10, 2007, as part of the game bundle "The Orange Box," which also included Half-Life 2 and its episodes.'}
"""
