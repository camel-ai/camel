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
import traceback
from typing import List

from camel.agents import ChatAgent
from camel.configs import AihubmixConfig
from camel.models import ModelFactory
from camel.models.aihubmix_model import AihubmixModel
from camel.types import ModelPlatformType


def test_single_model(model_type: str, api_key: str, api_base_url: str, app_code: str):
    """Test a single model.
    
    Args:
        model_type (str): The model type to test.
        api_key (str): The API key for authentication.
        api_base_url (str): The base URL for the API.
        app_code (str): The application code.
        
    Returns:
        bool: True if test was successful, False otherwise.
    """
    print("=" * 60)
    print(f"Testing model: {model_type}")
    print("=" * 60)

    # Create model configuration using the config class
    # Note: Claude models require either temperature or top_p to be set, not both
    model_config = AihubmixConfig(
        temperature=0.2,
        # Explicitly set top_p to None to avoid conflict with temperature
        top_p=None
    )

    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.AIHUBMIX,
            model_type=model_type,
            model_config_dict=model_config.as_dict(),
            api_key=api_key,  # Explicitly pass API key
        )
    except Exception as e:
        print(f"Failed to create model {model_type}: {e}")
        return False

    # Show model routing information
    # Create AihubmixModel instance to demonstrate routing logic
    aihubmix_model = AihubmixModel(
        model_type=model_type,
        model_config_dict=model_config.as_dict(),
        api_key=api_key,
        url=api_base_url
    )

    # Output model information
    print(f"Model Platform: {ModelPlatformType.AIHUBMIX}")
    print(f"Model Type: {model_type}")

    # Display backend information based on routing rules
    if model_type.startswith("claude"):
        print("Routing Rule: Claude models use Anthropic SDK")
        print(f"Actual Backend Model: {type(aihubmix_model.model_backend).__name__}")
        print(f"Backend URL: {aihubmix_model.model_backend._url}")
    elif (model_type.startswith("gemini") or model_type.startswith("imagen")) and not model_type.endswith(("-nothink", "-search")) and "embedding" not in model_type:
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
        return True
    except Exception as e:
        print(f"Error occurred: {e}")
        print("Troubleshooting tips:")
        print("1. Claude models require either temperature or top_p, but not both")
        print("2. Check your API key and network connectivity")
        print("3. Verify the model name is supported on AIHUBMIX platform")
        print("4. For Gemini models, ensure google-genai package is installed")
        print("5. Check that the model is available on AIHUBMIX platform")
        traceback.print_exc()
        return False


def main():
    # Check if API key is set
    api_key = os.environ.get("AIHUBMIX_API_KEY")
    api_base_url = os.environ.get("AIHUBMIX_API_BASE_URL", "https://aihubmix.com")
    app_code = os.environ.get("AIHUBMIX_APP_CODE", "APP Code")

    print(f"AIHUBMIX API Base URL: {api_base_url}")
    print(f"AIHUBMIX APP Code: {app_code}")
    if not api_key:
        print("Warning: AIHUBMIX_API_KEY environment variable not set.")
        print("Please set it using: export AIHUBMIX_API_KEY='your-api-key'")
        return

    # Define list of models to test
    models_to_test: List[str] = [
        "gemini-2.5-pro",
        "claude-3-5-sonnet",
        "gpt-5",
        "glm-4.6"
    ]

    print(f"Preparing to test {len(models_to_test)} models: {', '.join(models_to_test)}")
    
    # Test each model
    successful_tests = 0
    for model_type in models_to_test:
        try:
            success = test_single_model(model_type, api_key, api_base_url, app_code)
            if success:
                successful_tests += 1
        except Exception as e:
            print(f"Unexpected error when testing model {model_type}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Test summary: {successful_tests}/{len(models_to_test)} models tested successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()