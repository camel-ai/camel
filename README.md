<div style="left">
  <a href="https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing" target="_blank">
    <img alt="Open In Colab" src="https://colab.research.google.com/assets/colab-badge.svg" />
  </a>
  <a href="https://huggingface.co/camel-ai" target="_blank">
    <img alt="Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-CAMEL--AI-ffc107?color=ffc107&logoColor=white" />
  </a>
  <a href="https://join.slack.com/t/camel-kwr1314/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA" target="_blank">
      <img alt="Slack" src="https://img.shields.io/badge/Slack-CAMEL--AI-blueviolet?logo=slack" />
  </a>
  <a href="https://discord.gg/CNcNpquyDc" target="_blank">
    <img alt="Discord" src="https://img.shields.io/badge/Discord-CAMEL--AI-7289da?logo=discord&logoColor=white&color=7289da" />
  </a>
  <a href="https://ghli.org/camel/wechat.png" target="_blank">
    <img alt="Discord" src="https://img.shields.io/badge/WeChat-CamelAIOrg-brightgreen?logo=wechat&logoColor=white" />
  </a>
  <a href="https://twitter.com/CamelAIOrg" target="_blank">
    <img alt="Twitter Follow" src="https://img.shields.io/twitter/follow/CamelAIOrg?style=social&color=brightgreen&logo=twitter" />
  </a>
</div>

# CAMEL: Communicative Agents for “Mind” Exploration of Large Scale Language Model Society

