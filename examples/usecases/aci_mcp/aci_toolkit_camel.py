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
#!/usr/bin/env python3
import os

from dotenv import load_dotenv
from rich import print as rprint

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ACIToolkit
from camel.types import ModelPlatformType, ModelType

load_dotenv()


def main():
    rprint("[green]CAMEL AI with ACI Toolkit[/green]")

    # get the linked account from env or use default
    linked_account_owner_id = os.getenv("LINKED_ACCOUNT_OWNER_ID")
    if not linked_account_owner_id:
        raise ValueError("LINKED_ACCOUNT_OWNER_ID environment variable is required")
    rprint(f"Using account: [cyan]{linked_account_owner_id}[/cyan]")

    # setup aci toolkit
    aci_toolkit = ACIToolkit(linked_account_owner_id=linked_account_owner_id)
    tools = aci_toolkit.get_tools()
    rprint(f"Loaded [cyan]{len(tools)}[/cyan] tools")

    # setup gemini model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_2_5_PRO,
        api_key=os.getenv("GEMINI_API_KEY"),
        model_config_dict={"temperature": 0.5, "max_tokens": 40000},
    )

    # create agent with tools
    agent = ChatAgent(model=model, tools=tools)
    rprint("[green]Agent ready[/green]")

    # get user query
    query = input("\nEnter your query: ")

    rprint("\n[yellow]Processing...[/yellow]")
    response = agent.step(query)

    # show raw response
    rprint(f"\n[dim]{response.msg}[/dim]")

    rprint(f"\n[dim]Raw response type: {type(response)}[/dim]")
    rprint(f"[dim]Response: {response}[/dim]")

    # try to get the actual content
    if hasattr(response, 'msgs') and response.msgs:
        rprint(f"\nFound [cyan]{len(response.msgs)}[/cyan] messages:")
        for i, msg in enumerate(response.msgs):
            rprint(f"Message {i + 1}: {msg.content}")

    rprint("\n[green]Done[/green]")


if __name__ == "__main__":
    main()
