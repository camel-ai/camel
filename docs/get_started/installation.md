---
title: Installation
description: Get started with CAMEL-AI - Install, configure, and build your first multi-agent system
icon: wrench
---

## Tutorial
<Note>
  **Python Version Requirements**

  CAMEL-AI requires `Python >=3.10 and <=3.14`. Here's how to check your version:
  ```bash
  python3 --version
  ```

  If you need to update Python, visit [python.org/downloads](https://python.org/downloads)
</Note>

CAMEL-AI supports multiple installation methods to suit different development workflows. Choose the method that best fits your needs.

<Steps>
    <Step title="Install CAMEL-AI 🐪">
      - **Basic Installation:**

        Install the core CAMEL library:

        ```shell
        pip install camel-ai
        ```

      - **Full Installation (Recommended):**

        Install CAMEL with all features and dependencies:

        ```shell
        pip install 'camel-ai[all]'
        ```

        <Note>
          Some features may not work without their required dependencies. Install `camel-ai[all]` to ensure all dependencies are available, or install specific extras based on the features you need.
        </Note>

      - **Custom Installation:**

        Available extras for specific use cases:
        - `all`: Includes all features below
        - `model_platforms`: OpenAI, Google, Mistral, Anthropic Claude, Cohere etc.
        - `huggingface`: Transformers, Diffusers, Accelerate, Datasets, PyTorch etc.
        - `rag`: Sentence Transformers, Qdrant, Milvus, TiDB, BM25, OceanBase, Weaviate, chroma etc.
        - `storage`: Neo4j, Redis, Azure Blob, Google Cloud Storage, AWS S3 etc, Pgvector.
        - `web_tools`: DuckDuckGo, Wikipedia, WolframAlpha, Google Maps, Weather API etc.
        - `document_tools`: PDF, Word, OpenAPI, BeautifulSoup, Unstructured etc.
        - `media_tools`: Image Processing, Audio Processing, YouTube Download, FFmpeg etc.
        - `communication_tools`: Slack, Discord, Telegram, GitHub, Reddit, Notion etc.
        - `data_tools`: Pandas, TextBlob, DataCommons, OpenBB, Stripe etc.
        - `research_tools`: arXiv, Google Scholar etc.
        - `dev_tools`: Docker, Jupyter, Tree-sitter, Code Interpreter etc.

        Multiple extras can be combined:
        ```shell
        pip install 'camel-ai[rag,web_tools,document_tools]'  # Example: RAG system with web search and document processing
        ```

      - To verify that `camel-ai` is installed, run:
        ```shell
        pip show camel-ai
        ```

      <Check>Installation successful! You're ready to create your first multi-agent system! 🎉</Check>
    </Step>
</Steps>

# Creating a CAMEL-AI Project

We recommend starting with a simple role-playing scenario to understand CAMEL's multi-agent capabilities. Here's how to get started:

<Steps>
  <Step title="Set Up Your Project Structure">
    - Create a new project directory:
      ```shell
      mkdir my_camel_project
      cd my_camel_project
      ```
  </Step>

  <Step title="Configure Your Environment">
    - Create a `.env` file with your API keys:
      ```bash
      OPENAI_API_KEY=<your_openai_api_key>
      OPENAI_API_BASE_URL=<your_openai_base_url>  # Optional: for proxy services
      ANTHROPIC_API_KEY=<your_anthropic_api_key>
      GOOGLE_API_KEY=<your_google_api_key>
      ```

    - Create a `requirements.txt` file:
      ```txt
      camel-ai[all]
      python-dotenv
      ```
  </Step>

  <Step title="Install Dependencies and Run">
    - Install project dependencies:
      ```bash
      pip install -r requirements.txt
      ```
    
    - Set up your environment variables by loading the `.env` file:
      ```python
      from dotenv import load_dotenv
      load_dotenv()
      ```

    - Run your first multi-agent example:
      ```bash
      python examples/role_playing.py
      ```

      
<Tip>
Want to see multi-agent collaboration at scale?
Try running the <a href="https://github.com/camel-ai/camel/tree/master/examples/workforce" target="_blank">workforce example</a>:

<code>python examples/workforce/multiple_single_agents.py</code>
</Tip>
  </Step>
</Steps>

## Alternative Installation Methods

<Note type="info">
CAMEL-AI offers multiple installation approaches for different development needs:

### From Docker
- Containerized deployment with pre-configured environment
- Detailed guidance available at [CAMEL Docker Guide](https://github.com/camel-ai/camel/blob/master/.container/README.md)

### From Source with UV
- Development installation with full source access
- Supports Python 3.10, 3.11, 3.12, 3.13, 3.14
- Includes development tools and testing capabilities

<Warning>
**Python 3.13+ Compatibility Notes:**
- `unstructured` and `pyobvector` packages are not available on Python 3.13+
- These packages require NumPy < 2.0, which is incompatible with Python 3.13+
- If you need these features, use Python 3.10-3.12
- All other features work normally on Python 3.13+
</Warning>

```bash
# Clone the repository
git clone https://github.com/camel-ai/camel.git
cd camel

# Install UV package manager
pip install uv

# Create virtual environment
uv venv .venv --python=3.10

# Activate environment (macOS/Linux)
source .venv/bin/activate
# For Windows: .venv\Scripts\activate

# Install CAMEL with all dependencies
uv pip install -e ".[all, dev, docs]"
```

<Card title="Explore Development Setup" icon="code" href="https://github.com/camel-ai/camel">
  Learn about contributing to CAMEL-AI and development best practices
</Card>
</Note>

## Configuration Options

<Steps>
  <Step title="Set Default Model Configuration">
    Configure default model platform and type using environment variables:
    ```bash
    export DEFAULT_MODEL_PLATFORM_TYPE=openai  # e.g., openai, anthropic, etc.
    export DEFAULT_MODEL_TYPE=gpt-4o-mini      # e.g., gpt-3.5-turbo, gpt-4o-mini, etc.
    ```

    By default, CAMEL uses:
    ```bash
    ModelPlatformType.DEFAULT = "openai"
    ModelType.DEFAULT = "gpt-4o-mini"
    ```
  </Step>

  <Step title="Set Up API Keys">
    **For Bash shell (Linux, macOS, Git Bash on Windows):**
    ```bash
    export OPENAI_API_KEY=<insert your OpenAI API key>
    export OPENAI_API_BASE_URL=<insert your OpenAI API BASE URL>  # Optional
    ```

    **For Windows Command Prompt:**
    ```cmd
    set OPENAI_API_KEY=<insert your OpenAI API key>
    set OPENAI_API_BASE_URL=<insert your OpenAI API BASE URL>
    ```

    **For Windows PowerShell:**
    ```powershell
    $env:OPENAI_API_KEY="<insert your OpenAI API key>"
    $env:OPENAI_API_BASE_URL="<insert your OpenAI API BASE URL>"
    ```

    **Using .env File (Recommended):**
    ```bash
    OPENAI_API_KEY=<fill your API KEY here>
    ANTHROPIC_API_KEY=<fill your Anthropic API KEY here>
    GOOGLE_API_KEY=<fill your Google API KEY here>
    ```

    Load in Python:
    ```python
    from dotenv import load_dotenv
    load_dotenv()  # Use load_dotenv(override=True) to overwrite existing variables
    ```
  </Step>
</Steps>

## Running Examples

After setting up your API keys, explore CAMEL's capabilities:

```bash
# Two agents role-playing and collaborating
python examples/ai_society/role_playing.py

# Agent utilizing code execution tools
python examples/toolkits/code_execution_toolkit.py

# Generating knowledge graphs with agents
python examples/knowledge_graph/knowledge_graph_agent_example.py  

# Multiple agents collaborating on complex tasks
python examples/workforce/multiple_single_agents.py 

# Creative image generation with agents
python examples/vision/image_crafting.py
```

## Testing Your Installation

Run the test suite to ensure everything is working:

```bash
# Activate virtual environment first
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Run all tests
pytest --fast-test-mode test/

# Run specific test categories
pytest -v apps/
pytest -v examples/
```

## Next Steps

<CardGroup cols={2}>
  <Card
    title="Build Your First Agent"
    icon="users"
    href="/basic_concepts/create_your_first_agent"
  >
    Follow our quickstart guide to create role-playing agents and see CAMEL in action.
  </Card>
  <Card
    title="Explore Advanced Features & Cookbooks"
    icon="bookmark"
    href="/cookbooks/"
  >
    Discover RAG systems, tool integration, and complex multi-agent cookbooks.
  </Card>
  <Card
    title="Join the Community"
    icon="comments"
    href="discord.camel-ai.org"
  >
    Connect with other developers, contribute, and share your CAMEL experiences.
  </Card>
  <Card
    title="API Documentation"
    icon="book"
    href="/reference"
  >
    Dive deep into CAMEL's API and advanced configuration options.
  </Card>
</CardGroup>

For additional feature examples and use cases, explore the [`examples`](https://github.com/camel-ai/camel/tree/master/examples) directory in the CAMEL repository.
