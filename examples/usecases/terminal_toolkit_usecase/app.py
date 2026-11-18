import os
import streamlit as st
from dotenv import load_dotenv
from camel.logger import set_log_level

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.toolkits import TerminalToolkit
from camel.messages import BaseMessage

# Load environment variables from .env file
load_dotenv()
set_log_level(level="DEBUG")

# Get current script directory
base_dir = os.path.dirname(os.path.abspath(__file__))
# Define workspace directory for the toolkit
workspace_dir = os.path.join(os.path.dirname(os.path.dirname(base_dir)), "workspace")

# Ensure workspace directory exists
os.makedirs(workspace_dir, exist_ok=True)

# Initialize the language model (using OpenAI's GPT-4o)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0}
)

# Streamlit UI
st.title("System Performance Monitor")

if st.button("Run System Analysis"):
    with st.spinner("Gathering system metrics..."):

        # Initialize the TerminalToolkit with workspace directory
        terminal_toolkit = TerminalToolkit(working_dir=workspace_dir)
        # Create the System Monitor agent
        monitor_system_msg = BaseMessage.make_assistant_message(
            role_name="System Monitor",
            content="You are a system monitoring agent that gathers system performance metrics using terminal commands."
        )
        monitor_agent = ChatAgent(
            system_message=monitor_system_msg,
            model=model,
            tools=terminal_toolkit.get_tools()
        )

        # Prepare the user message to instruct the agent to gather system metrics
        monitor_input = BaseMessage.make_user_message(
            role_name="User",
            content=f"Please gather system performance metrics such as disk usage. If it is not running then try different approach using terminal"
        )

        # Run the System Monitor agent
        monitor_response = monitor_agent.step(monitor_input)
        monitor_output = monitor_response.msgs[-1].content if monitor_response.msgs else ""

        st.subheader("Raw Terminal Output")
        st.code(monitor_output, language="bash")

    with st.spinner("Analyzing system health..."):
        # Create the System Analyst agent
        analyst_system_msg = BaseMessage.make_assistant_message(
            role_name="System Analyst",
            content="You are a system analyst. Analyze raw terminal output and summarize system health."
        )
        analyst_agent = ChatAgent(
            system_message=analyst_system_msg,
            model=model
        )

        # Provide the monitor output to the System Analyst agent
        analysis_input = BaseMessage.make_user_message(
            role_name="User",
            content=monitor_output
        )
        analysis_response = analyst_agent.step(analysis_input)
        analysis_output = analysis_response.msgs[0].content if analysis_response.msgs else ""

        st.subheader("System Analysis")
        st.write(analysis_output)