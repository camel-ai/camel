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
    AskNewsToolkit,DalleToolkit, ThinkingToolkit,
    FileWriteToolkit, LinkedInToolkit
)
from camel.logger import set_log_level
import logging

logging.basicConfig(level=logging.DEBUG)
load_dotenv()
set_log_level(level="DEBUG")

# 1. Model Setup
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI, 
    model_type=ModelType.GPT_4O, 
    model_config_dict={"temperature": 0.0}
)

def get_author_id_from_bulk_search(topic: str):
    """Search papers using fetch_bulk_paper_data and extract the top author's ID."""
    toolkit = SemanticScholarToolkit()

    # ✅ Request authors explicitly in the fields
    results = toolkit.fetch_bulk_paper_data(
        query=topic,
        fields=[
            "title",
            "authors",
            "url",
            "publicationDate",
            "openAccessPdf"
        ]
    )

    if "data" in results and isinstance(results["data"], list):
        for paper in results["data"]:
            authors = paper.get("authors", [])
            if authors:
                return authors[0].get("authorId")  # Return first author ID
    
    return None


# 3. Streamlit UI: Get topic from user
st.title("CAMEL Multi-Agent Research Assistant")
topic = st.text_input("Enter a research topic:", value="latest breakthroughs in quantum computing")
if st.button("Generate Report") and topic:
    
    # 4. Initialize RolePlaying session
    task_prompt = f"Create a comprehensive report on: {topic} and save it locally"
    st.info("🔍 Finding top researcher for topic...")
    author_id = get_author_id_from_bulk_search(topic)
    if not author_id:
        st.error("No author found for this topic.")
        st.stop()

    st.success(f"Using author ID: {author_id}")

    all_tools=[*GoogleScholarToolkit(author_identifier=author_id).get_tools(),
           *SemanticScholarToolkit().get_tools(),
           *ArxivToolkit().get_tools(),
           *AskNewsToolkit().get_tools(),
           *ThinkingToolkit().get_tools(),
           *FileWriteToolkit().get_tools(),
           *LinkedInToolkit().get_tools(),
           *DalleToolkit().get_tools()]

    role_play = RolePlaying(
        assistant_role_name="Researcher Agent",
        user_role_name="Project Manager",
        assistant_agent_kwargs=dict(
            model=model,
            tools=all_tools   # attach toolset to assistant
        ),
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=False
    )
    # Start conversation
    next_msg = role_play.init_chat()
    # 5. Run conversation loop
    while True:
        assistant_resp, user_resp = role_play.step(next_msg)
        if assistant_resp.terminated or user_resp.terminated:
            break
        # Print conversation (for debugging; in practice, gather outputs)
        st.write("**Assistant:**", assistant_resp.msg.content)
        st.write("**User:**", user_resp.msg.content)
        # Exit if task done signal
        if "CAMEL_TASK_DONE" in user_resp.msg.content:
            break
        next_msg = assistant_resp.msg

    st.success("Report generation completed.")
    # The final report and image would have been written to files by the agent.