"""
Example: Using AnySearch Toolkit with CAMEL Agent

This example demonstrates how to use the AnySearch toolkit with a CAMEL
ChatAgent to perform web search and page extraction.
"""

from camel.agents import ChatAgent
from camel.agents.toolkits import AnySearchToolkit


def main():
    """Run the AnySearch example."""
    # Initialize the AnySearch toolkit
    # Note: Replace with your actual API key
    toolkit = AnySearchToolkit(api_key="your_api_key_here")

    # Get the tools from the toolkit
    tools = toolkit.get_tools()

    # Initialize the agent
    agent = ChatAgent(tools=tools)

    # Example 1: Simple web search
    print("=== Web Search ===")
    result = agent.step("Search for recent news about artificial intelligence")
    print(result)

    # Example 2: Parallel search
    print("\n=== Parallel Search ===")
    queries = ["Python programming", "Machine learning tutorials", "Data science"]
    result = agent.step(
        f"Run parallel searches for: {', '.join(queries)}"
    )
    print(result)

    # Example 3: Page extraction
    print("\n=== Page Extraction ===")
    url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    result = agent.step(f"Extract content from: {url}")
    print(result)

    # Example 4: Vertical search
    print("\n=== Vertical Search ===")
    result = agent.step("Search for images related to 'sunset'")
    print(result)


if __name__ == "__main__":
    main()
