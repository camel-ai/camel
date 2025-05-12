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
st.set_page_config(page_title="GitHub Repo Explorer", layout="wide")

# ——— Load assets & logos ———
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
with open(ASSETS / "logo_camel_ai.png", "rb") as f:
    camel_b64 = base64.b64encode(f.read()).decode()
with open(ASSETS / "logo_github.JPG", "rb") as f:
    gh_b64 = base64.b64encode(f.read()).decode()

# ——— Header ———
st.markdown(
    f"""
    <div style='text-align:center; margin-bottom:2rem;'>
      <h1>GitHub Repo Explorer</h1>
      <img src='data:image/png;base64,{camel_b64}' width='80' alt='Camel-AI' style='margin:0 20px;'>
      <img src='data:image/png;base64,{gh_b64}' width='80' alt='GitHub' style='margin:0 20px;'>
      <p style='font-size:14px; color:gray;'>Powered by Camel-AI &amp; Git-Ingest MCP</p>
    </div>
    """,  # noqa: E501
    unsafe_allow_html=True,
)

# ——— Initialize ———
load_dotenv()
set_log_level("DEBUG")

# ——— Sidebar Inputs ———
st.sidebar.header("Search parameters")
repo_url = st.sidebar.text_input(
    "GitHub Repo URL", "https://github.com/1sarthakbhardwaj/Ollama"
)
query = st.sidebar.text_area(
    "Query", "Show me the directory tree of this repository.", height=100
)

# ——— Run query ———
if st.sidebar.button("Run Query"):
    # echo parameters
    st.subheader("🔍 Your search parameters")
    cols = st.columns(2)
    cols[0].write(f"**Repo URL:** {repo_url}")
    cols[1].write(f"**Query:** {query}")

    # call agent
    async def run_task():
        config = Path(__file__).parent / "mcp_servers_config.json"
        toolkit = MCPToolkit(config_path=str(config))
        await toolkit.connect()
        tools = list(toolkit.get_tools())
        agent = ChatAgent(
            system_message="You are a GitHub repo explorer.",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
                model_config_dict={"temperature": 0},
            ),
            tools=tools,
        )
        prompt = f"{query}\nRepository: {repo_url}"
        resp = await agent.astep(prompt)
        await toolkit.disconnect()
        return resp

    with st.spinner("Running query…"):
        result = asyncio.run(run_task())

    # display
    st.success("Query complete!")
    st.markdown("### Result")

    raw = result.msgs[0].content or ""
    # strip fences
    lines = [
        line for line in raw.splitlines() if not line.strip().startswith("```")
    ]
    clean = "\n".join(lines).strip()
    st.code(clean)

    # tool calls
    st.markdown("### Tool Calls")
    for rec in result.info.get("tool_calls", []):
        name = getattr(rec, "tool_name", None) or getattr(
            rec, "name", "<unknown>"
        )
        args = getattr(rec, "args", None) or getattr(rec, "arguments", {})
        st.markdown(f"- **{name}**: `{args}`")

# ——— Footer ———
st.markdown(
    """
    <hr>
    <p style='text-align:center; color:gray; font-size:0.8rem;'>Powered by Camel-AI &amp; GitHub MCP</p>
    """,  # noqa: E501
    unsafe_allow_html=True,
)
