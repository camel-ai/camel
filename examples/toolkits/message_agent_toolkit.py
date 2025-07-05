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
Example demonstrating the usage of MessageAgentTool for agent communication.

This example shows how to:
1. Create multiple specialized agents
2. Set up communication between them using MessageAgentTool
3. Coordinate agents through a manager agent
4. Handle multi-step collaborative tasks
"""

import os

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.message_agent_toolkit import MessageAgentTool
from camel.types import ModelPlatformType, ModelType


def main():
    """Demonstrate MessageAgentTool usage with multiple specialized agents."""

    # Ensure you have your OpenAI API key set up
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set your OPENAI_API_KEY environment variable.")
        return

    print("🤖 Setting up Multi-Agent Communication Example")
    print("=" * 50)

    # Create model backend
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={"temperature": 0.1},
    )

    # Create specialized agents
    print("📝 Creating specialized agents...")

    # Data Analyst Agent
    analyst_system_message = BaseMessage.make_assistant_message(
        role_name="Data Analyst",
        content="""You are a data analyst agent. Your role is to:
        - Analyze data and identify patterns
        - Provide insights and recommendations
        - Create summaries of analytical findings
        - Respond concisely and focus on key insights.""",
    )
    analyst_agent = ChatAgent(
        system_message=analyst_system_message, model=model
    )

    # Technical Writer Agent
    writer_system_message = BaseMessage.make_assistant_message(
        role_name="Technical Writer",
        content="""You are a technical writer agent. Your role is to:
        - Transform technical analysis into clear, readable reports
        - Create well-structured documentation
        - Make complex information accessible
        - Write in a professional but engaging tone.""",
    )
    writer_agent = ChatAgent(system_message=writer_system_message, model=model)

    # Research Agent
    researcher_system_message = BaseMessage.make_assistant_message(
        role_name="Research Agent",
        content="""You are a research agent. Your role is to:
        - Gather information on specific topics
        - Provide comprehensive background research
        - Identify relevant trends and context
        - Support analysis with additional data points.""",
    )
    researcher_agent = ChatAgent(
        system_message=researcher_system_message, model=model
    )

    # Create MessageAgentTool and register agents
    print("🔗 Setting up agent communication...")
    communication_tool = MessageAgentTool(
        {
            "analyst": analyst_agent,
            "writer": writer_agent,
            "researcher": researcher_agent,
        }
    )

    # Create Manager Agent with communication capabilities
    manager_system_message = BaseMessage.make_assistant_message(
        role_name="Project Manager",
        content="""You are a project manager that coordinates other agents.
        You have access to message_agent() function to communicate with:
        - "analyst": For data analysis tasks
        - "writer": For creating reports and documentation  
        - "researcher": For gathering additional information
        
        Break down complex tasks and delegate appropriately to other agents.
        Coordinate their work to produce comprehensive results.""",
    )

    manager_agent = ChatAgent(
        system_message=manager_system_message,
        model=model,
        tools=communication_tool.get_tools(),
    )

    print("✅ All agents set up successfully!")
    print(f"📊 Agent registry: {communication_tool.list_available_agents()}")
    print()

    # Example 1: Simple agent-to-agent communication
    print("🔄 Example 1: Direct Agent Communication")
    print("-" * 40)

    # Direct message to analyst
    message = (
        "Analyze the trend: Sales increased 25% in Q1, 15% in Q2, "
        "and 10% in Q3. What insights can you provide?"
    )
    analyst_response = communication_tool.message_agent(message, "analyst")
    print(f"💼 Analyst Response: {analyst_response}")
    print()

    # Pass analyst result to writer
    writer_message = (
        f"Please create a professional summary report based on this "
        f"analysis: {analyst_response}"
    )
    writer_response = communication_tool.message_agent(
        writer_message, "writer"
    )
    print(f"📝 Writer Response: {writer_response}")
    print()

    # Example 2: Manager coordinating multiple agents
    print("🔄 Example 2: Manager-Coordinated Multi-Agent Task")
    print("-" * 40)

    complex_task = """
    We need a comprehensive report on the impact of remote work.
    Please coordinate with the team to:
    1. Research current trends and studies on remote work productivity
    2. Analyze the key factors affecting productivity
    3. Create a professional report summarizing the findings
    """

    print(f"📋 Task: {complex_task}")
    print()

    # Manager coordinates the task
    manager_response = manager_agent.step(complex_task)
    print(f"👨‍💼 Manager Coordination: {manager_response.msgs[0].content}")
    print()

    # Example 3: Agent management operations
    print("🔄 Example 3: Agent Management Operations")
    print("-" * 40)

    # Add a new agent dynamically
    qa_system_message = BaseMessage.make_assistant_message(
        role_name="QA Specialist",
        content=(
            "You are a quality assurance specialist. "
            "Review work for accuracy and completeness."
        ),
    )
    qa_agent = ChatAgent(system_message=qa_system_message, model=model)

    # Register the new agent
    registration_result = communication_tool.register_agent(
        "qa_specialist", qa_agent
    )
    print(f"+ Registration: {registration_result}")

    # List all agents
    print(
        f"📋 Updated agent list: {communication_tool.list_available_agents()}"
    )

    # Get agent count
    print(f"🔢 Agent count: {communication_tool.get_agent_count()}")

    # Use the new agent
    qa_message = (
        "Please review this for quality: "
        "'The report shows good trends in productivity metrics.'"
    )
    qa_response = communication_tool.message_agent(qa_message, "qa_specialist")
    print(f"🔍 QA Response: {qa_response}")

    # Remove an agent
    removal_result = communication_tool.remove_agent("qa_specialist")
    print(f"- Removal: {removal_result}")
    print(f"📋 Final agent list: {communication_tool.list_available_agents()}")
    print()

    # Example 4: Error handling
    print("🔄 Example 4: Error Handling")
    print("-" * 40)

    # Try to message non-existent agent
    error_response = communication_tool.message_agent(
        "Hello", "nonexistent_agent"
    )
    print(f"❌ Error handling: {error_response}")
    print()

    print("🎉 MessageAgentTool demonstration completed!")
    print("This example showed:")
    print("  ✓ Creating specialized agents")
    print("  ✓ Setting up agent communication")
    print("  ✓ Direct agent-to-agent messaging")
    print("  ✓ Manager-coordinated multi-agent tasks")
    print("  ✓ Dynamic agent registration and removal")
    print("  ✓ Error handling for robust operation")


if __name__ == "__main__":
    main()
