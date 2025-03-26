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
import tempfile

import pandas as pd

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import DocumentProcessingToolkit
from camel.types import ModelPlatformType, ModelType

# Create a sample Excel file for demonstration
temp_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
sample_file_path = temp_file.name

# Create a sample DataFrame
df = pd.DataFrame(
    {
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Age': [25, 30, 35],
        'City': ['New York', 'San Francisco', 'Seattle'],
        'Department': ['Engineering', 'Marketing', 'Finance'],
    }
)

# Save the DataFrame to the CSV file
df.to_csv(sample_file_path, index=False)
print(f"Created sample Excel file at: {sample_file_path}")

# Initialize the Excel toolkit
document_toolkit = DocumentProcessingToolkit()

# Create a model using OpenAI
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Create a chat agent with the Excel toolkit
agent = ChatAgent(
    system_message=(
        "You are a helpful assistant that can analyze Excel files. "
        "Use the provided Excel toolkit to extract and analyze data."
    ),
    model=model,
    tools=[*document_toolkit.get_tools()],
)

# Example: Ask the agent to analyze the Excel file
response = agent.step(
    f"Analyze the Excel file at {sample_file_path} and tell me what data "
    f"it contains."
)

print(response.msgs[0].content)

# Clean up the temporary file
if os.path.exists(sample_file_path):
    os.remove(sample_file_path)
    print(f"Removed temporary file: {sample_file_path}")

'''
===============================================================================
Created sample Excel file at: /var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/T/
tmpqweue66k.csv
The Excel file contains the following data:

| Name    | Age | City          | Department   |
|---------|-----|---------------|--------------|
| Alice   | 25  | New York      | Engineering   |
| Bob     | 30  | San Francisco | Marketing     |
| Charlie | 35  | Seattle       | Finance       |

### Summary:
- **Total Records**: 3
- **Columns**:
  - **Name**: Names of individuals
  - **Age**: Ages of individuals
  - **City**: Cities where individuals reside
  - **Department**: Departments where individuals work
Removed temporary file: /var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/T/
tmpqweue66k.csv
===============================================================================
'''
