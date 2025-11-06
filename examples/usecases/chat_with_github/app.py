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
import asyncio
import base64
import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.logger import set_log_level
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType

# Silence noisy asyncio cancellation messages
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# ——— Page Config ———
st.set_page_config(page_title="Chat with your Repo", layout="wide")

# ——— Load assets & logos ———
ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
with open(ASSETS / "logo_camel_ai.png", "rb") as f:
    camel_b64 = base64.b64encode(f.read()).decode()
with open(ASSETS / "logo_github.jpg", "rb") as f:
    gh_b64 = base64.b64encode(f.read()).decode()

# ——— Header ———
st.markdown(
    f"""
    <div style='text-align:center; margin-bottom:2rem;'>
      <h1>Chat with any Github Repo</h1>
      <img src='data:image/png;base64,{camel_b64}' width='80' style='margin:0 20px;'>
      <img src='data:image/png;base64,{gh_b64}' width='80' style='margin:0 20px;'>
      <p style='font-size:14px; color:gray;'>Powered by Camel-AI &amp; Git-Ingest MCP</p>
    </div>
    """,  # noqa: E501
    unsafe_allow_html=True,
)

# ——— Initialize ———
load_dotenv()
set_log_level("DEBUG")

# ——— Session State Setup ———
if 'repo_url' not in st.session_state:
    st.session_state['repo_url'] = ''
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# ——— Sidebar: Repo Input ———
st.sidebar.header("Repository")
repo = st.sidebar.text_input("GitHub Repo URL", st.session_state['repo_url'])
if st.sidebar.button("Set Repo"):
    st.session_state['repo_url'] = repo.strip()
    st.session_state['messages'] = []  # reset conversation

# ——— Main: Chat UI ———
if not st.session_state['repo_url']:
    st.info("Please set a GitHub repository URL in the sidebar to start.")
    st.stop()

# Display existing messages
for msg in st.session_state['messages']:
    if msg['role'] == 'user':
        st.chat_message('user').markdown(msg['content'])
    else:
        st.chat_message('assistant').markdown(msg['content'])

# Chat input
if user_input := st.chat_input("Ask a question about the repo…"):
    # Add user message
    st.session_state['messages'].append(
        {'role': 'user', 'content': user_input}
    )
    st.chat_message('user').markdown(user_input)

    # Define async function to query the agent
    async def query_agent(question: str):
        config_path = Path(__file__).parent / "mcp_servers_config.json"
        toolkit = MCPToolkit(config_path=str(config_path))
        await toolkit.connect()
        tools = list(toolkit.get_tools())
        agent = ChatAgent(
            system_message=f"You are a GitHub repo assistant. Repository: {st.session_state['repo_url']}",  # noqa: E501
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
                model_config_dict={"temperature": 0},
            ),
            tools=tools,
        )
        prompt = f"{question}\nRepository: {st.session_state['repo_url']}"
        response = await agent.astep(prompt)
        await toolkit.disconnect()
        return response.msgs[0].content

    # Run the agent
    with st.spinner("Thinking…"):
        answer = asyncio.run(query_agent(user_input))

    # Display assistant reply
    st.session_state['messages'].append(
        {'role': 'assistant', 'content': answer}
    )
    st.chat_message('assistant').markdown(answer)

# ——— Footer ———
st.markdown(
    """
    <hr>
    <p style='text-align:center; color:gray; font-size:0.8rem;'>Powered by Camel-AI &amp; GitHub MCP</p>
    """,  # noqa: E501
    unsafe_allow_html=True,
)
