[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing) 
[![slack](https://img.shields.io/badge/Slack-CAMEL--AI-green)](https://join.slack.com/t/camel-kwr1314/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA)
[![Discord](https://img.shields.io/badge/Discord-CAMEL--AI-green)](https://discord.gg/CNcNpquyDc)
<a href="https://huggingface.co/camel-ai"><img src="https://huggingface.co/datasets/huggingface/brand-assets/resolve/main/hf-logo-with-title.png" alt="Hugging Face" width="100"/></a> 
# CAMEL: Communicative Agents for “Mind” Exploration of Large Scale Language Model Society

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
  <img src='./misc/logo.png' width=800>
</p>

## Overview
The rapid advancement of conversational and chat-based language models has led to remarkable progress in complex task-solving. However, their success heavily relies on human input to guide the conversation, which can be challenging and time-consuming. This paper explores the potential of building scalable techniques to facilitate autonomous cooperation among communicative agents and provide insight into their "cognitive" processes. To address the challenges of achieving autonomous cooperation, we propose a novel communicative agent framework named *role-playing*. Our approach involves using *inception prompting* to guide chat agents toward task completion while maintaining consistency with human intentions. We showcase how role-playing can be used to generate conversational data for studying the behaviors and capabilities of chat agents, providing a valuable resource for investigating conversational language models. Our contributions include introducing a novel communicative agent framework, offering a scalable approach for studying the cooperative behaviors and capabilities of multi-agent systems, and open-sourcing our library to support research on communicative agents and beyond. The GitHub repository of this project is made publicly available on: [https://github.com/camel-ai/camel](https://github.com/camel-ai/camel).

## Community
🐫 CAMEL is an open-source library designed for the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we implement and support various types of agents, tasks, prompts, models, and simulated environments. Join us ([slack](https://join.slack.com/t/camel-kwr1314/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA), [discord](https://discord.gg/CNcNpquyDc)) in pushing the boundaries of simulating AI Society with CAMEL.

## Try it yourself
We provide a [![Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1AzP33O8rnMW__7ocWJhVBXjKziJXPtim?usp=sharing) demo showcasing a conversation between two ChatGPT agents playing roles as a python programmer and a stock trader collaborating on developing a trading bot for stock market.

<p align="center">
  <img src='./misc/framework.png' width=800>
</p>

## Documentation

[CAMEL package documentation pages](https://camel-ai.github.io/camel/)

## Installation
Install `CAMEL` from source with conda:
```
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

# Install pre-commmit within camel env (only needed for opening pull requests)
pip install pre-commit
pre-commit install
```
## Example
You can find a list of tasks for different set of assistant and user role pairs [here](https://drive.google.com/file/d/194PPaSTBR07m-PzjS-Ty6KlPLdFIPQDd/view?usp=share_link)

Run the `role_playing.py` script

First, you need to add your OpenAI API key to system environment variables. The method to do this depends on your operating system and the shell you're using.

**For Bash shell (Linux, macOS, Git Bash on Windows):**

```bash
# Export your OpenAI API key
export OPENAI_API_KEY=<insert your OpenAI API key>
```

**For Windows Command Prompt:**

```cmd
REM export your OpenAI API key
set OPENAI_API_KEY=<insert your OpenAI API key>
```

**For Windows PowerShell:**

```powershell
# Export your OpenAI API key
$env:OPENAI_API_KEY="<insert your OpenAI API key>"
```

Replace `<insert your OpenAI API key>` with your actual OpenAI API key in each case. Make sure there are no spaces around the `=` sign.

After setting the OpenAI API key, you can run the script:

```bash
# You can change the role pair and initial prompt in role_playing.py
python examples/ai_society/role_playing.py
```

Please note that the environment variable is session-specific. If you open a new terminal window or tab, you will need to set the API key again in that new session.

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


## News
- Released AI Society and Code dataset (April 2, 2023)
- Initial release of `CAMEL` python library (March 21, 2023)

## Citation
```
@misc{li2023camel,
    title={CAMEL: Communicative Agents for "Mind" Exploration of Large Scale Language Model Society},
    author={Guohao Li and Hasan Abed Al Kader Hammoud and Hani Itani and Dmitrii Khizbullin and Bernard Ghanem},
    year={2023},
    eprint={2303.17760},
    archivePrefix={arXiv},
    primaryClass={cs.AI}
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
