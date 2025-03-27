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

from camel.agents import RepoAgent
from camel.embeddings import OpenAIEmbedding
from camel.retrievers import VectorRetriever
from camel.storages.vectordb_storages import QdrantStorage

vector_storage = QdrantStorage(
    vector_dim=OpenAIEmbedding().get_output_dim(),
    collection_name="tmp_collection",
    path="local_data/",
)

vr = VectorRetriever(embedding_model=OpenAIEmbedding(), storage=vector_storage)

repo_agent = RepoAgent(
    repo_paths=["https://github.com/camel-ai/camel"],
    chunk_size=8192,
    top_k=5,
    similarity=0.3,
    vector_retriever=vr,
    github_auth_token=os.getenv("GITHUB_AUTH_TOKEN"),
)

response = repo_agent.step("How to use a ChatAgent in CAMEL?")

print(response.msgs[0].content)

"""
Based on your request to learn how to use a `ChatAgent` in CAMEL, I will 
explain key aspects of the implementation provided in the source code 
"retrieved" and guide you on how to create and utilize the `ChatAgent` 
effectively.

### Overview of `ChatAgent`

`ChatAgent` is designed to interact with language models, supporting 
conversation management, memory, and tool integration. 
It can perform tasks like handling user queries, responding with structured 
data, and performing computations.

### Basic Usage of `ChatAgent`

Here's a step-by-step guide on how to implement and utilize a `ChatAgent`:

1. **Import Necessary Modules**:
   Ensure to import the relevant classes from the CAMEL library.

   ```python
   from camel.agents import ChatAgent
   ```

2. **Creating a `ChatAgent` Instance**:
   When you create an instance of `ChatAgent`, you can optionally pass a 
   `system_message` to define its role and behavior.

   ```python
   agent = ChatAgent(system_message="You are a helpful assistant.")
   ```

3. **Interacting with the Agent**:
   You can have a conversation by using the `step()` method, which allows you 
   to send messages and get responses.

   ```python
   user_message = "Hello, can you help me with a question?"
   response = agent.step(user_message)
   print(response.msgs[0].content)  # Print the agent's response
   ```

### Advanced Features

#### Integrating Tools

You can define tools (functions) that the agent can call during its operation.

```python
from camel.toolkits import FunctionTool

def calculator(a: int, b: int) -> int:
    return a + b

# Create ChatAgent with a tool
agent_with_tool = ChatAgent(tools=[calculator])
response = agent_with_tool.step("What is 2 + 2 using the calculator?")
```

#### Structured Output

You can specify structured outputs using Pydantic models to control the 
format of the response.

```python
from pydantic import BaseModel
from typing import List

class StructuredResponse(BaseModel):
    points: List[str]
    summary: str

agent = ChatAgent()
response = agent.step(
    "List benefits of exercise", response_format=StructuredResponse
)
```

### Example with a Specific Model

The code examples you provided also show how to specify and configure models 
used by `ChatAgent`. Here's how to create a `ChatAgent` with a custom model:

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="gpt-3.5-turbo",  # Example model
    api_key="your_api_key",  # Ensure you have appropriate credentials
    model_config_dict={"temperature": 0.7}
)

camel_agent = ChatAgent(
    system_message="You are a helpful assistant.", model=model
)

user_message = "What are the best practices for using AI?"
response = camel_agent.step(user_message)
print(response.msgs[0].content)
```

### Conclusion

You can leverage `ChatAgent` in CAMEL to create powerful conversational agents 
that can perform a variety of tasks, integrate tools, and manage conversations 
effectively. The examples given demonstrate basic usage, tool integration, 
structured output formats, and model specification, allowing you to customize 
the behavior of your chat agent to suit your needs.

If you need more specific features or have other questions about the CAMEL 
framework, feel free to ask!

"""
