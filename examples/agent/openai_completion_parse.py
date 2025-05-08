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

from pydantic import BaseModel

from camel.models import OpenAICompatibleModel


# Define a Pydantic model for the expected response structure
class MyResponse(BaseModel):
    name: str
    age: int


# Create an instance of OpenAICompatibleModel
model = OpenAICompatibleModel(model_type="gpt-3.5-turbo")

# Prepare messages
messages = [{"role": "user", "content": "Return a JSON with name and age."}]

# Get the raw completion
completion = model._run(messages, response_format=MyResponse)

# Parse the completion into the structured format
parsed_response = model.parse(completion, response_format=MyResponse)

# Access the parsed data
print(parsed_response.name, parsed_response.age)
