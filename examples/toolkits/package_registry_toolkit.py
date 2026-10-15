# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PackageRegistryToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize toolkit
toolkit = PackageRegistryToolkit()

# Direct toolkit method calls
print("=== PyPI Info for 'requests' ===")
pypi_info = toolkit.package_get_pypi_info("requests")
print(pypi_info)

print("\n=== PyPI Search for 'camel-ai' ===")
pypi_search = toolkit.package_search_pypi("camel-ai", limit=3)
print(pypi_search)

print("\n=== npm Info for 'express' ===")
npm_info = toolkit.package_get_npm_info("express")
print(npm_info)

print("\n=== npm Search for 'react' ===")
npm_search = toolkit.package_search_npm("react", limit=3)
print(npm_search)

# Example with ChatAgent
tools = toolkit.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent = ChatAgent(
    system_message="You are a helpful coding assistant with access to package "
    "registries (PyPI and npm).",
    model=model,
    tools=tools,
)

response = agent.step(
    "What is the latest version of requests on PyPI, and what are its "
    "dependencies?"
)
print(response.msgs[0].content)
