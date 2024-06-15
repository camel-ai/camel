# Installation and Setup
## 🕹 Installation

### [Option 1] Install from PyPI
To install the base CAMEL library:
```bash
pip install camel-ai
```
Some features require extra dependencies:
- To install with all dependencies:
    ```bash
    pip install 'camel-ai[all]'
    ```
- To use the HuggingFace agents:
    ```bash
    pip install 'camel-ai[huggingface-agent]'
    ```
- To enable RAG or use agent memory:
    ```bash
    pip install 'camel-ai[tools]'
    ```

### [Option 2] Install from Source
#### Install from Source with Poetry
```bash
# Make sure your python version is later than 3.9
# You can use pyenv to manage multiple python verisons in your sytstem

# Clone github repo
git clone https://github.com/camel-ai/camel.git

# Change directory into project directory
cd camel

# If you didn't install peotry before
pip install poetry  # (Optional)

# We suggest using python 3.10
poetry env use python3.10  # (Optional)

# Activate CAMEL virtual environment
poetry shell

# Install the base CAMEL library
# It takes about 90 seconds
poetry install

# Install CAMEL with all dependencies
poetry install -E all  # (Optional)

# Exit the virtual environment
exit
```

#### Install from Source with Conda and Pip
```bash
# Create a conda virtual environment
conda create --name camel python=3.10

# Activate CAMEL conda environment
conda activate camel

# Clone github repo
git clone -b v0.1.5.1 https://github.com/camel-ai/camel.git

# Change directory into project directory
cd camel

# Install CAMEL from source
pip install -e .

# Or if you want to use all other extra packages
pip install -e '.[all]' # (Optional)
```


## 🕹 API Setup
Our agents can be deployed with either OpenAI API or your local models.

### [Option 1] Using OpenAI API
Assessing the OpenAI API requires the API key, which you may obtained from [here](https://platform.openai.com/account/api-keys). We here provide instructions for different OS.

#### Unix-like System (Linux / MacOS)
```bash
echo 'export OPENAI_API_KEY="your_api_key"' >> ~/.zshrc

# If you are using other proxy services like Azure
echo 'export OPENAI_API_BASE_URL="your_base_url"' >> ~/.zshrc # (Optional)

# Let the change take place
source ~/.zshrc
```

Replace `~/.zshrc` with `~/.bashrc` if you are using bash.

#### Windows
If you are using Command Prompt:
```bash
set OPENAI_API_KEY="your_api_key"

# If you are using other proxy services like Azure
set OPENAI_API_BASE_URL="your_base_url" # (Optional)
```
Or if you are using PowerShell:
```powershell
$env:OPENAI_API_KEY="your_api_key"

# If you are using other proxy services like Azure
$env:OPENAI_API_BASE_URL="your_base_url" # (Optional)
```
These commands on Windows will set the environment variable for the duration of that particular Command Prompt or PowerShell session only. You may use `setx` or change the system properties dialog for the change to take place in all the new sessions.


### [Option 2] Using Local Models
The high-level idea is to deploy a server with the local model in the backend and use it as a local drop-in replacement for the API. We here use [FastChat](https://github.com/lm-sys/FastChat/blob/main/docs/openai_api.md) as an example.

0. Install the FastChat package with the following command, or see [here](https://github.com/lm-sys/FastChat/tree/main#install) for other options.
    ```bash
    pip3 install "fschat[model_worker,webui]"
    ```

1. Starting the FastChat server in the backend.
    ```python
    # Launch the fastchat controller
    python -m fastchat.serve.controller

    # Launch the model worker
    python -m fastchat.serve.model_worker \
        --model-path meta-llama/Llama-2-7b-chat-hf  # a local folder or HuggingFace repo Name

    # Launch the API server
    python -m fastchat.serve.openai_api_server \
        --host localhost \
        --port 8000
    ```


2. Initialize the agent.
    ```python
    # Import the necessary classes
    from camel.configs import ChatGPTConfig, OpenSourceConfig
    from camel.types import ModelType

    # Set the arguments
    agent_kwargs = dict(
        model_type=ModelType.LLAMA_2,                    # Specify the model type

        model_config=OpenSourceConfig(
            model_path='meta-llama/Llama-2-7b-chat-hf',  # a local folder or HuggingFace repo Name
            server_url='http://localhost:8000/v1',       # The url with the set port number
        ),

        token_limit=2046,                                # [Optional] Choose the ideal limit
    )

    # Now your agent is ready to play
    agent = ChatAgent(sys_msg, **agent_kwargs)
    ```
