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
    "https://arxiv.org/pdf/1706.03762.pdf": "1706.03762.pdf",
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

# # Init agent & toolkit
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
    rf"Extract content in the document located at {zip_path}, "
    "return the abstract of them."
)

print(response.msgs[0].content)

# Expected agent response
expected_response = (
    "1. **Document: 1512.03385.pdf**\n"
    "   - **Title:** Deep Residual Learning for Image Recognition\n"
    "   - **Abstract:** Deeper neural networks are more difficult to train. "
    "We present a residual learning framework to ease the training of "
    "networks that are substantially deeper than those used previously. "
    "We explicitly reformulate the layers as learning residual functions "
    "with reference to the layer inputs, instead of learning unreferenced "
    "functions. We provide comprehensive empirical evidence showing that "
    "these residual networks are easier to optimize, and can gain accuracy "
    "from considerably increased depth. On the ImageNet dataset, we evaluate "
    "residual nets with a depth of up to 152 layers—8x deeper than VGG nets "
    "but still having lower complexity. An ensemble of these residual nets "
    "achieves 3.57% error on the ImageNet test set. This result won the 1st "
    "place on the ILSVRC 2015 classification task. We also present analysis "
    "on CIFAR-10 with 100 and 1000 layers. The depth of representations is "
    "of central importance for many visual recognition tasks. Solely due to "
    "our extremely deep representations, we obtain a 28% relative improvement "
    "on the COCO object detection dataset. Deep residual nets are foundations "
    "of our submissions to ILSVRC & COCO 2015 competitions, where we also "
    "won the 1st places on the tasks of ImageNet detection, ImageNet "
    "localization, COCO detection, and COCO segmentation.\n\n"
    "2. **Document: 1706.03762.pdf**\n"
    "   - **Title:** Attention Is All You Need\n"
    "   - **Abstract:** The dominant sequence transduction models are based "
    "on complex recurrent or convolutional neural networks that include an "
    "encoder and a decoder. The best performing models also connect the "
    "encoder and decoder through an attention mechanism. We propose a new "
    "simple network architecture, the Transformer, based solely on attention "
    "mechanisms, dispensing with recurrence and convolutions entirely. "
    "Experiments on two machine translation tasks show these models to be "
    "superior in quality while being more parallelizable and requiring "
    "significantly less time to train. Our model achieves 28.4 BLEU on the "
    "WMT 2014 English-to-German translation task, improving over the existing "
    "best results, including ensembles, by over 2 BLEU. On the WMT 2014 "
    "English-to-French translation task, our model establishes a new "
    "single-model state-of-the-art BLEU score of 41.8 after training for 3.5 "
    "days on eight GPUs, a small fraction of the training costs of the best "
    "models from the literature. We show that the Transformer generalizes "
    "well to other tasks by applying it successfully to English constituency "
    "parsing both with large and limited training data."
)
print(expected_response)

print(
    doc_toolkit._handle_text_file(
        "C:/Users/saedi/OneDrive/Desktop/yizhan/camel/camel/toolkits/example.txt",
        start_line=1,
        end_line=1,
    )
)

# Cleanup all files
for filename in files.values():
    file_path = os.path.join(download_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {file_path}")

if os.path.exists(zip_path):
    os.remove(zip_path)
    print(f"Deleted: {zip_path}")

# Create an example file for agent tool calls
demo_example_file = os.path.join(
    os.path.dirname(__file__), '../../camel/toolkits/example.txt'
)
demo_example_file = os.path.abspath(demo_example_file)

response = agent.step(
    f"create a new file named {demo_example_file} and add content about "
    "camel-ai."
)
print(response.msgs[0].content)

# The file `example.txt` has been successfully created at the specified
# location:
# **C:/Users/saedi/OneDrive/Desktop/yizhan/camel/camel/toolkits/example.txt**
# The content about Camel-AI has been added to the file. If you need any
# further assistance or modifications, feel free to ask!

# 1. Insert a line
response = agent.step(
    f"Insert the line 'Inserted by agent' at line 1 in the file "
    f"{demo_example_file}."
)
print(response.msgs[0].content)

# 2. Replace content
response = agent.step(
    f"Replace the line 'Inserted by agent' with 'Replaced by agent' in the "
    f"file {demo_example_file}."
)
print(response.msgs[0].content)

# The line "Inserted by agent" has been successfully replaced with
# "Replaced by agent" in the file:
# **C:/Users/saedi/OneDrive/Desktop/yizhan/camel/camel/toolkits/example.txt**

# The line is now back to "Inserted by agent." If you need any further
# assistance or modifications, just let me know!  If you need any further
# changes or assistance, feel free to ask!
# The last edit has been successfully undone in the file:
# **C:/Users/saedi/OneDrive/Desktop/yizhan/camel/camel/toolkits/example.txt**
# The line is now back to "Inserted by agent." If you need any further
# assistance or modifications, just let me know!

# 4. Read file content
response = agent.step(f"Read lines 0 to 1 from the file {demo_example_file}.")
print(response.msgs[0].content)
"""ere are the contents of lines 0 to 1 from the file:

```
```
Camel-AI is an innovative framework designed to facilitate the development
and deployment of artificial intelligence applications. It provides a
comprehensive set of tools and libraries that streamline the process of
building machine learning models, enabling developers to focus on creating
intelligent solutions without getting bogged down by the complexities of
underlying algorithms and data management.
Inserted by agent
```

If you need further assistance or additional information, feel free to ask!
"""
# Cleanup the example file
if os.path.exists(demo_example_file):
    os.remove(demo_example_file)
    print(f"Deleted: {demo_example_file}")
