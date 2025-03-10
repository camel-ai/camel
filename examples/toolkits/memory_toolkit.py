# memory_toolkit_example.py
import json
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.configs import ChatGPTConfig
from camel.types import ModelPlatformType, ModelType
from camel.toolkits.memory_toolkit import MemoryToolkit

def run_memory_toolkit_example():
    """
    Demonstrates a ChatAgent using the MemoryToolkit for function calling to manage memory.
    """

    # Create a Model
    model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config_dict,
    )

    # Create a ChatAgent
    agent = ChatAgent(
        system_message="You are an assistant that can manage conversation memory using tools.",
        model=model,
    )

    # Add MemoryToolkit to the Agent
    memory_toolkit = MemoryToolkit(agent=agent)
    for tool in memory_toolkit.get_tools():
        agent.add_tool(tool)

    # Have a conversation to populate memory
    print("\n--- Starting a Conversation ---")
    user_msg_1 = "Tell me about the moon."
    print(f"[User] {user_msg_1}")
    response_1 = agent.step(user_msg_1)
    print(f"[Agent] {response_1.msgs[0].content}")

    # Save the memory to a file via function calling
    print("\n--- Saving Memory ---")
    save_msg = "Please save the current memory to 'conversation_memory.json'."
    response_save = agent.step(save_msg)
    print(f"[Agent] {response_save.msgs[0].content}")
    print(f"[Tool Call Info] {response_save.info['tool_calls']}")

    # Clear the memory via function calling
    print("\n--- Clearing Memory ---")
    clear_msg = "Please clear the memory."
    response_clear = agent.step(clear_msg)
    print(f"[Agent] {response_clear.msgs[0].content}")
    print(f"[Tool Call Info] {response_clear.info['tool_calls']}")

    # Verify memory is cleared
    print("\n--- Checking Memory After Clear ---")
    check_msg = "What do you remember about the moon?"
    response_check = agent.step(check_msg)
    print(f"[Agent] {response_check.msgs[0].content}")

    # Load memory from the saved file via function calling
    print("\n--- Loading Memory from File ---")
    load_msg = "Please load the memory from 'conversation_memory.json'."
    response_load = agent.step(load_msg)
    print(f"[Agent] {response_load.msgs[0].content}")
    print(f"[Tool Call Info] {response_load.info['tool_calls']}")

    # Verify memory is restored
    print("\n--- Checking Memory After Load ---")
    check_msg = "What do you remember about the moon?"
    response_restored = agent.step(check_msg)
    print(f"[Agent] {response_restored.msgs[0].content}")

if __name__ == "__main__":
    run_memory_toolkit_example()