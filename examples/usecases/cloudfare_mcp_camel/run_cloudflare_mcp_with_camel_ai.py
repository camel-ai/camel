from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
import dotenv
import os

dotenv.load_dotenv()

sys_msg = BaseMessage(
    role_name="cloudfare assistant",
    role_type="assistant",
    meta_dict={},
    content="You are a helpful assistant that can access Cloudflare's documentation via MCP"
)


# Initialize the model (using Anthropic's Claude as an example)
model = ModelFactory.create(
    model_platform="gemini",
    model_type="gemini-2.5-pro-preview-05-06",
    api_key=os.getenv("GEMINI_API_KEY"),
    model_config_dict={"temperature": 0.5, "max_tokens": 4096},
    )

#configure the mcp camel toolkit with the path of the config file
mcp_toolkit = MCPToolkit(config_path="mcp_config.json")

# Get the tools from the toolkit
mcp_tools = mcp_toolkit.get_tools()

# Create the ChatAgent with the system message, model, and toolkit
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=mcp_tools,
)

# Example interaction with the agent
user_msg = "list me the index of the documentation?"
response = agent.step(user_msg)
print(response)