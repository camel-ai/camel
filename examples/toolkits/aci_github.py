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

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits.aci_tool import ACIToolkit
from camel.types import ModelPlatformType, ModelType

load_dotenv()

LINKED_ACCOUNT_OWNER = os.getenv("LINKED_ACCOUNT_OWNER")

if LINKED_ACCOUNT_OWNER is None:
    raise ValueError("LINKED_ACCOUNT_owner environment variable is not set.")

# Create ACIToolkit with GitHub permissions
client = ACIToolkit(linked_account=LINKED_ACCOUNT_OWNER)

model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH,
)

# Create ChatAgent with GitHub tools
model = ChatAgent(
    "GitHub Agent",  # More specific agent name
    model=model,
    tools=client.get_tools(),  # Explicitly allow GitHub app
)

respond = model.step("star the repo camel-ai/camel")
print(respond)
