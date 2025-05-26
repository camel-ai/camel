#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from rich import print as rprint
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ACIToolkit

load_dotenv()

def main():
    rprint("[green]CAMEL AI with ACI Toolkit[/green]")
    
    # get the linked account from env or use default
    linked_account = os.getenv("LINKED_ACCOUNT_OWNER", "parthshr370")
    rprint(f"Using account: [cyan]{linked_account}[/cyan]")

    # setup aci toolkit
    aci_toolkit = ACIToolkit(linked_account_owner_id=linked_account)
    tools = aci_toolkit.get_tools()
    rprint(f"Loaded [cyan]{len(tools)}[/cyan] tools")

    # setup gemini model
    model = ModelFactory.create(
        model_platform="gemini",
        model_type="gemini-2.5-pro-preview-05-06",
        api_key=os.getenv("GOOGLE_API_KEY"),
        model_config_dict={"temperature": 0.5, "max_tokens": 4000},
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
            rprint(f"Message {i+1}: {msg.content}")
    
    rprint("\n[green]Done[/green]")

if __name__ == "__main__":
    main()
