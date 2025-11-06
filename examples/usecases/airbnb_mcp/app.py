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
import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.logger import set_log_level
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType

# ——— Page config ———
st.set_page_config(page_title="Airbnb Listings Search", layout="wide")


# ——— Load & encode logos ———
with open("assets/logo_camel_ai.png", "rb") as f:
    camel_bytes = f.read()
with open("assets/logo_airbnb_mcp.png", "rb") as f:
    airbnb_bytes = f.read()

camel_b64 = base64.b64encode(camel_bytes).decode()
airbnb_b64 = base64.b64encode(airbnb_bytes).decode()

# ——— Header with Logos ———
st.markdown(
    f"""
    <div style="text-align: center; margin-bottom: 2rem;">
      <h1>Airbnb Listings Search</h1>
      <img src="data:image/png;base64,{camel_b64}" width="80" alt="Camel-AI logo" style="margin:0 20px;" />
      <img src="data:image/png;base64,{airbnb_b64}" width="80" alt="Airbnb MCP logo" style="margin:0 20px;" />
      <p style="font-size:14px; color:gray; margin-top:0.5rem;">
        Powered by Camel-AI &amp; Airbnb MCP
      </p>
    </div>
    """,  # noqa: E501
    unsafe_allow_html=True,
)

# ——— Load env & logging ———
load_dotenv()
set_log_level("DEBUG")

# ——— Persist defaults ———
if "checkin" not in st.session_state:
    st.session_state.checkin = datetime.date.today()
if "checkout" not in st.session_state:
    st.session_state.checkout = datetime.date.today() + datetime.timedelta(
        days=1
    )

# ——— Sidebar inputs ———
st.sidebar.header("Search parameters")
city = st.sidebar.text_input("City", "")
checkin = st.sidebar.date_input("Check-in", value=st.session_state.checkin)
checkout = st.sidebar.date_input("Check-out", value=st.session_state.checkout)
adults = st.sidebar.number_input("Adults", min_value=1, value=2)

# ——— Main: show parameters & run search ———
if st.sidebar.button("Search Listings"):
    # Save for next time
    st.session_state.checkin = checkin
    st.session_state.checkout = checkout

    # Quick summary on the main page
    st.subheader("🔍 You are searching for")
    cols = st.columns(4)
    cols[0].metric("City", city)
    cols[1].metric("Check-in", checkin.strftime("%Y-%m-%d"))
    cols[2].metric("Check-out", checkout.strftime("%Y-%m-%d"))
    cols[3].metric("Adults", adults)

    # Build prompt
    prompt = f"""
        Find me the best Airbnb in {city} with a check-in date 
        of {checkin:%Y-%m-%d} and a check-out date of 
        {checkout:%Y-%m-%d} for {adults} adults. 
        Return the top 5 listings with their names, prices, and locations.
    """

    # Run the agent
    with st.spinner("Searching…"):

        async def run_task():
            config_path = Path(__file__).parent / "mcp_servers_config.json"
            mcp = MCPToolkit(config_path=str(config_path))
            await mcp.connect()
            tools = list(mcp.get_tools())
            agent = ChatAgent(
                system_message="You are an Airbnb search assistant.",
                model=ModelFactory.create(
                    model_platform=ModelPlatformType.OPENAI,
                    model_type=ModelType.GPT_4O,
                    model_config_dict={"temperature": 0.7},
                ),
                tools=tools,
            )
            res = await agent.astep(prompt)
            try:
                await mcp.disconnect()
            except Exception:
                pass
            return res

        result = asyncio.run(run_task())

    # Show results
    st.success("Search complete!")
    st.markdown("### Results")
    st.markdown(result.msgs[0].content)
# ——— Footer ———
st.markdown(
    """
    <hr style="margin-top:3rem">
    <p style="text-align:center; color:gray; font-size:0.8rem;">
      Powered by Camel-AI &amp; Airbnb MCP
    </p>
    """,
    unsafe_allow_html=True,
)
