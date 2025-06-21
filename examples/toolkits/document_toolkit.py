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


from __future__ import annotations

import os
import zipfile

import requests

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import DocumentToolkit
from camel.types import ModelPlatformType, ModelType


# set test file
download_dir = "./test"
os.makedirs(download_dir, exist_ok=True)

files = {
    "https://arxiv.org/pdf/1512.03385.pdf": "1512.03385.pdf",
    "https://arxiv.org/pdf/1706.03762.pdf": "1706.03762.pdf"
}

for url, filename in files.items():
    file_path = os.path.join(download_dir, filename)
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
    else:
        print(f"Failed to download: {url}")

zip_path = os.path.join(download_dir, "test.zip")
with zipfile.ZipFile(zip_path, "w") as zipf:
    for filename in files.values():
        zipf.write(os.path.join(download_dir, filename), arcname=filename)
        print(f"Added to zip: {filename}")

# Init agent & toolkit
doc_toolkit = DocumentToolkit()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

agent = ChatAgent(
    system_message=(
        "You are a helpful assistant that can read arbitrary documents. "
        "Use the provided DocumentToolkit to extract text."
    ),
    model=model,
    tools=[*doc_toolkit.get_tools()],
)

# Run agent
response = agent.step(
    fr"Extract content in the document located at {zip_path}, return the abstract of them."
)

print(response.msgs[0].content)

# Cleanup all files
for filename in files.values():
    file_path = os.path.join(download_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {file_path}")

if os.path.exists(zip_path):
    os.remove(zip_path)
    print(f"Deleted: {zip_path}")

