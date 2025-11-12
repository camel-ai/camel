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
"""
Example showing how to use CAMEL with custom E2B-compatible sandbox providers.

This example demonstrates how to configure a custom E2B endpoint using
environment variables.
"""

import os

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print(
        "⚠️  python-dotenv not installed. Install with: "
        "pip install python-dotenv"
    )
    print("   Or set environment variables manually")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.interpreters import E2BInterpreter
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType
from camel.utils import print_text_animated


def test_environment_variables():
    """Test: Using environment variables (recommended approach)"""
    print(
        f"{Fore.CYAN}=== Testing E2B with Custom Environment "
        f"Variables ==={Fore.RESET}"
    )

    # Show current environment configuration
    api_key = os.environ.get("E2B_API_KEY", "Not set")
    domain = os.environ.get("E2B_DOMAIN", "Not set")
    print(
        f"{Fore.BLUE}Current E2B_API_KEY: {api_key[:10]}...{Fore.RESET}"
        if api_key != "Not set"
        else f"{Fore.RED}E2B_API_KEY: {api_key}{Fore.RESET}"
    )
    print(
        f"{Fore.BLUE}Current E2B_DOMAIN: {domain}{Fore.RESET}"
        if domain != "Not set"
        else f"{Fore.RED}E2B_DOMAIN: {domain}{Fore.RESET}"
    )

    if api_key == "Not set":
        print(
            f"{Fore.YELLOW}Please set E2B_API_KEY environment "
            f"variable{Fore.RESET}"
        )
        return

    # Create toolkit - it will automatically use the environment variables
    try:
        toolkit = CodeExecutionToolkit(verbose=True, sandbox="e2b")
        print(f"{Fore.GREEN}✅ Successfully created E2B toolkit{Fore.RESET}")
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to create E2B toolkit: {e}{Fore.RESET}")
        return

    # Set up LLM model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type="deepseek/deepseek-v3-0324",
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    )

    # Create agent
    agent = ChatAgent(
        system_message=(
            "You are a helpful coding assistant. When asked to solve a "
            "problem, write and execute Python code."
        ),
        model=model,
        tools=toolkit.get_tools(),
    )

    # Test
    prompt = "Calculate the sum of numbers from 1 to 10 using Python"
    print(f"{Fore.YELLOW}User prompt: {prompt}{Fore.RESET}")

    try:
        response = agent.step(prompt)
        for msg in response.msgs:
            print_text_animated(
                f"{Fore.GREEN}Agent response: {msg.content}{Fore.RESET}"
            )
    except Exception as e:
        print(f"{Fore.RED}❌ Error during execution: {e}{Fore.RESET}")


def test_direct_interpreter():
    """Test: Using E2BInterpreter directly"""
    print(f"\n{Fore.CYAN}=== Testing E2BInterpreter Directly ==={Fore.RESET}")

    # Check environment variables
    api_key = os.environ.get("E2B_API_KEY")
    if not api_key:
        print(
            f"{Fore.RED}❌ E2B_API_KEY not set, skipping direct "
            f"interpreter test{Fore.RESET}"
        )
        return

    try:
        # Create E2B interpreter (uses environment variables)
        interpreter = E2BInterpreter(require_confirm=False)
        print(
            f"{Fore.GREEN}✅ Successfully created E2B interpreter{Fore.RESET}"
        )

        # Execute code directly
        code = """
# Test basic arithmetic and output
result = sum(range(1, 11))
print(f"Sum of 1 to 10: {result}")

# Test a simple function
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(f"Factorial of 5: {factorial(5)}")
"""

        print(
            f"{Fore.YELLOW}Executing code directly with "
            f"E2BInterpreter:{Fore.RESET}"
        )
        print(f"{Fore.BLUE}{code}{Fore.RESET}")

        result = interpreter.run(code)
        print(f"{Fore.GREEN}✅ Execution result: {result}{Fore.RESET}")

    except Exception as e:
        print(f"{Fore.RED}❌ Error with direct interpreter: {e}{Fore.RESET}")


def main():
    """Main function demonstrating E2B custom endpoint configuration"""
    print(f"{Fore.MAGENTA}CAMEL E2B Custom Endpoint Test{Fore.RESET}")
    print(f"{Fore.MAGENTA}{'='*40}{Fore.RESET}")

    print(
        "\nThis example tests CAMEL's E2B integration with custom "
        "sandbox providers."
    )
    print("Configuration is done through environment variables:")
    print("- E2B_API_KEY: Your API key")
    print("- E2B_DOMAIN: Custom E2B domain (optional)")

    # Run tests
    test_environment_variables()
    test_direct_interpreter()

    print(f"\n{Fore.CYAN}Configuration Summary:{Fore.RESET}")
    print("✅ E2B now supports custom endpoints via E2B_DOMAIN")
    print("✅ All configuration is done through environment variables")
    print("✅ No code changes needed to switch providers")


if __name__ == "__main__":
    main()
