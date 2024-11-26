# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========

"""Example of using NVIDIA models for CAMEL-like interactions."""

from dotenv import load_dotenv
from camel.configs import NvidiaConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
import os

def get_model(model_type: ModelType, temperature: float = 0.7, stream: bool = True):
    """Create a NVIDIA model instance with specified configuration.

    This function creates and configures a NVIDIA model instance with the specified
    parameters. It requires a NVIDIA API key to be set in the environment.

    Args:
        model_type (ModelType): The type of NVIDIA model to use
        temperature (float, optional): Controls randomness in responses.
            Higher values (e.g., 0.8) make output more random, while lower
            values (e.g., 0.2) make it more deterministic. Defaults to 0.7.
        stream (bool, optional): Whether to stream the response. When True,
            responses are returned as they're generated. Defaults to True.

    Returns:
        BaseModelBackend: Configured NVIDIA model instance

    Raises:
        ValueError: If NVIDIA_API_KEY environment variable is not set
    """
    config = NvidiaConfig().model_copy(update={
        'temperature': temperature,
        'top_p': 0.9,
        'max_tokens': 500,
        'stream': stream
    })

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError(
            "NVIDIA_API_KEY environment variable must be set. "
            "Please obtain an API key from NVIDIA and set it in your environment."
        )

    return ModelFactory.create(
        model_platform=ModelPlatformType.NVIDIA,
        model_type=model_type,
        model_config_dict=config.model_dump(),
        api_key=api_key,
    )

def simulate_task_solving():
    """Simulate a task-solving conversation between an assistant and a user."""
    print("\nSimulating a task-solving conversation:")
    print("-" * 50)
    
    # Initialize model for assistant
    assistant_model = get_model(
        ModelType.NVIDIA_LLAMA3_CHATQA_70B,
        temperature=0.7,
        stream=True
    )
    
    # Initial task description
    task = "Design a Python function that implements a custom sorting algorithm."
    
    # Context setup for the assistant
    assistant_context = (
        "You are an expert Python developer helping to implement algorithms. "
        "Provide detailed, well-documented code solutions."
    )
    
    messages = [
        {"role": "context", "content": assistant_context},
        {"role": "user", "content": task}
    ]
    
    print("User: " + task)
    print("\nAssistant (streaming):")
    for response in assistant_model.chat(messages=messages):
        print(response, end="", flush=True)
    print("\n")
    
    # Follow-up question about time complexity
    follow_up = "What is the time complexity of this sorting algorithm?"
    messages.append({"role": "assistant", "content": response})
    messages.append({"role": "user", "content": follow_up})
    
    print("User: " + follow_up)
    print("\nAssistant (streaming):")
    for response in assistant_model.chat(messages=messages):
        print(response, end="", flush=True)
    print("\n")

def demonstrate_model_comparison():
    """Compare responses between different NVIDIA models."""
    print("\nComparing responses between models:")
    print("-" * 50)
    
    # Initialize both models
    model_70b = get_model(ModelType.NVIDIA_LLAMA3_CHATQA_70B, stream=False)
    model_8b = get_model(ModelType.NVIDIA_LLAMA3_CHATQA_8B, stream=False)
    
    prompt = (
        "Explain how the CAMEL framework facilitates multi-agent conversations "
        "and what makes it unique compared to other conversational AI frameworks."
    )
    
    messages = [
        {"role": "context", "content": "You are an AI researcher explaining AI concepts."},
        {"role": "user", "content": prompt}
    ]
    
    print(f"Prompt: {prompt}\n")
    
    print("70B Model Response:")
    response_70b = model_70b.chat(messages=messages)
    print(response_70b)
    print("\n8B Model Response:")
    response_8b = model_8b.chat(messages=messages)
    print(response_8b)

def main() -> None:
    """Run the example demonstrating NVIDIA model capabilities."""
    
    # Example 1: Task-solving conversation
    simulate_task_solving()
    
    # Example 2: Model comparison
    demonstrate_model_comparison()

if __name__ == "__main__":
    load_dotenv()
    main()
