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
"""
Example script demonstrating the to_openai_compatible_server() method.

This shows how to create an OpenAI-compatible server from a ChatAgent
and serve it with uvicorn.
"""

from camel.agents import ChatAgent


def main():
    # Create a ChatAgent instance
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        # You can specify any model supported by CAMEL
        # model="gpt-4o-mini",  # Uncomment to use a specific model
    )

    # Create the FastAPI server
    app = agent.to_openai_compatible_server()

    # You can now serve the app with uvicorn
    print("Starting OpenAI-compatible server on http://localhost:8000")
    print("API endpoint: http://localhost:8000/v1/chat/completions")
    print("Press Ctrl+C to stop the server")

    try:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        print("\nError: uvicorn not installed.")
        print("Install it with: pip install uvicorn")
        print(
            "Then run: uvicorn example_openai_server:app "
            "--host 0.0.0.0 --port 8000"
        )

        # Return the app so it can be imported and used with uvicorn command
        return app

    return app


# For uvicorn command line usage:
# uvicorn example_openai_server:app --host 0.0.0.0 --port 8000
app = None

if __name__ == "__main__":
    app = main()
else:
    # If imported, create the app
    agent = ChatAgent(system_message="You are a helpful assistant.")
    app = agent.to_openai_compatible_server()
