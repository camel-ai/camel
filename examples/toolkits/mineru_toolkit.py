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

import time

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MinerUToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize the toolkit with longer timeouts
mineru_toolkit = MinerUToolkit()

# Example 1: Direct toolkit usage
print("Example 1: Extracting content from a single URL...")
try:
    print("Starting extraction (this may take several minutes)...")
    # First, initiate the extraction task
    task_data = mineru_toolkit.extract_from_url(
        url="https://arxiv.org/pdf/2311.10993.pdf",
        enable_formula=True,
        enable_table=True,
        language="en",
    )

    print(f"Task initiated with ID: {task_data['task_id']}")

    # Then check the status periodically
    max_retries = 30
    delay = 10
    for _ in range(max_retries):
        result = mineru_toolkit.get_task_status(task_data['task_id'])
        if result['state'] == 'done':
            print(f"Single URL extraction result:\n{result}\n")
            break
        print(f"Status: {result['state']}. Waiting {delay} seconds...")
        time.sleep(delay)
    else:
        raise TimeoutError("Extraction timed out")
except (TimeoutError, RuntimeError) as e:
    print(f"Extraction failed: {e}\n")

"""
Example 1: Extracting content from a single URL...
Starting extraction (this may take several minutes)...
Task initiated with ID: cb66f544-8f8f-4b39-8339-b296622a0f5f
Status: pending. Waiting 10 seconds...

Single URL extraction result:
{
    'task_id': 'cb66f544-8f8f-4b39-8339-b296622a0f5f',
    'state': 'done', 
    'err_msg': '',
    'full_zip_url': 
        'https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip'
}
"""

# Example 2: Batch extract content from multiple URLs
print("Example 2: Extracting content from multiple URLs...")
try:
    print("Starting batch extraction (this may take several minutes)...")
    urls = [
        "https://arxiv.org/pdf/2311.10993.pdf",
        "https://arxiv.org/pdf/2310.07298.pdf",
    ]
    # First, initiate the batch extraction
    batch_id = mineru_toolkit.batch_extract_from_urls(
        urls=urls,
        enable_formula=True,
        enable_table=True,
        language="en",
    )

    print(f"Batch initiated with ID: {batch_id}")

    # Then check the status periodically
    max_retries = 30
    delay = 10
    for _ in range(max_retries):
        result = mineru_toolkit.get_batch_status(batch_id)
        if all(
            task['state'] == 'completed' for task in result['extract_result']
        ):
            print(f"Batch extraction result:\n{result}\n")
            break
        print(f"Batch still processing. Waiting {delay} seconds...")
        time.sleep(delay)
    else:
        raise TimeoutError("Batch extraction timed out")
except (TimeoutError, RuntimeError) as e:
    print(f"Batch extraction failed: {e}\n")

"""
===============================================================================
Example 2: Extracting content from multiple URLs...
Starting batch extraction (this may take several minutes)...
Batch initiated with ID: {
    'batch_id': '7a2a71b4-db30-4cc8-a78d-a067be5e50fa',
    'extract_result': [
        {
            'file_name': '2311.10993.pdf',
            'state': 'pending',
            'err_msg': ''
        },
        {
            'file_name': '2310.07298.pdf',
            'state': 'pending',
            'err_msg': ''
        }
    ]
}
Batch extraction failed: Failed to get batch status: 'data'
===============================================================================
"""

# Example 3: Using with ChatAgent
print("Example 3: Using MinerU with ChatAgent...")

# Set up the agent
sys_msg = BaseMessage.make_assistant_message(
    role_name="Document Analyzer",
    content="""You are a helpful assistant that can extract, analyze content 
    from documents using MinerU's document extraction capabilities. Document 
    processing may take several minutes, so please be patient and inform the 
    user about potential waiting times.""",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=mineru_toolkit.get_tools(),
)

# Example document analysis request
usr_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Please analyze this research paper and extract any mathematical 
    formulas and tables: https://arxiv.org/pdf/2311.10993.pdf""",
)

try:
    print("\nStarting document analysis (this may take several minutes)...")
    response = agent.step(usr_msg)
    print("\nAgent Response:")
    print(response.msg.content)
except Exception as e:
    print(f"\nAgent encountered an error: {e}")

"""
===============================================================================
Example 3: Using MinerU with ChatAgent...

Starting document analysis (this may take several minutes)...

Agent Response:
The extraction process is complete. You can download the extracted content, 
including mathematical formulas and tables, from the following link:

[Download Extracted Content]
(https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip)

If you need any further analysis or specific information from the extracted 
content, feel free to ask!
===============================================================================
"""
