from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
from camel.toolkits import SearchToolkit

"""
please set the below os environment:
export CRYNUX_API_KEY="your key"

We offer an API key for testing (rate limit = 0.1):
Rfx0SUNqUBovo5MZpArUbzIT3dJpm2JyEd7-6SgikW4=
"""

model = ModelFactory.create(
  model_platform=ModelPlatformType.CRYNUX,
  model_type=ModelType.CRYNUX_QWEN_2_5_7B_INSTRUCT,
  model_config_dict={"temperature": 0.0},
)

search_tool = SearchToolkit().search_duckduckgo

agent = ChatAgent(model=model, tools=[search_tool])

response_1 = agent.step("What is CAMEL-AI?")
print(response_1.msgs[0].content)

"""
CAMEL-AI is an open-source community and the first LLM multi-agent framework dedicated to finding the scaling laws of agents. Here are some key points about CAMEL-AI:

1. **Website**: [CAMEL-AI.org](https://www.camel-ai.org/)
2. **Products**:
   - **EigentBot**: An easy-to-use tool for building a secure and efficient AI knowledge base.
3. **Documentation and Resources**:
   - [CAMEL Tech Stack and Cookbooks](https://docs.camel-ai.org/) to help you build powerful multi-agent systems.
   - [Installation and Setup Guide](https://docs.camel-ai.org/)
   - [MCP Cookbook](https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_MCP.html) which covers advanced features like Model Context Protocol (MCP).

CAMEL-AI aims to advance collaborative AI research and innovation through its platform and community. You can find more detailed information and tutorials on their official website and documentation.
"""

response_2 = agent.step("What is the Github link to CAMEL framework?")
print(response_2.msgs[0].content)

"""
The GitHub link to the CAMEL framework (likely referring to the `camel-ai/camel` repository) is:

- [GitHub - camel-ai/camel: CAMEL: The first and the best multi-agent...](https://github.com/camel-ai/camel)

This repository seems to focus on creating and using LLM-based agents for real-world task solving.
"""

