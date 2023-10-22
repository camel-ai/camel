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

# Import necessary libraries and modules
import os

import openai
import streamlit as st

# Import functions and data related to the Streamlit user interface
from apps.streamlit_ui.multi_agent_communication_ui import (
    context_content_supply_chain,
    main,
    task_prompt_supply_chain,
)
from camel.configs import ChatGPTConfig
from camel.functions.data_io_functions import read_file
from camel.models.openai_model import OpenAIModel
from camel.typing import ModelType

# Set the title for the Streamlit app
st.title("🐫 CAMEL Multi-Agent")

# Create a sidebar with form elements
with st.sidebar:
    with st.form(key='form1'):
        # Input field for OpenAI API Key
        openai_api_key = st.text_input("OpenAI API Key", key="api_key_openai",
                                       type="password")

        # Set the OpenAI API Key in the environment variable
        os.environ["OPENAI_API_KEY"] = openai_api_key
        openai.api_key = openai_api_key

        # File uploader for users to upload a document
        uploaded_file = st.file_uploader(
            "Upload a file", type=("txt", "docx", "pdf", "json", "html"))

        # If a file is uploaded, extract content from it
        if uploaded_file:
            article = read_file(uploaded_file)
            normal_string = article.docs[0]['page_content']

            # Create an instance of the OpenAI model
            my_openai_model = OpenAIModel(
                model_type=ModelType.GPT_3_5_TURBO,
                model_config_dict=ChatGPTConfig().__dict__)

            # Create a task prompt based on the uploaded content
            messages_task_prompt = [
                {
                    "role":
                    "system",
                    "content":
                    '''You are a helpful assistant to extract and
                     re-organize information from provided information.
                    Please create a prompt for the task to be
                     performed described in the given information.''',
                },
                {
                    "role": "user",
                    "content": normal_string,
                },
            ]

            # Get a response for the task prompt
            response_task_prompt = my_openai_model.run(
                messages=messages_task_prompt)['choices'][0]
            content_task_prompt = response_task_prompt['message']['content']

            # Create a context content based on the uploaded content
            messages_context_content = [
                {
                    "role":
                    "system",
                    "content":
                    '''You are a helpful assistant to extract and
                     re-organize information from provided information.
                    Please extract the context content for the task to
                     be performed described in the given information.''',
                },
                {
                    "role": "user",
                    "content": normal_string,
                },
            ]

            # Get a response for the context content
            response_context_content = my_openai_model.run(
                messages=messages_context_content)['choices'][0]
            content_context_content = response_context_content['message'][
                'content']

            # Set task prompt and context content as inputs in the form
            task_prompt = st.text_area(
                "Your task prompt extracted from the file",
                value=content_task_prompt)
            context_content = st.text_area(
                "Your context content extracted from the file",
                value=content_context_content)
        else:
            # Set default values for task prompt and context content
            task_prompt = st.text_area("Insert your task prompt here",
                                       value=task_prompt_supply_chain)
            context_content = st.text_area("Insert your context content here",
                                           value=context_content_supply_chain)

        # Create a submit button in the form
        submit_button = st.form_submit_button(label='Submit')

# Check if all required inputs are provided and the submit button is clicked
if openai_api_key and task_prompt and context_content and submit_button:
    # Call the 'main' function with the task prompt and context content
    main(task_prompt, context_content)
