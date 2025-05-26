#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from rich import print as rprint

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType

load_dotenv()

async def main():
    try:
        from create_config import create_config
        
        rprint("[green]CAMEL AI Agent with MCP Toolkit[/green]")
        
        # create config for mcp server
        create_config()

        # connect to mcp server
        rprint("Connecting to MCP server...")
        mcp_toolkit = MCPToolkit(config_path="config.json")
        await mcp_toolkit.connect()
        tools = mcp_toolkit.get_tools()
        
        rprint(f"Connected successfully. Found [cyan]{len(tools)}[/cyan] tools available")

        # setup gemini model
        model = ModelFactory.create(
            model_platform=ModelPlatformType.GEMINI,
            model_type="gemini-2.5-pro-preview-05-06",
            api_key=os.getenv("GOOGLE_API_KEY"),
            model_config_dict={"temperature": 0.7, "max_tokens": 4000},
        )

        system_message = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="You are a helpful assistant with access to search, GitHub, and arXiv tools.",
        )

        # create camel agent
        agent = ChatAgent(
            system_message=system_message, 
            model=model, 
            tools=tools, 
            memory=None
        )

        rprint("[green]Agent ready[/green]")
        
        # get user query
        user_query = input("\nEnter your query: ")
        user_message = BaseMessage.make_user_message(role_name="User", content=user_query)

        rprint("\n[yellow]Processing...[/yellow]")
        response = await agent.astep(user_message)

        # show raw response for debugging
        rprint(f"\n[dim]Raw response type: {type(response)}[/dim]")
        rprint(f"[dim]Response: {response}[/dim]")

        # try to get actual content
        if response and hasattr(response, "msgs") and response.msgs:
            rprint(f"\nFound [cyan]{len(response.msgs)}[/cyan] messages:")
            for i, msg in enumerate(response.msgs):
                rprint(f"Message {i+1}: {msg.content}")
        elif response:
            rprint(f"Response content: {response}")
        else:
            rprint("[red]No response received[/red]")

        # disconnect from mcp
        await mcp_toolkit.disconnect()
        rprint("\n[green]Done[/green]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        import traceback
        rprint(f"[dim]{traceback.format_exc()}[/dim]")

if __name__ == "__main__":
    asyncio.run(main())