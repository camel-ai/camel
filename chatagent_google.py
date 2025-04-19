import os
import sys
import warnings
from dotenv import load_dotenv, find_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.agents import ChatAgent
from camel.toolkits import SearchToolkit

# Suppress specific UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

# Locate and load the .env file
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print(
        "Warning: .env file not found. Ensure environment variables are set."
    )

# Set the LiteLLM API base URL
os.environ["LITELLM_API_BASE"] = (
    "http://0.0.0.0:4000"  # Update this to match your LiteLLM proxy server URL
)

# Configure LiteLLM with the mistral-large-latest model and specify the provider
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,  # Use OPENAI_COMPATIBLE_MODEL
    model_type="mistral-large-latest",  # Specify the LiteLLM-supported model
    url="http://0.0.0.0:4000",  # Explicitly set the LiteLLM proxy server URL
    model_config_dict={
        "temperature": 0.0,  # Adjust temperature as needed
        "max_tokens": 128000,  # Add max_tokens as in the example
    },
)

# Initialize the DuckDuckGo search tool
search_tool = SearchToolkit().search_google

# Create the ChatAgent with the model and tools
agent = ChatAgent(model=model, tools=[search_tool])

# Query the agent
response_1 = agent.step("What is CAMEL-AI?")
print(response_1.msgs[0].content)

response_2 = agent.step("What is the Github link to CAMEL framework?")
print(response_2.msgs[0].content)
