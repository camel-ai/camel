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
import asyncio

from camel.datasets import StaticDataset
from camel.environments.single_step import SingleStepEnv
from camel.verifiers import MathVerifier


def create_math_environment():
    r"""Creates a SingleStepEnv for math problems.

    Returns:
        SingleStepEnv: An environment for math problem solving.
    """
    # Create a simple dataset of math questions
    data = [
        {
            "question": "What is 2 + 2?",
            "final_answer": "4",
            "rationale": "Adding 2 and 2 gives 4.",
        },
        {
            "question": "What is 5 * 3?",
            "final_answer": "15",
            "rationale": "Multiplying 5 and 3 gives 15.",
        },
        {
            "question": "What is 10 - 7?",
            "final_answer": "3",
            "rationale": "Subtracting 7 from 10 gives 3.",
        },
        {
            "question": "What is 20 / 4?",
            "final_answer": "5",
            "rationale": "Dividing 20 by 4 gives 5.",
        },
        {
            "question": "What is the square root of 16?",
            "final_answer": "4",
            "rationale": "The square root of 16 is 4 because 4 * 4 = 16.",
        },
        {
            "question": "What is 3^2?",
            "final_answer": "9",
            "rationale": "3^2 means 3 squared, which is 3 * 3 = 9.",
        },
    ]

    # Create a static dataset from our questions
    dataset = StaticDataset(data)

    # Create a math verifier that can evaluate mathematical expressions
    verifier = MathVerifier()

    # Initialize the environment with our dataset and verifier
    return SingleStepEnv(dataset=dataset, verifier=verifier)


async def setup_and_test_mcp_server():
    r"""Creates the MCP server and tests it locally before serving.

    This function demonstrates how to set up an MCP server from a
    SingleStepEnv and tests it by running a sample interaction.
    """
    # Create the environment
    env = create_math_environment()

    # Set up the environment
    await env.setup()

    # Create MCP server from the environment
    mcp_server = env.to_mcp(
        name="MathSolver",
        description="A single-step environment for solving math problems",
        host="localhost",
        port=8001,
    )

    print("MCP server created successfully!")
    print("Available tools:")

    # Clean up
    await env.close()

    return mcp_server


if __name__ == "__main__":
    # Run the setup function to create the MCP server
    loop = asyncio.get_event_loop()
    mcp_server = loop.run_until_complete(setup_and_test_mcp_server())

    print("\nStarting MCP server on http://localhost:8001")
    print("You can now connect to this server using an MCP client.")

    # Run the server
    mcp_server.run(transport="streamable-http")
