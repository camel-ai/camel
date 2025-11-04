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
import os

from camel.agents import ChatAgent
from camel.configs import AihubmixConfig
from camel.models import ModelFactory
from camel.models.aihubmix_model import AihubmixModel
from camel.types import ModelPlatformType

# Check if API key is set
api_key = os.environ.get("AIHUBMIX_API_KEY")
api_base_url = os.environ.get("AIHUBMIX_API_BASE_URL", "https://aihubmix.com")
app_code = os.environ.get("AIHUBMIX_APP_CODE", "APP Code")

print(f"AIHUBMIX API Base URL: {api_base_url}")
print(f"AIHUBMIX APP Code: {app_code}")
if not api_key:
    print("Warning: AIHUBMIX_API_KEY environment variable not set.")
    print("Please set it using: export AIHUBMIX_API_KEY='your-api-key'")
    # Can choose to exit or continue execution (if just testing)
    # exit(1)

# Create model configuration using the config class
# Note: Claude models require either temperature or top_p to be set, not both
model_config = AihubmixConfig(
    temperature=0.2,
    # Explicitly set top_p to None to avoid conflict with temperature
    top_p=None
)

# Select model to test
MODEL_TYPE = "claude-3-7-sonnet"

model = ModelFactory.create(
    model_platform=ModelPlatformType.AIHUBMIX,
    model_type=MODEL_TYPE,
    model_config_dict=model_config.as_dict(),
    api_key=api_key,  # Explicitly pass API key
)

# Show model routing information
# Create AihubmixModel instance to demonstrate routing logic
aihubmix_model = AihubmixModel(
    model_type=MODEL_TYPE,
    model_config_dict=model_config.as_dict(),
    api_key=api_key,
    url=api_base_url
)

# Output model information
print(f"Model Platform: {ModelPlatformType.AIHUBMIX}")
print(f"Model Type: {MODEL_TYPE}")

# Display backend information based on routing rules
if MODEL_TYPE.startswith("claude"):
    print("Routing Rule: Claude models use Anthropic SDK")
    print(f"Actual Backend Model: {type(aihubmix_model.model_backend).__name__}")
    print(f"Backend URL: {aihubmix_model.model_backend._url}")
elif (MODEL_TYPE.startswith("gemini") or MODEL_TYPE.startswith("imagen")) and not MODEL_TYPE.endswith(("-nothink", "-search")) and "embedding" not in MODEL_TYPE:
    print("Routing Rule: Gemini/Imagen models use Google SDK via AIHUBMIX")
    print(f"Actual Backend Model: {type(aihubmix_model.model_backend).__name__}")
    print(f"Backend URL: {getattr(aihubmix_model.model_backend, 'url', 'Not available')}")
    print("Note: AIHUBMIX Gemini models now use Google's native SDK for better compatibility")
else:
    print("Routing Rule: Other models use OpenAI compatible interface")
    print(f"Actual Backend Model: {type(aihubmix_model.model_backend).__name__}")
    print(f"Backend URL: {aihubmix_model.model_backend._url}")

print(f"Temperature: {model_config.temperature}")
if model_config.top_p is not None:
    print(f"Top P: {model_config.top_p}")

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# Use simple English message, avoiding special characters
user_msg = "Hello, this is a test message for CAMEL AI."

print("Sending message to AIHUBMIX model...")
print("Note: Claude models require either temperature or top_p, but not both.")
try:
    # Get response information
    response = camel_agent.step(user_msg)
    print("Response received:")
    print(response.msgs[0].content)
except Exception as e:
    print(f"Error occurred: {e}")
    print("Troubleshooting tips:")
    print("1. Claude models require either temperature or top_p, but not both")
    print("2. Check your API key and network connectivity")
    print("3. Verify the model name is supported on AIHUBMIX platform")
    print("4. For Gemini models, ensure google-genai package is installed")
    print("5. Check that the model is available on AIHUBMIX platform")
    import traceback
    traceback.print_exc()

'''
===============================================================================
 Hello CAMEL AI! It's great to meet a community dedicated to the study of 
 autonomous and communicative agents. How can I assist you today?
===============================================================================
'''