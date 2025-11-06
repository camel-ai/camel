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

import dotenv
import streamlit as st

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType

# Load environment variables
dotenv.load_dotenv()

# Initialize the model
model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_5_PRO,
    api_key=os.getenv("GEMINI_API_KEY"),
    model_config_dict={"temperature": 0.5, "max_tokens": 4096},
)

# Initialize MCP toolkit
mcp_toolkit = MCPToolkit(config_path="mcp_config.json")

# Create the ChatAgent
agent = ChatAgent(
    system_message=BaseMessage(
        role_name="cloudflare assistant",
        role_type="assistant",
        meta_dict={},
        content="You are a helpful assistant that can access Cloudflare's services via MCP"
    ),
    model=model,
    tools=mcp_toolkit.get_tools(),
)

# Set page config
st.set_page_config(
    page_title="Cloudflare MCP Interface",
    page_icon="☁️",
    layout="wide"
)

# Title and description
st.title("☁️ Cloudflare MCP Interface")
st.markdown("""
This interface allows you to interact with Cloudflare's public MCP servers:
- 📚 Documentation Server
- 📊 Radar Server (Internet Traffic Insights)
- 🌐 Browser Server (Web Page Analysis)
""")

# Create tabs for different services
tab1, tab2, tab3 = st.tabs(["📚 Documentation", "📊 Radar", "🌐 Browser"])

# Documentation Tab
with tab1:
    st.header("Cloudflare Documentation")
    st.markdown("Ask questions about Cloudflare's documentation and services.")
    
    doc_query = st.text_area("Enter your documentation query:", height=100)
    if st.button("Search Documentation", key="doc_search"):
        if doc_query:
            with st.spinner("Searching documentation..."):
                response = agent.step(doc_query)
                st.markdown("### Response:")
                # Access the message content from the response
                if hasattr(response, 'msgs') and response.msgs:
                    st.markdown(response.msgs[0].content)
                else:
                    st.error("No response content available")
        else:
            st.warning("Please enter a query.")

# Radar Tab
with tab2:
    st.header("Cloudflare Radar")
    st.markdown("Get insights about internet traffic and trends.")
    
    radar_options = st.selectbox(
        "Select Radar Query Type:",
        ["Traffic Trends", "URL Analysis", "DNS Analytics", "HTTP Protocol Analysis"]
    )
    
    if radar_options == "Traffic Trends":
        st.markdown("Get insights about global internet traffic trends.")
        trend_query = st.text_input("Enter your trend query (e.g., 'Show me traffic trends for the last week'):")
    elif radar_options == "URL Analysis":
        st.markdown("Analyze a specific URL's traffic and performance.")
        url = st.text_input("Enter URL to analyze:")
        trend_query = f"Analyze traffic and performance for {url}"
    elif radar_options == "DNS Analytics":
        st.markdown("Get DNS-related insights and analytics.")
        domain = st.text_input("Enter domain name:")
        trend_query = f"Show DNS analytics for {domain}"
    else:  # HTTP Protocol Analysis
        st.markdown("Get insights about HTTP protocol usage.")
        trend_query = "Show HTTP protocol analysis and trends"
    
    if st.button("Get Radar Insights", key="radar_search"):
        if trend_query:
            with st.spinner("Fetching radar insights..."):
                response = agent.step(trend_query)
                st.markdown("### Radar Insights:")
                if hasattr(response, 'msgs') and response.msgs:
                    st.markdown(response.msgs[0].content)
                else:
                    st.error("No response content available")
        else:
            st.warning("Please enter required information.")

# Browser Tab
with tab3:
    st.header("Cloudflare Browser")
    st.markdown("Fetch and analyze web pages.")
    
    browser_options = st.selectbox(
        "Select Browser Action:",
        ["Fetch Page", "Take Screenshot", "Convert to Markdown"]
    )
    
    url = st.text_input("Enter URL:")
    
    if browser_options == "Fetch Page":
        action = "Fetch and analyze the content of"
    elif browser_options == "Take Screenshot":
        action = "Take a screenshot of"
    else:  # Convert to Markdown
        action = "Convert to markdown the content of"
    
    if st.button("Execute Browser Action", key="browser_action"):
        if url:
            with st.spinner("Processing..."):
                query = f"{action} {url}"
                response = agent.step(query)
                st.markdown("### Result:")
                if hasattr(response, 'msgs') and response.msgs:
                    st.markdown(response.msgs[0].content)
                else:
                    st.error("No response content available")
        else:
            st.warning("Please enter a URL.")

# Add a sidebar with information
with st.sidebar:
    st.header("About")
    st.markdown("""
    This interface provides access to Cloudflare's public MCP servers, powered by CAMEL AI:
    
    - **Documentation Server**: Access Cloudflare's documentation
    - **Radar Server**: Get internet traffic insights
    - **Browser Server**: Fetch and analyze web pages
    
    Select a tab above to interact with each service.
    """)
    
    st.header("Tips")
    st.markdown("""
    - Be specific in your queries
    - For Radar insights, try different query types
    - For Browser actions, ensure URLs are complete
    """) 