<div align="center">

  <a>![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)</a>
  <a href="https://github.com/camel-ai/camel/actions/workflows/pytest_package.yml">![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/camel-ai/camel/pytest_package.yml?label=tests&logo=github)</a>
  <a href="https://camel-ai.github.io/camel/">
    ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/camel-ai/camel/documentation.yaml?label=docs&logo=github)
  </a>
  <a href="https://github.com/camel-ai/camel/stargazers" target="_blank">
  <img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/camel-ai/camel?label=stars&logo=github&color=brightgreen" />
  </a>
  <a href="https://github.com/camel-ai/camel/blob/master/licenses/LICENSE">![License](https://img.shields.io/github/license/camel-ai/camel?label=license&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiBmaWxsPSIjZmZmZmZmIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0xMi43NSAyLjc1YS43NS43NSAwIDAwLTEuNSAwVjQuNUg5LjI3NmExLjc1IDEuNzUgMCAwMC0uOTg1LjMwM0w2LjU5NiA1Ljk1N0EuMjUuMjUgMCAwMTYuNDU1IDZIMi4zNTNhLjc1Ljc1IDAgMTAwIDEuNUgzLjkzTC41NjMgMTUuMThhLjc2Mi43NjIgMCAwMC4yMS44OGMuMDguMDY0LjE2MS4xMjUuMzA5LjIyMS4xODYuMTIxLjQ1Mi4yNzguNzkyLjQzMy42OC4zMTEgMS42NjIuNjIgMi44NzYuNjJhNi45MTkgNi45MTkgMCAwMDIuODc2LS42MmMuMzQtLjE1NS42MDYtLjMxMi43OTItLjQzMy4xNS0uMDk3LjIzLS4xNTguMzEtLjIyM2EuNzUuNzUgMCAwMC4yMDktLjg3OEw1LjU2OSA3LjVoLjg4NmMuMzUxIDAgLjY5NC0uMTA2Ljk4NC0uMzAzbDEuNjk2LTEuMTU0QS4yNS4yNSAwIDAxOS4yNzUgNmgxLjk3NXYxNC41SDYuNzYzYS43NS43NSAwIDAwMCAxLjVoMTAuNDc0YS43NS43NSAwIDAwMC0xLjVIMTIuNzVWNmgxLjk3NGMuMDUgMCAuMS4wMTUuMTQuMDQzbDEuNjk3IDEuMTU0Yy4yOS4xOTcuNjMzLjMwMy45ODQuMzAzaC44ODZsLTMuMzY4IDcuNjhhLjc1Ljc1IDAgMDAuMjMuODk2Yy4wMTIuMDA5IDAgMCAuMDAyIDBhMy4xNTQgMy4xNTQgMCAwMC4zMS4yMDZjLjE4NS4xMTIuNDUuMjU2Ljc5LjRhNy4zNDMgNy4zNDMgMCAwMDIuODU1LjU2OCA3LjM0MyA3LjM0MyAwIDAwMi44NTYtLjU2OWMuMzM4LS4xNDMuNjA0LS4yODcuNzktLjM5OWEzLjUgMy41IDAgMDAuMzEtLjIwNi43NS43NSAwIDAwLjIzLS44OTZMMjAuMDcgNy41aDEuNTc4YS43NS43NSAwIDAwMC0xLjVoLTQuMTAyYS4yNS4yNSAwIDAxLS4xNC0uMDQzbC0xLjY5Ny0xLjE1NGExLjc1IDEuNzUgMCAwMC0uOTg0LS4zMDNIMTIuNzVWMi43NXpNMi4xOTMgMTUuMTk4YTUuNDE4IDUuNDE4IDAgMDAyLjU1Ny42MzUgNS40MTggNS40MTggMCAwMDIuNTU3LS42MzVMNC43NSA5LjM2OGwtMi41NTcgNS44M3ptMTQuNTEtLjAyNGMuMDgyLjA0LjE3NC4wODMuMjc1LjEyNi41My4yMjMgMS4zMDUuNDUgMi4yNzIuNDVhNS44NDYgNS44NDYgMCAwMDIuNTQ3LS41NzZMMTkuMjUgOS4zNjdsLTIuNTQ3IDUuODA3eiI+PC9wYXRoPjwvc3ZnPgo=)</a>
</div>

<p align="center">
   <a href="https://github.com/camel-ai/camel#community">Community</a> |
  <a href="https://github.com/camel-ai/camel#installation">Installation</a> |
  <a href="https://camel-ai.github.io/camel/">Documentation</a> |
  <a href="https://github.com/camel-ai/camel/tree/HEAD/examples">Examples</a> |
  <a href="https://arxiv.org/abs/2303.17760">Paper</a> |
  <a href="https://github.com/camel-ai/camel#citation">Citation</a> |
  <a href="https://github.com/camel-ai/camel#contributing-to-camel-">Contributing</a> |
  <a href="https://www.camel-ai.org/">CAMEL-AI</a>
</p>

<p align="center">
  <img src='https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo.png' width=800>
</p>

## Overview
The rapid advancement of conversational and chat-based language models has led to remarkable progress in complex task-solving. However, their success heavily relies on human input to guide the conversation, which can be challenging and time-consuming. This paper explores the potential of building scalable techniques to facilitate autonomous cooperation among communicative agents and provide insight into their "cognitive" processes. To address the challenges of achieving autonomous cooperation, we propose a novel communicative agent framework named *role-playing*. Our approach involves using *inception prompting* to guide chat agents toward task completion while maintaining consistency with human intentions. We showcase how role-playing can be used to generate conversational data for studying the behaviors and capabilities of chat agents, providing a valuable resource for investigating conversational language models. Our contributions include introducing a novel communicative agent framework, offering a scalable approach for studying the cooperative behaviors and capabilities of multi-agent systems, and open-sourcing our library to support research on communicative agents and beyond. The GitHub repository of this project is made publicly available on: [https://github.com/camel-ai/camel](https://github.com/camel-ai/camel).

## Community
🐫 CAMEL is an open-source library designed for the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we implement and support various types of agents, tasks, prompts, models, and simulated environments.

Join us ([*Slack*](https://join.slack.com/t/camel-kwr1314/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA), [*Discord*](https://discord.gg/CNcNpquyDc) or [*WeChat*](https://ghli.org/camel/wechat.png)) in pushing the boundaries of building AI Societiy.

## Try it yourself
We provide a [![Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing) demo showcasing a conversation between two ChatGPT agents playing roles as a python programmer and a stock trader collaborating on developing a trading bot for stock market.

<p align="center">
  <img src='https://raw.githubusercontent.com/camel-ai/camel/master/misc/framework.png' width=800>
</p>

## Installation

### From PyPI

To install the base camel library, simply run `pip install camel-ai`

Some features reuqire extra dependencies.

To use hugging-face agent, run `pip install camel-ai[huggingface-agent]`

To enable RAG or use agent memory, run `pip install camel-ai[tools]`

To install with all dependencies, run `pip install camel-ai[all]`

### From Source

Install `CAMEL` from source with poetry (Recommended):
```sh
# Make sure your python version is later than 3.9
# You can use pyenv to manage multiple python verisons in your sytstem

# Clone github repo
git clone https://github.com/camel-ai/camel.git

# Change directory into project directory
cd camel

# Activate camel virtual environment
poetry shell

# Install camel from source
# It takes about 90 seconds to resolve dependencies
poetry install

# Or if you want to use "huggingface agent"
poetry install -E huggingface-agent # (Optional)

# do something with camel

# Exit the virtual environment
exit
```

Install `CAMEL` from source with conda and pip:
```sh
# Create a conda virtual environment
conda create --name camel python=3.10

# Activate camel conda environment
conda activate camel

# Clone github repo
git clone -b v0.1.0 https://github.com/camel-ai/camel.git

# Change directory into project directory
cd camel

# Install camel from source
pip install -e .

# Or if you want to use "huggingface agent"
pip install -e .[huggingface-agent] # (Optional)
```

## Documentation

[CAMEL package documentation pages](https://camel-ai.github.io/camel/)

## Example
You can find a list of tasks for different set of assistant and user role pairs [here](https://drive.google.com/file/d/194PPaSTBR07m-PzjS-Ty6KlPLdFIPQDd/view?usp=share_link)

Run the `role_playing.py` script

First, you need to add your OpenAI API key to system environment variables. The method to do this depends on your operating system and the shell you're using.

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

Replace `<insert your OpenAI API key>` with your actual OpenAI API key in each case. Make sure there are no spaces around the `=` sign.

After setting the OpenAI API key, you can run the script:

```bash
# You can change the role pair and initial prompt in role_playing.py
python examples/ai_society/role_playing.py
```

Please note that the environment variable is session-specific. If you open a new terminal window or tab, you will need to set the API key again in that new session.


**For Azure OpenAI API**

First, you need to add your Azure OpenAI API infos to system environment variables. The method to do this depends on your operating system and the shell you're using. Take Bash shell as an example:

```bash
# Export your Azure OpenAI API infos
export AZURE_ENDPOINT=<inert your Azure OpenAI API Endpoint>,
export AZURE_OPENAI_API_KEY= <insert your Azure OpenAI API key>,
export AZURE_DEPLOYMENT_NAME=<insert your Azure OpenAI model's deployment name>
```

Replace `<insert your OpenAI API Endpoint>` with your actual Azure OpenAI API endpoint in each case. Make sure there are no spaces around the `=` sign.

Replace `<insert your Azure OpenAI API key>` with your actual Azure OpenAI API key in each case. Make sure there are no spaces around the `=` sign.

Replace `<insert your Azure OpenAI model's deployment name>` with your actual Azure OpenAI API model deployment name in each case. Make sure there are no spaces around the `=` sign.

The default model type is gpt-3.5-turbo, if your Azure model has a different model deployed, plase change the model_type in `examples/ai_society/role_playing_with_azure.py` to match your model type before running the following command.

```bash
# You can change the role pair and initial prompt in role_playing.py
python examples/ai_society/role_playing_with_azure.py
```

Please note that the environment variable is session-specific. If you open a new terminal window or tab, you will need to set the API key again in that new session.


## Use Open-Source Models as Backends

The basic workflow of using an open-sourced model as the backend is based on an external server running LLM inference service, e.g. during the development we chose [FastChat](https://github.com/lm-sys/FastChat) to run the service. 

We do not fix the choice of server to decouple the implementation of any specific LLM inference server with CAMEL (indicating the server needs to be deployed by the user himself). But the server to be deployed must satisfy that **it supports OpenAI-compatible APIs, especially the method `openai.ChatCompletion.create`**.

Here are some instructions for enabling open-source backends, where we use the [FastChat](https://github.com/lm-sys/FastChat) and a LLaMA2-based model ([`meta-llama/Llama-2-7b-chat-hf`](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)) in the example. Please install FastChat in advance following their installation guidance.

1. Before running CAMEL, we should firstly launch FastChat server following the guidance on https://github.com/lm-sys/FastChat/blob/main/docs/openai_api.md. The instructions summarized below should be kept running **in separate processes**:

```sh
# Launch the controller
python -m fastchat.serve.controller

# Launch the model worker(s)
python3 -m fastchat.serve.model_worker --model-path meta-llama/Llama-2-7b-chat-hf

# Launch the RESTful API server
python3 -m fastchat.serve.openai_api_server --host localhost --port 8000
```

2. After observing the controller successfully receiving the heart beat signal from the worker, the server should be ready for use at http://localhost:8000/v1. 

3. Then we can try on running `role_playing_with_open_source_model.py`, where each agent in this example is initialized with specifying the `model_path` and `server_url`, similar to the example code below:

```python
system_message = # ...

agent_kwargs = dict(
    model=model_type,
    model_config=OpenSourceConfig(
        model_path="meta-llama/Llama-2-7b-chat-hf",
        server_url="http://localhost:8000/v1",
    ),
)

agent = ChatAgent(
    system_message,
    **agent_kwargs,
)
```

### Supported Models

- LLaMA2-based models
  - example: [meta-llama/Llama-2-7b-chat-hf](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)
- Vicuna-based models
  - example: [lmsys/vicuna-7b-v1.5](https://huggingface.co/lmsys/vicuna-7b-v1.5)

## Data (Hosted on Hugging Face)
| Dataset | Chat format | Instruction format | Chat format (translated) |
| -- | -- | -- | -- |
| **AI Society** | [Chat format](https://huggingface.co/datasets/camel-ai/ai_society/blob/main/ai_society_chat.tar.gz) | [Instruction format](https://huggingface.co/datasets/camel-ai/ai_society/blob/main/ai_society_instructions.json) | [Chat format (translated)](https://huggingface.co/datasets/camel-ai/ai_society_translated) |
| **Code** | [Chat format](https://huggingface.co/datasets/camel-ai/code/blob/main/code_chat.tar.gz) | [Instruction format](https://huggingface.co/datasets/camel-ai/code/blob/main/code_instructions.json) | x |
| **Math** | [Chat format](https://huggingface.co/datasets/camel-ai/math) | x | x|
| **Physics** | [Chat format](https://huggingface.co/datasets/camel-ai/physics) | x | x |
| **Chemistry** | [Chat format](https://huggingface.co/datasets/camel-ai/chemistry) | x | x |
| **Biology** | [Chat format](https://huggingface.co/datasets/camel-ai/biology) | x | x |

## Visualizations of Instructions and Tasks

| Dataset | Instructions | Tasks |
| -- | -- | -- |
| **AI Society** | [Instructions](https://atlas.nomic.ai/map/3a559a06-87d0-4476-a879-962656242452/db961915-b254-48e8-8e5c-917f827b74c6) | [Tasks](https://atlas.nomic.ai/map/cb96f41b-a6fd-4fe4-ac40-08e101714483/ae06156c-a572-46e9-8345-ebe18586d02b) |
| **Code** | [Instructions](https://atlas.nomic.ai/map/902d6ccb-0bbb-4294-83a8-1c7d2dae03c8/ace2e146-e49f-41db-a1f4-25a2c4be2457) | [Tasks](https://atlas.nomic.ai/map/efc38617-9180-490a-8630-43a05b35d22d/2576addf-a133-45d5-89a9-6b067b6652dd) |
| **Misalignment** | [Instructions](https://atlas.nomic.ai/map/5c491035-a26e-4a05-9593-82ffb2c3ab40/2bd98896-894e-4807-9ed8-a203ccb14d5e) | [Tasks](https://atlas.nomic.ai/map/abc357dd-9c04-4913-9541-63e259d7ac1f/825139a4-af66-427c-9d0e-f36b5492ab3f) |

## Implemented Research Ideas from Other Works
We implemented amazing research ideas from other works for you to build, compare and customize your agents. If you use any of these modules, please kindly cite the original works:
- `TaskCreationAgent`, `TaskPrioritizationAgent` and `BabyAGI` from *Nakajima et al.*: [Task-Driven Autonomous Agent](https://yoheinakajima.com/task-driven-autonomous-agent-utilizing-gpt-4-pinecone-and-langchain-for-diverse-applications/). [[Example](https://github.com/camel-ai/camel/blob/master/examples/ai_society/babyagi_playing.py)]

## News
- Released AI Society and Code dataset (April 2, 2023)
- Initial release of `CAMEL` python library (March 21, 2023)

## Citation
```
@inproceedings{li2023camel,
  title={CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society},
  author={Li, Guohao and Hammoud, Hasan Abed Al Kader and Itani, Hani and Khizbullin, Dmitrii and Ghanem, Bernard},
  booktitle={Thirty-seventh Conference on Neural Information Processing Systems},
  year={2023}
}
```
## Acknowledgement
Special thanks to [Nomic AI](https://home.nomic.ai/) for giving us extended access to their data set exploration tool (Atlas).

We would also like to thank Haya Hammoud for designing the logo of our project.

## License

The intended purpose and licensing of CAMEL is solely for research use.

The source code is licensed under Apache 2.0.

The datasets are licensed under CC BY NC 4.0, which permits only non-commercial usage. It is advised that any models trained using the dataset should not be utilized for anything other than research purposes.

## Contributing to CAMEL 🐫
We appreciate your interest in contributing to our open-source initiative. We provide a document of [contributing guidelines](https://github.com/camel-ai/camel/blob/master/CONTRIBUTING.md) which outlines the steps for contributing to CAMEL. Please refer to this guide to ensure smooth collaboration and successful contributions. 🤝🚀

## Contact
For more information please contact camel.ai.team@gmail.com.
