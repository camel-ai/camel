<!--
Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
# Cloudflare MCP with Camel-ai

This project provides a Streamlit-based web interface to interact with public Cloudflare MCP (Model-Controlled Proxy) servers. It allows users to easily query Cloudflare's documentation, get internet traffic insights from Cloudflare Radar, and perform browser actions like fetching web pages or taking screenshots, all powered by CAMEL AI.

## Features

-   **Interactive UI**: A user-friendly interface built with Streamlit.
-   **Tabbed Navigation**: Separate tabs for different Cloudflare services:
    -   📚 **Documentation Server**: Ask questions and get information from Cloudflare's official documentation.
    -   📊 **Radar Server**: Access insights on global internet traffic trends, URL analysis, DNS analytics, and HTTP protocol analysis.
    -   🌐 **Browser Server**: Fetch web page content, take screenshots of URLs, or convert web pages to Markdown.
-   **Powered by CAMEL AI**: Leverages the CAMEL AI library to interact with the MCP servers and process language queries.
-   **Easy Configuration**: Uses a `mcp_config.json` file to define accessible MCP servers.

## Prerequisites

-   Python 3.10+
-   Node.js and npm (for `npx mcp-remote` if your `mcp_config.json` uses it)
-   A Gemini API Key (or another compatible model API key supported by CAMEL AI)

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    # git clone <repository-url>
    # cd <repository-name>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    If `mcp-remote` is used by your `mcp_config.json` (as in the default configuration for this project), ensure it can be executed. You might need to install it globally or ensure `npx` can run it:
    ```bash
    npm install -g mcp-remote 
    ```

4.  **Set up your API Key:**
    Create a `.env` file in the root directory of the project and add your Gemini API key:
    ```env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```

5.  **Configure MCP Servers:**
    The `mcp_config.json` file lists the MCP servers the application will connect to. The default configuration includes public Cloudflare servers:
    ```json
    {
        "servers": [
            {
                "name": "cloudflare_docs",
                "url": "https://docs.mcp.cloudflare.com/sse"
            },
            {
                "name": "cloudflare_radar",
                "url": "https://radar.mcp.cloudflare.com/sse"
            },
            {
                "name": "cloudflare_browser",
                "url": "https://browser.mcp.cloudflare.com/sse"
            }
        ]
    }
    ```
    If your `mcp_config.json` uses the `mcpServers` block with `command: "npx"` and `args: ["mcp-remote", "..."]`, ensure `npx` and `mcp-remote` are correctly installed and accessible in your system's PATH.

## Running the Application

Once the setup is complete, run the Streamlit application using:

```bash
streamlit run app.py
```

The application will open in your default web browser, usually at `http://localhost:8501`.

## Project Structure

-   `app.py`: The main Streamlit application script.
-   `mcp_config.json`: Configuration file for MCP servers.
-   `requirements.txt`: Python dependencies.
-   `.env`: (You create this) Stores your API key.
-   `README.md`: This file.

## Troubleshooting

-   **`openai.InternalServerError: Error code: 500`**: This usually indicates a temporary issue with the backend LLM service (e.g., Gemini). Try again after a few moments. If persistent, check the status of the LLM provider.
-   **`AttributeError: 'ChatAgentResponse' object has no attribute 'content'`**: Ensure your `app.py` correctly parses the response from `agent.step()`. It should typically be `response.msgs[0].content`.
-   **`mcp-remote` not found**: If your `mcp_config.json` uses `mcp-remote`, ensure it's installed (`npm install -g mcp-remote`) and `npx` is in your system's PATH.

## Contributing

Feel free to open issues or submit pull requests if you have suggestions for improvements or bug fixes. 
