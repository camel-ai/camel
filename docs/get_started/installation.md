🐫 **Welcome to CAMEL!** 🐫

## Installation

### 1. From PyPI

To install the base CAMEL library:
```bash
pip install camel-ai
```

> **Note**: Some features may not work without their required dependencies. Install `camel-ai[all]` to ensure all dependencies are available, or install specific extras based on the features you need.

```bash
pip install 'camel-ai[all]'  # Replace with options below
```

Available extras:
- `all`: Includes all features below
- `model_platforms`: OpenAI, Google, Mistral, Anthropic Claude, Cohere etc.
- `huggingface`: Transformers, Diffusers, Accelerate, Datasets, PyTorch etc.
- `rag`: Sentence Transformers, Qdrant, Milvus, TiDB, BM25 etc.
- `storage`: Neo4j, Redis, Azure Blob, Google Cloud Storage, AWS S3  etc.
- `web_tools`: DuckDuckGo, Wikipedia, WolframAlpha, Google Maps, Weather API etc.
- `document_tools`: PDF, Word, OpenAPI, BeautifulSoup, Unstructured etc.
- `media_tools`: Image Processing, Audio Processing, YouTube Download, FFmpeg etc.
- `communication_tools`: Slack, Discord, Telegram, GitHub, Reddit, Notion etc.
- `data_tools`: Pandas, TextBlob, DataCommons, OpenBB, Stripe etc.
- `research_tools`: arXiv, Google Scholar etc.
- `dev_tools`: Docker, Jupyter, Tree-sitter, Code Interpreter etc.

Multiple extras can be combined using commas:
```bash
pip install 'camel-ai[rag,web_tools,document_tools]'  # Example: RAG system with web search and document processing
```

### 2. From Docker

Detailed guidance can be find [here](https://github.com/camel-ai/camel/blob/master/.container/README.md)


By default, the agent uses the `ModelType.DEFAULT` model from the `ModelPlatformType.DEFAULT`. You can configure the default model platform and model type using environment variables. If these are not set, the agent will fall back to the default settings:

```bash
ModelPlatformType.DEFAULT = "openai"
ModelType.DEFAULT = "gpt-4o-mini"
```

### 3. From Source with uv

```bash
# Clone github repo
git clone https://github.com/camel-ai/camel.git

# Change directory into project directory
cd camel

# Install uv if you don't have it already
pip install uv

# Create a virtual environment and install dependencies
# We support using Python 3.10, 3.11, 3.12
uv venv .venv --python=3.10

# Activate the virtual environment
# For macOS/Linux
source .venv/bin/activate
# For Windows
.venv\Scripts\activate

# Install CAMEL with all dependencies
uv pip install -e ".[all, dev, docs]"

# For developers: Install pre-commit hooks and mypy
uv pip install pre-commit mypy
pre-commit install

# Exit the virtual environment when done
deactivate
```

### 4. Running Tests

To run tests, make sure you have activated the virtual environment first:

```bash
# Activate the virtual environment
# For macOS/Linux
source .venv/bin/activate
# For Windows
.venv\Scripts\activate

# Run tests
pytest --fast-test-mode test/

# Run specific tests
pytest -v apps/
pytest -v examples/

# Exit the virtual environment when done
deactivate
```

### 5. Setting Default Model Platform and Model Type (Optional)

You can customize the default model platform and model type by setting the following environment variables:
```bash
export DEFAULT_MODEL_PLATFORM_TYPE=<your preferred platform>  # e.g., openai, anthropic, etc.
export DEFAULT_MODEL_TYPE=<your preferred model>  # e.g., gpt-3.5-turbo, gpt-4o-mini, etc.
```

### 6. Setting Your Model API Key (Using OpenAI as an Example)

**For Bash shell (Linux, macOS, Git Bash on Windows):**

```bash
# Export your OpenAI API key
export OPENAI_API_KEY=<insert your OpenAI API key>
OPENAI_API_BASE_URL=<inert your OpenAI API BASE URL>  #(Should you utilize an OpenAI proxy service, kindly specify this)
```

**For Windows Command Prompt:**

```cmd
REM export your OpenAI API key
set OPENAI_API_KEY=<insert your OpenAI API key>
set OPENAI_API_BASE_URL=<inert your OpenAI API BASE URL>  #(Should you utilize an OpenAI proxy service, kindly specify this)
```

**For Windows PowerShell:**

```powershell
# Export your OpenAI API key
$env:OPENAI_API_KEY="<insert your OpenAI API key>"
$env:OPENAI_API_BASE_URL="<inert your OpenAI API BASE URL>"  #(Should you utilize an OpenAI proxy service, kindly specify this)
```

Replace `<insert your OpenAI API key>` with your actual OpenAI API key in each case.


Please note that the environment variable is session-specific. If you open a new terminal window or tab, you will need to set the API key again in that new session.

**For `.env` File:**

To simplify the process of managing API Keys, you can use store information in a `.env` file and load them into your application dynamically.

1. Modify .env file in the root directory of CAMEL and fill the following lines:

```bash
OPENAI_API_KEY=<fill your API KEY here>
```

Replace <fill your API KEY here> with your actual API key.

2. Load the .env file in your Python script: Use the load_dotenv() function from the dotenv module to load the variables from the .env file into the environment. Here's an example:

```python
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()
```
For more details about the key names in project and how to apply key, 
you can refer to [here](./setup.md).

> [!TIP]
> By default, the load_dotenv() function does not overwrite existing environment variables that are already set in your system. It only populates variables that are missing.
If you need to overwrite existing environment variables with the values from your `.env` file, use the `override=True` parameter:
> ```python
> load_dotenv(override=True)
> ```

After setting the OpenAI API key, you can run the `role_playing.py` script. Find tasks for various assistant-user roles [here](https://drive.google.com/file/d/194PPaSTBR07m-PzjS-Ty6KlPLdFIPQDd/view?usp=share_link).

```bash
# You can change the role pair and initial prompt in role_playing.py
python examples/ai_society/role_playing.py
```

Also feel free to run any scripts below that interest you:

```bash
# You can change the role pair and initial prompt in these python files

# Examples of two agents role-playing
python examples/ai_society/role_playing.py

# The agent answers questions by utilizing code execution tools.
python examples/toolkits/code_execution_toolkit.py

# Generating a knowledge graph with an agent
python examples/knowledge_graph/knowledge_graph_agent_example.py  

# Multiple agents collaborating to decompose and solve tasks
python examples/workforce/multiple_single_agents.py 

# Use agent to generate creative image
python examples/vision/image_crafting.py
```
For additional feature examples, see the [`examples`](https://github.com/camel-ai/camel/tree/master/examples) directory.

<br>