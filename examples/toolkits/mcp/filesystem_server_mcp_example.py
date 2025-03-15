import asyncio
import os  # noqa: F401
import sys
from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType

# Load environment variables from .env if available.
load_dotenv()

# Set your Anthropic API key (ensure this is valid).
# anthropic_api_key = "Your_Anthropic_API_Key" # Replace with your API key
# os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

# Import _MCPServer from the correct location.
from camel.toolkits.mcp_toolkit import _MCPServer  # noqa: E402


async def interactive_input_loop(agent: ChatAgent):
    loop = asyncio.get_event_loop()
    print("\nEntering interactive mode. Type 'exit' at any prompt to quit.")
    
    while True:
        choice = await loop.run_in_executor(
            None,
            input,
            "\nChoose an action (Type 'exit' to end loop or press Enter to use current directory):\n1. Read a file\n2. List a directory\nYour choice (1/2): "
        )
        choice = choice.strip().lower()
        if choice == "exit":
            print("Exiting interactive mode.")
            break

        if choice == "1":
            file_path = await loop.run_in_executor(
                None,
                input,
                "Enter the file path to read (default: README.md): "
            )
            file_path = file_path.strip() or "README.md"
            query = f"Use the read_file tool to display the content of {file_path}. Do not generate an answer from your internal knowledge."
        elif choice == "2":
            dir_path = await loop.run_in_executor(
                None,
                input,
                "Enter the directory path to list (default: .): "
            )
            dir_path = dir_path.strip() or "."
            query = f"Call the list_directory tool to show me all files in {dir_path}. Do not answer directly."
        else:
            print("Invalid choice. Please enter 1 or 2.")
            continue

        response = await agent.astep(query)
        print(f"\nYour Query: {query}")
        print("Full Agent Response:")
        print(response.info)
        if response.msgs and response.msgs[0].content:
            print("Agent Output:")
            print(response.msgs[0].content.rstrip())
        else:
            print("No output received.")

async def main(server_transport: str = 'stdio'):
    if server_transport == 'stdio':
        # Determine the absolute path to filesystem_server_mcp.py
        server_script_path = (Path(__file__).resolve().parents[3] / "camel" / "toolkits" / "mcp" / "servers" / "filesystem_server_mcp.py")
        
        # Ensure the server script exists
        if not server_script_path.is_file():
            print(f"Error: Server script not found at {server_script_path}")
            return
        
        # Create an _MCPServer instance for our local filesystem server.
        server = _MCPServer(
            command_or_url=sys.executable,
            args=[str(server_script_path)]
        )
        mcp_toolkit = MCPToolkit(servers=[server])
    else:
        mcp_toolkit = MCPToolkit("tcp://localhost:5000")
    
    async with mcp_toolkit.connection() as toolkit:
        tools = toolkit.get_tools()

        # System prompt instructing the assistant to use external filesystem tools.
        sys_msg = (
            "You are a helpful assistant. Always use the provided external tools for filesystem operations "
            "Also remember to use the tools to answer questions about the filesystem. Always use the tools "
            "Make sure to keep the messages short and to the point so that tokens are not wasted. "
            "when asked, rather than relying on your internal knowledge. Ensure that your final answer does not "
            "end with any trailing whitespace."
        )
        
        # Create the model using the Anthropic configuration.
        model = ModelFactory.create(
            model_platform=ModelPlatformType.ANTHROPIC,
            model_type="claude-3-7-sonnet-20250219",
            api_key=anthropic_api_key,
            model_config_dict={"temperature": 0.8, "max_tokens": 4096},
        )
        
        # Create the ChatAgent with the system message, model, and registered tools.
        camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=tools,
        )
        camel_agent.reset()
        # Clear memory to avoid empty messages that may cause errors.
        camel_agent.memory.clear()
        
        # Start the interactive input loop.
        await interactive_input_loop(camel_agent)

if __name__ == "__main__":
    asyncio.run(main())



"""
Expected Output - 

Entering interactive mode. Type 'exit' at any prompt to quit.

Choose an action (Type 'exit' to end loop or press Enter to use current directory):
1. Read a file
2. List a directory
Your choice (1/2): 2
Enter the directory path to list (default: .): /home/parthshr370/Downloads/camel/camel/toolkits
INFO:mcp.server.lowlevel.server:Processing request of type CallToolRequest
INFO:__main__:list_directory triggered with directory_path: /home/parthshr370/Downloads/camel/camel/toolkits

Your Query: Call the list_directory tool to show me all files in /home/parthshr370/Downloads/camel/camel/toolkits. Do not answer directly.
Full Agent Response:
{'id': 'msg_01AsGxxSsdgzwvb42Niczkc4', 'usage': 
{'completion_tokens': 33, 'prompt_tokens': 975, 'total_tokens': 1008, 'completion_tokens_details': None, 'prompt_tokens_details': None}, 'termination_reasons': ['stop'], 'num_tokens': 381, 
'tool_calls': [ToolCallingRecord(tool_name='list_directory', 
args={'directory_path': '/home/parthshr370/Downloads/camel/camel/toolkits'}, 
result='excel_toolkit.py\nbrowser_toolkit.py\nfunction_tool.py\nsympy_toolkit.py\nmeshy_toolkit.py\nvideo_download_toolkit.py\nstripe_toolkit.py\narxiv_toolkit.py\nmcp_toolkit.py\n__init__.py
\nslack_toolkit.py\nreddit_toolkit.py\ndappier_toolkit.py\nopen_api_specs
\nmineru_toolkit.py\ntwitter_toolkit.py\ngoogle_maps_toolkit.py\ncode_execution.py
\n__pycache__\nsemantic_scholar_toolkit.py\nask_news_toolkit.py\ndata_commons_toolkit.py
\nmcp\nimage_analysis_toolkit.py\nopenbb_toolkit.py\ngoogle_scholar_toolkit.py\nmath_toolkit.py
\nopen_api_toolkit.py\nsearch_toolkit.py\nweather_toolkit.py\npage_script.js\nbase.py\ndalle_toolkit.py
\nzapier_toolkit.py\nwhatsapp_toolkit.py\nnotion_toolkit.py\nnetworkx_toolkit.py\npubmed_toolkit.py\nvideo_analysis_toolkit.py
\nlinkedin_toolkit.py\nhuman_toolkit.py\naudio_analysis_toolkit.py\nterminal_toolkit.py\nfile_write_toolkit.py\nretrieval_toolkit.py
\ngithub_toolkit.py', tool_call_id='toolu_012KYHbf5r2f3Xz5reGanLNS')], 'external_tool_call_request': None}
Agent Output:
Here are the files in the directory /home/parthshr370/Downloads/camel/camel/toolkits as requested.

Choose an action (Type 'exit' to end loop or press Enter to use current directory):
1. Read a file
2. List a directory
Your choice (1/2): exit
Exiting interactive mode.

"""