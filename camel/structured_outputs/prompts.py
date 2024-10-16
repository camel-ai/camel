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

DEFAULT_STRUCTURED_PROMPTS = """
    You are an advanced language model tasked with extracting key entities 
    and attributes from unstructured text and 
    converting them into a structured JSON format. 
    Your goal is to analyze the provided text, identify relevant entities, 
    and organize them with corresponding attributes in a clear structure.
    Please ensure the output is formatted as follows: 
    { 
        'entity_name': '...', 'attributes': 
        { 'attribute1': '...', 'attribute2': '...' }, 
        'additional_information': '...' 
    }.
"""
