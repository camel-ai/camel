<div align="center">
  <a href="https://www.camel-ai.org/">
    <img src="docs/images/banner.png" alt="Banner">
  </a>
</div>

</br>

<div align="center">

[![Documentation][docs-image]][docs-url]
[![Discord][discord-image]][discord-url]
[![X][x-image]][x-url]
[![Reddit][reddit-image]][reddit-url]
[![Wechat][wechat-image]][wechat-url]
[![Hugging Face][huggingface-image]][huggingface-url]
[![Star][star-image]][star-url]
[![Package License][package-license-image]][package-license-url]

</div>

<div align="left">

<p style="line-height: 1.5;"> 🐫 CAMEL is an open-source community dedicated to finding the scaling laws of agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we implement and support various types of agents, tasks, prompts, models, and simulated environments.</p>

Join us ([*Discord*](https://discord.camel-ai.org/) or [*WeChat*](https://ghli.org/camel/wechat.png)) in pushing the boundaries of finding the scaling laws of agents.


</div>

<h4 align="left">

[Community](https://github.com/camel-ai/camel#community) |
[Installation](https://github.com/camel-ai/camel#installation) |
[Examples](https://github.com/camel-ai/camel/tree/HEAD/examples) |
[Paper](https://arxiv.org/abs/2303.17760) |
[Citation](https://github.com/camel-ai/camel#citation) |
[Contributing](https://github.com/camel-ai/camel#contributing-to-camel-) |
[CAMEL-AI](https://www.camel-ai.org/)

</h4>


## 🌟　When to Choose CAMEL-AI Over Other Frameworks?

```bash
##If you need multi-agent collaboration
CAMEL-AI is purpose-built for creating and managing systems where multiple agents interact and collaborate.

##If you're conducting research
CAMEL-AI research-first design makes it the go-to framework for academic and experimental projects.

##If you require high customizability
CAMEL-AI offers unparalleled flexibility in defining agent behaviors and workflows.

##If you're tackling complex, decomposable tasks
CAMEL-AI task decomposition capabilities make it ideal for breaking down and solving intricate problems.
```


| Feature | CAMEL-AI | LangChain | AutoGen | Crew-AI | AutoGPT |
|---------|----------|-----------|----------|----------|----------|
| Multi-Agent Focus | ✅ Optimized | ❌ General-purpose | ✅ Optimized | ❌ Human-AI focus | ❌ Single-agent focus |
| Task Decomposition | ✅ Excellent | ❌ Limited | ❌ Moderate | ❌ Limited | ❌ Limited |
| Customizability | ✅ High | ✅ Moderate | ✅ High | ❌ Low | ❌ Low |
| Research-Oriented | ✅ Strong focus | ❌ General-purpose | ❌ Production-focused | ❌ Hybrid workflows | ❌ Automation-focused |
| Scalability | ✅ Large-scale systems | ✅ Moderate | ✅ Large-scale systems | ❌ Small-scale | ❌ Moderate |



##  Quick Start

### 1. Install CAMEL

#### 1.1 Install from PyPI
To install the base CAMEL library:
```bash
pip install camel-ai
```
Some features require extra dependencies:

To install with all dependencies:
```bash
pip install 'camel-ai[all]'  # Replace with other options like `rag`, `document_tools`
```

#### 1.2 Install from Source with Poetry
```bash
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

### 2. Explore Different Types of Agents
Explore different types of agents, their roles, and their applications.

- **[Creating Your First Agent](https://docs.camel-ai.org/cookbooks/basic_concepts/create_your_first_agent.html)**
- **[Creating Your First Agent Society](https://docs.camel-ai.org/cookbooks/basic_concepts/create_your_first_agents_society.html)**
- **[Embodied Agents](https://docs.camel-ai.org/cookbooks/advanced_features/embodied_agents.html)**
- **[Critic Agents](https://docs.camel-ai.org/cookbooks/advanced_features/critic_agents_and_tree_search.html)**

We provide a [![Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing) demo showcasing a conversation between two ChatGPT agents playing roles as a python programmer and a stock trader collaborating on developing a trading bot for stock market.

<div align="center">
  <a href="https://arxiv.org/abs/2303.17760">
    <img src="docs/images/role_playing.png" alt="Role Playing">
  </a>
</div>

## 💡 What Can You Build With CAMEL?

### 1. Data Generation
description of datageneration
- function-calling
- CoT Data
- Distillation reason
- cases & links cooklinks

### 2. Task Automation

- RolePlaying

RolePlaying was designed in an instruction-following manner. These roles independently undertake the responsibilities of executing and planning tasks, respectively. The dialogue is continuously advanced through a turn-taking mechanism, thereby collaborating to complete tasks. 

https://docs.camel-ai.org/cookbooks/applications/dynamic_travel_planner.html

- Workforce

Workforce is a system where multiple agents work together to solve tasks. By using Workforce, users can quickly set up a multi-agent task solving system with customized configurations. In this section, we will give a brief view on the architecture of workforce, and how you can configure and utilize it to solve tasks.

https://docs.camel-ai.org/cookbooks/multi_agent_society/workforce_judge_committee.html

- RAG Pipeline

Graph RAG utilize LLM to extract and structure knowledge from a given content source, and store this information in graph database. Subsequently, we can leverage a hybrid approach, combining vector retrieval and knowledge graph retrieval, to query and explore the stored knowledge.

https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_graph_rag.html

### 3. World Simulation

- OASIS

<br/>

## TechStack
[Image]

### 🔑 Key Modules
Core components and utilities to build, operate, and enhance CAMEL-AI agents and societies.

| Module | Description |
|:---|:---|
| **[Models](https://docs.camel-ai.org/key_modules/models.html)** | Model architectures and customization options for agent intelligence. |
| **[Messages](https://docs.camel-ai.org/key_modules/messages.html)** | Messaging protocols for agent communication. |
| **[Memory](https://docs.camel-ai.org/key_modules/memory.html)** | Memory storage and retrieval mechanisms. |
| **[Tools](https://docs.camel-ai.org/key_modules/tools.html)** | Tools integration for specialized agent tasks. |
| **[Prompts](https://docs.camel-ai.org/key_modules/prompts.html)** | Prompt engineering and customization. |
| **[Tasks](https://docs.camel-ai.org/key_modules/tasks.html)** | Task creation and management for agent workflows. |
| **[Loaders](https://docs.camel-ai.org/key_modules/loaders.html)** | Data loading tools for agent operation. |
| **[Storages](https://docs.camel-ai.org/key_modules/storages.html)** | Storage solutions for agent. |
| **[Society](https://docs.camel-ai.org/key_modules/society.html)** | Components for building agent societies and inter-agent collaboration. |
| **[Embeddings](https://docs.camel-ai.org/key_modules/embeddings.html)** | Embedding models for RAG. |
| **[Retrievers](https://docs.camel-ai.org/key_modules/retrievers.html)** | Retrieval methods for knowledge access. |
---

## 📦 Installation

### From PyPI

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
- `rag`: Sentence Transformers, Qdrant, Milvus, BM25 etc.
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

### From Docker

Detailed guidance can be find [here](https://github.com/camel-ai/camel/blob/master/.container/README.md)


By default, the agent uses the `ModelType.DEFAULT` model from the `ModelPlatformType.DEFAULT`. You can configure the default model platform and model type using environment variables. If these are not set, the agent will fall back to the default settings:

```bash
ModelPlatformType.DEFAULT = "openai"
ModelType.DEFAULT = "gpt-4o-mini"
```

### From Source with Poetry
```bash
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

### Setting Default Model Platform and Model Type (Optional)

You can customize the default model platform and model type by setting the following environment variables:
```bash
export DEFAULT_MODEL_PLATFORM_TYPE=<your preferred platform>  # e.g., openai, anthropic, etc.
export DEFAULT_MODEL_TYPE=<your preferred model>  # e.g., gpt-3.5-turbo, gpt-4o-mini, etc.
```

### Setting Your Model API Key (Using OpenAI as an Example)

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
you can refer to [here](https://github.com/camel-ai/camel/.env).

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


## 📖 Cookbooks (Usecase)
Practical guides and tutorials for implementing specific functionalities in CAMEL-AI agents and societies.

### 1. Basic Concepts
| Cookbook | Description |
|:---|:---|
| **[Creating Your First Agent](https://docs.camel-ai.org/cookbooks/basic_concepts/create_your_first_agent.html)** | A step-by-step guide to building your first agent. |
| **[Creating Your First Agent Society](https://docs.camel-ai.org/cookbooks/basic_concepts/create_your_first_agents_society.html)** | Learn to build a collaborative society of agents. |
| **[Message Cookbook](https://docs.camel-ai.org/cookbooks/basic_concepts/agents_message.html)** | Best practices for message handling in agents. |

### 2. Advanced Features
| Cookbook | Description |
|:---|:---|
| **[Tools Cookbook](https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_tools.html)** | Integrating tools for enhanced functionality. |
| **[Memory Cookbook](https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_memory.html)** | Implementing memory systems in agents. |
| **[RAG Cookbook](https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_rag.html)** | Recipes for Retrieval-Augmented Generation. |
| **[Graph RAG Cookbook](https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_graph_rag.html)** | Leveraging knowledge graphs with RAG. |
| **[Track CAMEL Agents with AgentOps](https://docs.camel-ai.org/cookbooks/advanced_features/agents_tracking.html)** | Tools for tracking and managing agents in operations. |

### 3. Model Training & Data Generation
| Cookbook | Description |
|:---|:---|
| **[Data Generation with CAMEL and Finetuning with Unsloth](https://docs.camel-ai.org/cookbooks/model_training/sft_data_generation_and_unsloth_finetuning_Qwen2_5_7B.html)** | Learn how to generate data with CAMEL and fine-tune models effectively with Unsloth. |
| **[Data Gen with Real Function Calls and Hermes Format](https://docs.camel-ai.org/cookbooks/model_training/data_gen_with_real_function_calls_and_hermes_format.html)** | Explore how to generate data with real function calls and the Hermes format. |
| **[CoT Data Generation and Upload Data to Huggingface](https://docs.camel-ai.org/cookbooks/model_training/cot_data_gen_upload_to_huggingface.html)** | Uncover how to generate CoT data with CAMEL and seamlessly upload it to Huggingface. |
| **[CoT Data Generation and SFT Qwen with Unsolth](https://docs.camel-ai.org/cookbooks/model_training/cot_data_gen_sft_qwen_unsolth_upload_huggingface.html)** | Discover how to generate CoT data using CAMEL and SFT Qwen with Unsolth, and seamlessly upload your data and model to Huggingface. |

### 4. Multi-Agent Systems & Applications
| Cookbook | Description |
|:---|:---|
| **[Role-Playing Scraper for Report & Knowledge Graph Generation](https://docs.camel-ai.org/cookbooks/applications/roleplaying_scraper.html)** | Create role-playing agents for data scraping and reporting. |
| **[Create A Hackathon Judge Committee with Workforce](https://docs.camel-ai.org/cookbooks/multi_agent_society/workforce_judge_committee.html)** | Building a team of agents for collaborative judging. |
| **[Customer Service Discord Bot with Agentic RAG](https://docs.camel-ai.org/cookbooks/applications/customer_service_Discord_bot_using_SambaNova_with_agentic_RAG.html)** | Learn how to build a robust customer service bot for Discord using Agentic RAG. |
| **[Customer Service Discord Bot with Local Model](https://docs.camel-ai.org/cookbooks/applications/customer_service_Discord_bot_using_local_model_with_agentic_RAG.html)** | Learn how to build a robust customer service bot for Discord using Agentic RAG which supports local deployment. |

### 5. Data Processing
| Cookbook | Description |
|:---|:---|
| **[Video Analysis](https://docs.camel-ai.org/cookbooks/data_processing/video_analysis.html)** | Techniques for agents in video data analysis. |
| **[3 Ways to Ingest Data from Websites with Firecrawl](https://docs.camel-ai.org/cookbooks/data_processing/ingest_data_from_websites_with_Firecrawl.html)** | Explore three methods for extracting and processing data from websites using Firecrawl. |
| **[Create AI Agents that work with your PDFs](https://docs.camel-ai.org/cookbooks/data_processing/agent_with_chunkr_for_pdf_parsing.html)** | Learn how to create AI agents that work with your PDFs using Chunkr and Mistral AI. |

## 🔀 Utilize Various LLMs as Backends

For more details, please see our [`Models Documentation`](https://docs.camel-ai.org/key_modules/models.html#).

## 🔗 Data (Hosted on Hugging Face)
| Dataset        | Chat format                                                                                         | Instruction format                                                                                               | Chat format (translated)                                                                   |
|----------------|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| **AI Society** | [Chat format](https://huggingface.co/datasets/camel-ai/ai_society/blob/main/ai_society_chat.tar.gz) | [Instruction format](https://huggingface.co/datasets/camel-ai/ai_society/blob/main/ai_society_instructions.json) | [Chat format (translated)](https://huggingface.co/datasets/camel-ai/ai_society_translated) |
| **Code**       | [Chat format](https://huggingface.co/datasets/camel-ai/code/blob/main/code_chat.tar.gz)             | [Instruction format](https://huggingface.co/datasets/camel-ai/code/blob/main/code_instructions.json)             | x                                                                                          |
| **Math**       | [Chat format](https://huggingface.co/datasets/camel-ai/math)                                        | x                                                                                                                | x                                                                                          |
| **Physics**    | [Chat format](https://huggingface.co/datasets/camel-ai/physics)                                     | x                                                                                                                | x                                                                                          |
| **Chemistry**  | [Chat format](https://huggingface.co/datasets/camel-ai/chemistry)                                   | x                                                                                                                | x                                                                                          |
| **Biology**    | [Chat format](https://huggingface.co/datasets/camel-ai/biology)                                     | x                                                                                                                | x                                                                                          |

## 📊 Visualizations of Instructions and Tasks

| Dataset          | Instructions                                                                                                         | Tasks                                                                                                         |
|------------------|----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| **AI Society**   | [Instructions](https://atlas.nomic.ai/map/3a559a06-87d0-4476-a879-962656242452/db961915-b254-48e8-8e5c-917f827b74c6) | [Tasks](https://atlas.nomic.ai/map/cb96f41b-a6fd-4fe4-ac40-08e101714483/ae06156c-a572-46e9-8345-ebe18586d02b) |
| **Code**         | [Instructions](https://atlas.nomic.ai/map/902d6ccb-0bbb-4294-83a8-1c7d2dae03c8/ace2e146-e49f-41db-a1f4-25a2c4be2457) | [Tasks](https://atlas.nomic.ai/map/efc38617-9180-490a-8630-43a05b35d22d/2576addf-a133-45d5-89a9-6b067b6652dd) |
| **Misalignment** | [Instructions](https://atlas.nomic.ai/map/5c491035-a26e-4a05-9593-82ffb2c3ab40/2bd98896-894e-4807-9ed8-a203ccb14d5e) | [Tasks](https://atlas.nomic.ai/map/abc357dd-9c04-4913-9541-63e259d7ac1f/825139a4-af66-427c-9d0e-f36b5492ab3f) |


## 🔬 Research

### We warmly invite you to use CAMEL for your impactful research. 🙌

<div align="center">
  <a href="https://crab.camel-ai.org/">
    <img src="docs/images/crab.png" alt="CRAB">
  </a>
</div>

<div align="center">
  <a href="https://www.agent-trust.camel-ai.org/">
    <img src="docs/images/agent_trust.png" alt="Agent Trust">
  </a>
</div>

<div align="center">
  <a href="https://oasis.camel-ai.org/">
    <img src="docs/images/oasis.png" alt="OASIS">
  </a>
</div>

<div align="center">
  <a href="https://emos-project.github.io/">
    <img src="docs/images/emos.png" alt="Emos">
  </a>
</div>

## 🏛️ Citation
```
@inproceedings{li2023camel,
  title={CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society},
  author={Li, Guohao and Hammoud, Hasan Abed Al Kader and Itani, Hani and Khizbullin, Dmitrii and Ghanem, Bernard},
  booktitle={Thirty-seventh Conference on Neural Information Processing Systems},
  year={2023}
}
```
## 📜 Acknowledgment
Special thanks to [Nomic AI](https://home.nomic.ai/) for giving us extended access to their data set exploration tool (Atlas).

We would also like to thank Haya Hammoud for designing the initial logo of our project.

We implemented amazing research ideas from other works for you to build, compare and customize your agents. If you use any of these modules, please kindly cite the original works:
- `TaskCreationAgent`, `TaskPrioritizationAgent` and `BabyAGI` from *Nakajima et al.*: [Task-Driven Autonomous Agent](https://yoheinakajima.com/task-driven-autonomous-agent-utilizing-gpt-4-pinecone-and-langchain-for-diverse-applications/). [[Example](https://github.com/camel-ai/camel/blob/master/examples/ai_society/babyagi_playing.py)]

- `PersonaHub` from *Tao Ge et al.*: [Scaling Synthetic Data Creation with 1,000,000,000 Personas](https://arxiv.org/pdf/2406.20094). [[Example](https://github.com/camel-ai/camel/blob/master/examples/personas/personas_generation.py)]

- `Self-Instruct` from *Yizhong Wang et al.*: [SELF-INSTRUCT: Aligning Language Models with Self-Generated Instructions](https://arxiv.org/pdf/2212.10560). [[Example](https://github.com/camel-ai/camel/blob/master/examples/datagen/self_instruct/self_instruct.py)]

## 📝 License

The source code is licensed under Apache 2.0.

## 🤝 Contributing to CAMEL 🐫
We appreciate your interest in contributing to our open-source initiative. We provide a document of [contributing guidelines](https://github.com/camel-ai/camel/blob/master/CONTRIBUTING.md) which outlines the steps for contributing to CAMEL. Please refer to this guide to ensure smooth collaboration and successful contributions. 🚀

## 📞 Community & Contact
For more information please contact camel-ai@eigent.ai



[docs-image]: https://img.shields.io/badge/Documentation-EB3ECC
[docs-url]: https://camel-ai.github.io/camel/index.html
[star-image]: https://img.shields.io/github/stars/camel-ai/camel?label=stars&logo=github&color=brightgreen
[star-url]: https://github.com/camel-ai/camel/stargazers
[package-license-image]: https://img.shields.io/badge/License-Apache_2.0-blue.svg
[package-license-url]: https://github.com/camel-ai/camel/blob/master/licenses/LICENSE

[colab-url]: https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing
[colab-image]: https://colab.research.google.com/assets/colab-badge.svg
[huggingface-url]: https://huggingface.co/camel-ai
[huggingface-image]: https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-CAMEL--AI-ffc107?color=ffc107&logoColor=white
[discord-url]: https://discord.camel-ai.org/
[discord-image]: https://img.shields.io/discord/1082486657678311454?logo=discord&labelColor=%20%235462eb&logoColor=%20%23f5f5f5&color=%20%235462eb
[wechat-url]: https://ghli.org/camel/wechat.png
[wechat-image]: https://img.shields.io/badge/WeChat-CamelAIOrg-brightgreen?logo=wechat&logoColor=white
[x-url]: https://x.com/CamelAIOrg
[x-image]: https://img.shields.io/twitter/follow/CamelAIOrg?style=social
[twitter-image]: https://img.shields.io/twitter/follow/CamelAIOrg?style=social&color=brightgreen&logo=twitter
[reddit-url]: https://www.reddit.com/r/CamelAI/
[reddit-image]: https://img.shields.io/reddit/subreddit-subscribers/CamelAI?style=plastic&logo=reddit&label=r%2FCAMEL&labelColor=white
