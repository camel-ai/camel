"""Test A2A agent with mock service"""
"""You can run the mock service with: python camel/mock_a2a.py to test your local A2A setup and HTTP connectivity."""
import asyncio
from camel.societies.workforce.a2a_worker import A2AAgent

async def main():
    base_url = "http://localhost:10000"
    http_kwargs = {
        "timeout": 30.0,
        "headers": {
            "User-Agent": "workforce-a2a-client/0.1",
        },
    }

    print(f"Connecting to A2A service at {base_url}...")
    try:
        # Create A2A agent - this will fetch the agent card
        agent = await A2AAgent.create(
            base_url=base_url,
            http_kwargs=http_kwargs,
        )
        print(f"✓ Successfully connected to A2A service!")
        print(f"  Agent ID: {agent.node_id}")
        print(f"  Agent description: {agent.description}")
        print(f"  Agent card: {agent.agent_card}")
    except Exception as e:
        print(f"✗ Failed to connect to A2A service: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
