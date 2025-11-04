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
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ZoomInfoToolkit
from camel.types import ModelPlatformType, ModelType

def main():
    # Initialize ZoomInfo toolkit
    zoominfo_toolkit = ZoomInfoToolkit()
    
    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create agent with ZoomInfo toolkit
    agent = ChatAgent(
        system_message="You are a B2B intelligence assistant. Help with company research, contact discovery, and data enrichment using ZoomInfo.",
        model=model,
        tools=zoominfo_toolkit.get_tools(),
    )
    
    # Example 1: Search for technology companies
    response = agent.step(
        "Search for technology companies in California with more than 100 employees. Show me the top 10 results sorted by employee count."
    )
    print("Company Search Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()
    
    # Example 2: Search for software engineers at specific companies
    response = agent.step(
        "Find software engineers at Apple Inc and Microsoft. Sort by contact accuracy score in descending order."
    )
    print("Contact Search Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()
    
    # Example 3: Enrich contact information
    response = agent.step(
        "Enrich contact information for john.doe@example.com and jane.smith@techcompany.com. "
        "Return their first name, last name, email, job title, and company information."
    )
    print("Contact Enrichment Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()
    
    # Example 4: Market research scenario
    response = agent.step(
        "I'm researching the fintech industry in New York. Find companies in the financial technology sector, "
        "then find C-level executives at those companies, and finally enrich their contact information."
    )
    print("Market Research Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()
    
    # Example 5: Sales prospecting scenario
    response = agent.step(
        "Help me find sales prospects. Look for companies in the SaaS industry with 50-500 employees, "
        "then find VPs of Sales or Sales Directors at those companies."
    )
    print("Sales Prospecting Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()


if __name__ == "__main__":
    main()
