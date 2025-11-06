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
from typing import List, Union

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import ExcelToolkit
from camel.types import ModelPlatformType, ModelType

# Create a temporary directory to store the Excel file
temp_dir = tempfile.TemporaryDirectory()
file_path = os.path.join(temp_dir.name, "sample.xlsx")

# Initialize the Excel toolkit
excel_toolkit = ExcelToolkit()

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
        "You are a helpful assistant that can create and manipulate Excel "
        "files. Use the provided Excel toolkit to perform actions like "
        "creating workbooks, managing sheets, and modifying data."
    ),
    model=model,
    tools=[*excel_toolkit.get_tools()],
)

# --- 1. Create a new workbook ---
print("--- 1. Creating a new workbook ---")
initial_data: List[List[Union[str, int]]] = [
    ['Name', 'Age', 'City', 'Department'],
    ['Alice', 25, 'New York', 'Engineering'],
    ['Bob', 30, 'San Francisco', 'Marketing'],
    ['Charlie', 35, 'Seattle', 'Finance'],
]
prompt1 = (
    f"Create a new Excel workbook at '{file_path}' with a sheet named "
    f"'Employees', and add the following data to it: {initial_data}"
)
response1 = agent.step(prompt1)
print(response1.msgs[0].content)
"""--- 1. Creating a new workbook ---
The Excel workbook has been created successfully at the specified path,
 and the 'Employees' sheet has been populated with the provided data. 
 If you need any further assistance, feel free to ask!
"""

# --- 2. Add a new row to the sheet ---
print("\n--- 2. Add a new row to the 'Employees' sheet ---")
new_row = ['David', 40, 'Chicago', 'HR']
prompt2 = (
    f"In the workbook at '{file_path}', append the following row to the "
    f"'Employees' sheet: {new_row}"
)
response2 = agent.step(prompt2)
print(response2.msgs[0].content)
"""--- 2. Add a new row to the 'Employees' sheet ---
The row ['David', 40, 'Chicago', 'HR'] has been successfully
 appended to the 'Employees' sheet in the workbook. If you 
 need any more modifications or assistance, just let me know!"""

# --- 3. Get all rows from the sheet to verify ---
print("\n--- 3. Verifying data by getting all rows ---")
prompt3 = (
    f"Get all rows from the 'Employees' sheet in the workbook at "
    f"'{file_path}'."
)
response3 = agent.step(prompt3)
print(response3.msgs[0].content)
"""--- 3. Verifying data by getting all rows ---
Here are all the rows from the 'Employees' sheet:

| Name    | Age | City            | Department   |
|---------|-----|-----------------|---------------|
| Alice   | 25  | New York        | Engineering   |
| Bob     | 30  | San Francisco   | Marketing     |
| Charlie | 35  | Seattle         | Finance       |
| David   | 40  | Chicago         | HR            |

If you need any further actions or modifications, feel free to ask!"""

# --- 4. Update a row ---
print("\n--- 4. Updating a row ---")
# Update Bob's department (row 3)
update_data = ['Bob', 30, 'San Francisco', 'Sales']
prompt4 = (
    f"In the workbook at '{file_path}', update row 3 in the 'Employees' "
    f"sheet with this data: {update_data}"
)
response4 = agent.step(prompt4)
print(response4.msgs[0].content)
"""--- 4. Updating a row ---
Row 3 in the 'Employees' sheet has been successfully updated with the
 new data: ['Bob', 30, 'San Francisco', 'Sales']. If you need any more 
 changes or assistance, just let me know!"""

# --- 5. Verifying data after update ---
print("\n--- 5. Verifying data after update ---")
response5 = agent.step(prompt3)  # Reuse prompt3
print(response5.msgs[0].content)

# --- 6. Delete a row ---
print("\n--- 6. Deleting a row ---")
# Delete Charlie (now at row 4)
prompt6 = (
    f"In the workbook at '{file_path}', delete row 4 from the 'Employees' "
    f"sheet."
)
response6 = agent.step(prompt6)
print(response6.msgs[0].content)
"""--- 6. Deleting a row ---
Row 4 has been successfully deleted from the 'Employees' sheet.
 If you need any further modifications or assistance, just let me know!
"""

# --- 7. Verifying data after deletion ---
print("\n--- 7. Verifying data after deletion ---")
response7 = agent.step(prompt3)  # Reuse prompt3
print(response7.msgs[0].content)
"""--- 7. Verifying data after deletion ---
Here are all the rows from the 'Employees' sheet after deleting row 4:

| Name    | Age | City            | Department   |
|---------|-----|-----------------|---------------|
| Alice   | 25  | New York        | Engineering   |
| Bob     | 30  | San Francisco   | Sales         |
| David   | 40  | Chicago         | HR            |

If you need any further actions or modifications, feel free to ask!"""


if os.path.exists(file_path):
    os.remove(file_path)
    print(f"Removed temporary file: {file_path}")
temp_dir.cleanup()
