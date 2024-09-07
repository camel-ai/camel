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
# Make sure your python version is later than 3.10
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
git clone -b v0.1.7.0 https://github.com/camel-ai/camel.git

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
In the current landscape, for those seeking highly stable content generation, OpenAI's GPT-3.5 turbo,  GPT-4o are often recommended. However, the field is rich with many other outstanding open-source models that also yield commendable results. CAMEL can support developers to delve into integrating these open-source large language models (LLMs) to achieve project outputs based on unique input ideas.

#### Example: Using Ollama to set Llama 3 locally

- Download [Ollama](https://ollama.com/download).
- After setting up Ollama, pull the Llama3 model by typing the following command into the terminal:
```bash
ollama pull llama3
```
- Create a ModelFile similar the one below in your project directory.
```bash
FROM llama3

# Set parameters
PARAMETER temperature 0.8
PARAMETER stop Result

# Sets a custom system message to specify the behavior of the chat assistant

# Leaving it blank for now.

SYSTEM """ """
```
- Create a script to get the base model (llama3) and create a custom model using the ModelFile above. Save this as a .sh file:
```bash
#!/bin/zsh

# variables
model_name="llama3"
custom_model_name="camel-llama3"

#get the base model
ollama pull $model_name

#create the model file
ollama create $custom_model_name -f ./Llama3ModelFile
```
- Navigate to the directory where the script and ModelFile are located and run the script. Enjoy your Llama3 model, enhanced by CAMEL's excellent agents.
```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llama3",
    url="http://localhost:11434/v1",
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)
agent = ChatAgent(assistant_sys_msg, model=ollama_model, token_limit=4096)

user_msg = BaseMessage.make_user_message(
    role_name="User", content="Say hi to CAMEL"
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
```
