
from camel.agents import ChatAgent
from camel.configs import SiliconFlowConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType

model = ModelFactory.create(
    model_platform=ModelPlatformType.SILICONFLOW,
    model_type="deepseek-ai/DeepSeek-R1",
    model_config_dict=SiliconFlowConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community
    dedicated to the study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Hello CAMEL AI community! 👋 Your dedication to advancing the study of 
autonomous and communicative agents through open-source collaboration is truly 
inspiring. The work you're doing to push the boundaries of AI interaction and 
cooperative systems will undoubtedly shape the future of intelligent 
technologies. Keep innovating, exploring, and fostering that spirit of shared 
learning—the world is excited to see what you create next! 🚀
===============================================================================
'''