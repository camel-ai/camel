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

import streamlit as st
from dotenv import load_dotenv
from camel.societies import RolePlaying
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.toolkits import (
    GoogleScholarToolkit, SemanticScholarToolkit, ArxivToolkit,
    AskNewsToolkit, ThinkingToolkit,
    FileWriteToolkit, LinkedInToolkit
)
from camel.logger import set_log_level
import logging

logging.basicConfig(level=logging.DEBUG)
load_dotenv()
set_log_level(level="DEBUG")

# Model Setup
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI, 
    model_type=ModelType.GPT_4O, 
    model_config_dict={"temperature": 0.0}
)

class DynamicResearchAgent:
    """
    Research agent that can dynamically add GoogleScholar tools based on discovered authors
    """
    def __init__(self, base_tools):
        self.base_tools = base_tools
        self.google_scholar_tools = {}
    
    def add_google_scholar_for_author(self, author_identifier: str, author_name: str = None):
        """Add GoogleScholar tools for a specific author"""
        if author_identifier not in self.google_scholar_tools:
            try:
                toolkit = GoogleScholarToolkit(author_identifier=author_identifier)
                self.google_scholar_tools[author_identifier] = toolkit.get_tools()
                return True
            except Exception as e:
                st.warning(f"Could not create GoogleScholar toolkit for {author_name or author_identifier}: {e}")
                return False
        return True
    
    def get_all_tools(self):
        """Get all available tools including dynamically added ones"""
        all_tools = list(self.base_tools)
        for tools in self.google_scholar_tools.values():
            all_tools.extend(tools)
        return all_tools

# Streamlit UI
st.title("CAMEL Dynamic Research Assistant")
topic = st.text_input("Enter a research topic:", value="latest breakthroughs in quantum computing")

if st.button("Generate Report") and topic:
    st.info("🤖 Starting research agent...")
    
    # Base tools that don't require author identifiers
    base_tools = [
        *SemanticScholarToolkit().get_tools(),
        *ArxivToolkit().get_tools(),
        *AskNewsToolkit().get_tools(),
        *ThinkingToolkit().get_tools(),
        *FileWriteToolkit().get_tools(),
        *LinkedInToolkit().get_tools(),
    ]
    
    # Create dynamic research agent
    research_agent = DynamicResearchAgent(base_tools)
    
    # Enhanced task prompt that explains available capabilities
    task_prompt = f"""
    Create a comprehensive research report on: {topic}
    
    Your complete task includes:
    1. Search for recent and relevant papers using SemanticScholar and ArXiv
    2. Identify key researchers and their contributions in this field
    3. If you find important authors, mention their IDs for potential GoogleScholar integration
    4. Analyze the latest trends, breakthroughs, and developments
    5. Get recent news using AskNews if relevant
    6. Synthesize ALL findings into a well-structured comprehensive report
    7. Save the final report as a local file using FileWrite tools
    8. When the report is complete and saved, respond with "CAMEL_TASK_DONE"
    
    Available tools:
    - SemanticScholar: Search academic papers, get author information
    - ArXiv: Search preprints and recent papers
    - AskNews: Get recent news and developments
    - Thinking: Plan and reflect on your research strategy
    - FileWrite: Save your findings and reports
    - LinkedIn: Research author profiles if needed
    
    IMPORTANT: Don't just list papers - create a comprehensive analysis report that synthesizes 
    the information, identifies trends, and provides insights. Save this report to a file.
    """
    
    # Initialize RolePlaying session
    role_play = RolePlaying(
        assistant_role_name="Senior Research Analyst",
        user_role_name="Research Director",
        assistant_agent_kwargs=dict(
            model=model,
            tools=research_agent.get_all_tools()
        ),
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=False
    )
    
    # Start conversation
    next_msg = role_play.init_chat()
    
    # Conversation loop with dynamic tool addition
    conversation_container = st.container()
    step_count = 0
    
    with conversation_container:
        while True:
            step_count += 1
            
            with st.expander(f"Step {step_count}: Agent Interaction", expanded=True):
                assistant_resp, user_resp = role_play.step(next_msg)
                
                if assistant_resp.terminated or user_resp.terminated:
                    st.info("🏁 Conversation terminated by agent")
                    break
                
                # Check if agent mentions needing GoogleScholar for specific authors
                # This is a simple pattern - you could make this more sophisticated
                content = assistant_resp.msg.content.lower()
                if "google scholar" in content and "author" in content:
                    st.info("🔍 Agent requested GoogleScholar tools - this could be implemented with author discovery")
                
                # Display conversation
                st.markdown("**🤖 Research Analyst:**")
                st.write(assistant_resp.msg.content)
                
                st.markdown("**👤 Research Director:**")
                st.write(user_resp.msg.content)
                
                # Check for completion in both agent responses
                if ("CAMEL_TASK_DONE" in user_resp.msg.content or 
                    "CAMEL_TASK_DONE" in assistant_resp.msg.content or
                    "report is complete" in assistant_resp.msg.content.lower() or
                    "task completed" in assistant_resp.msg.content.lower()):
                    st.success("✅ Task completed successfully!")
                    break
                
                next_msg = assistant_resp.msg
                
                # Safety break to prevent infinite loops
                if step_count > 20:
                    st.warning("⚠️ Maximum steps reached. Stopping conversation.")
                    break

    st.success("🎉 Report generation completed!")
    st.info("📄 The research report has been saved locally by the agent.")