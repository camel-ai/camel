# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os

import streamlit as st

from apps.streamlit_ui.multi_agent_communication_ui import (
    context_content_supply_chain,
    main,
    taks_prompt_supply_chain,
)
from camel.functions.data_io_functions import read_file

st.title("🐫 CAMEL Multi-Agent")

with st.sidebar:
    with st.form(key='form1'):
        openai_api_key = st.text_input("OpenAI API Key", key="api_key_openai",
                                       type="password")
        os.environ["OPENAI_API_KEY"] = openai_api_key

        uploaded_file = st.file_uploader(
            "Upload an file", type=("txt", "docx", "pdf", "json", "html"))

        task_prompt = st.text_input("Insert your task prompt here",
                                    taks_prompt_supply_chain)
        context_content = st.text_input("Insert your context content here",
                                        context_content_supply_chain)

        submit_button = st.form_submit_button(label='Submit')

if uploaded_file and submit_button:
    article = read_file(uploaded_file)
    normal_string = article.docs[0]['page_content']
    main(normal_string, normal_string)
elif task_prompt and context_content and submit_button:
    main(task_prompt, context_content)
