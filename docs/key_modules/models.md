# Models

## 1. Concept
The model is the brain of the intelligent agent, responsible for intelligent agent, processing all input and output data to execute tasks such as text analysis, image recognition, and complex reasoning. With customizable interfaces and multiple integration options, CAMEL AI enables rapid development with leading LLMs.  

> **Explore the Code:** Check out our [Colab Notebook](https://colab.research.google.com/drive/18hQLpte6WW2Ja3Yfj09NRiVY-6S2MFu7?usp=sharing) for a hands-on demonstration.


## 2. Supported Model Platforms in CAMEL

CAMEL supports a wide range of models, including [OpenAI’s GPT series](https://platform.openai.com/docs/models), [Meta’s Llama models](https://www.llama.com/), [DeepSeek's R1](https://www.deepseek.com/), and more. The table below lists all supported model platforms:

| Model Platform | Model Type(s) |
|---------------|--------------|
| **OpenAI** | gpt-4o, gpt-4o-mini, o1, o1-preview, o1-mini, o3-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| **Azure OpenAI** | gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| **Mistral AI** | mistral-large-latest, pixtral-12b-2409, ministral-8b-latest, ministral-3b-latest, open-mistral-nemo, codestral-latest, open-mistral-7b, open-mixtral-8x7b, open-mixtral-8x22b, open-codestral-mamba |
| **Anthropic** | claude-2.1, claude-2.0, claude-instant-1.2, claude-3-opus-latest, claude-3-sonnet-20240229, claude-3-haiku-20240307, claude-3-5-sonnet-latest, claude-3-5-haiku-latest |
| **Gemini** | gemini-1.5-flash, gemini-1.5-pro, gemini-exp-1114 |
| **Lingyiwanwu** | yi-lightning, yi-large, yi-medium, yi-large-turbo, yi-vision, yi-medium-200k, yi-spark, yi-large-rag, yi-large-fc |
| **Qwen** | qwq-32b-preview, qwen-max, qwen-plus, qwen-turbo, qwen-long, qwen-vl-max, qwen-vl-plus, qwen-math-plus, qwen-math-turbo, qwen-coder-turbo, qwen2.5-coder-32b-instruct, qwen2.5-72b-instruct, qwen2.5-32b-instruct, qwen2.5-14b-instruct |
| **DeepSeek** | deepseek-chat, deepseek-reasoner |
| **ZhipuAI** | glm-4v, glm-4, glm-3-turbo |
| **InternLM** | internlm3-latest, internlm3-8b-instruct, internlm2.5-latest, internlm2-pro-chat |
| **Reka** | reka-core, reka-flash, reka-edge |
| **GROQ** | llama-3.1-8b-instant, llama-3.3-70b-versatile, llama-3.3-70b-specdec, llama3-8b-8192, llama3-70b-8192, mixtral-8x7b-32768, gemma2-9b-it |
| **TOGETHER** | meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo, meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo, meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo, meta-llama/Llama-3.3-70B-Instruct-Turbo, mistralai/Mixtral-8x7B-Instruct-v0.1, mistralai/Mistral-7B-Instruct-v0.1 |
| **SAMBA** | Meta-Llama-3.1-8B-Instruct, Meta-Llama-3.1-70B-Instruct, Meta-Llama-3.1-405B-Instruct |
| **SGLANG** | meta-llama/Meta-Llama-3.1-8B-Instruct, meta-llama/Meta-Llama-3.1-70B-Instruct, meta-llama/Meta-Llama-3.1-405B-Instruct, meta-llama/Llama-3.2-1B-Instruct, mistralai/Mistral-Nemo-Instruct-2407, mistralai/Mistral-7B-Instruct-v0.3, Qwen/Qwen2.5-7B-Instruct, Qwen/Qwen2.5-32B-Instruct, Qwen/Qwen2.5-72B-Instruct |
| **NVIDIA** | nvidia/nemotron-4-340b-instruct, nvidia/nemotron-4-340b-reward, 01-ai/yi-large, mistralai/mistral-large, mistralai/mixtral-8x7b-instruct, meta/llama3-70b, meta/llama-3.1-8b-instruct, meta/llama-3.1-70b-instruct, meta/llama-3.1-405b-instruct, meta/llama-3.2-1b-instruct, meta/llama-3.2-3b-instruct, meta/llama-3.3-70b-instruct |
| **COHERE** | command-r-plus, command-r, command-light, command, command-nightly |


## 3. How to Use Models via API Calls

Easily integrate your chosen model with CAMEL AI using straightforward API calls. For example, to use the **gpt-4o-mini** model:

> If you want to use another model, you can simply change these three parameters: `model_platform`, `model_type`, `model_config_dict` .

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.agents import ChatAgent

# Define the model, here in this case we use gpt-4o-mini
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Define an assitant message
system_msg = "You are a helpful assistant."

# Initialize the agent
ChatAgent(system_msg, model=model)
```

> And if you want to use an OpenAI-compatible API, you can replace the `model` with the following code:

```python
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="a-string-representing-the-model-type",
    api_key=os.environ.get("OPENAI_COMPATIBILIY_API_KEY"),
    url=os.environ.get("OPENAI_COMPATIBILIY_API_BASE_URL"),
    model_config_dict={"temperature": 0.4, "max_tokens": 4096},
)
```

## 4. Using On-Device Open Source Models
CAMEL AI also supports local deployment of open-source LLMs. Choose the setup that suits your project:

### 4.1 Using Ollama to Set Llama 3 Locally

1. Download [Ollama](https://ollama.com/download).
2. After setting up Ollama, pick a model like Llama3 for your project:

```bash
ollama pull llama3
```

3. Create a `ModelFile` similar the one below in your project directory. (Optional)

```
FROM llama3

# Set parameters
PARAMETER temperature 0.8
PARAMETER stop Result

# Sets a custom system message to specify the behavior of the chat assistant
# Leaving it blank for now.

SYSTEM """ """
```

4. Create a script to get the base model (llama3) and create a custom model using the `ModelFile` above. Save this as a `.sh` file: (Optional)

```
#!/bin/zsh

# variables
model_name="llama3"
custom_model_name="camel-llama3"

#get the base model
ollama pull $model_name

#create the model file
ollama create $custom_model_name -f ./Llama3ModelFile
```

5. Navigate to the directory where the script and `ModelFile` are located and run the script. Enjoy your Llama3 model, enhanced by CAMEL's excellent agents.

```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llama3",
    url="http://localhost:11434/v1", # Optional
    model_config_dict={"temperature": 0.4},
)

agent_sys_msg = "You are a helpful assistant."

agent = ChatAgent(agent_sys_msg, model=ollama_model, token_limit=4096)

user_msg = "Say hi to CAMEL"

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
```

### 4.2 Using vLLM to Set Phi-3 Locally

Install [vLLM](https://docs.vllm.ai/en/latest/getting_started/installation.html) first.

After setting up vLLM, start an OpenAI compatible server for example by:

```
python -m vllm.entrypoints.openai.api_server --model microsoft/Phi-3-mini-4k-instruct --api-key vllm --dtype bfloat16
```

Create and run following script (more details please refer to this [example](https://github.com/camel-ai/camel/blob/master/examples/models/vllm_model_example.py)):

```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

vllm_model = ModelFactory.create(
    model_platform=ModelPlatformType.VLLM,
    model_type="microsoft/Phi-3-mini-4k-instruct",
    url="http://localhost:8000/v1", # Optional
    model_config_dict={"temperature": 0.0}, # Optional
)

agent_sys_msg = "You are a helpful assistant."

agent = ChatAgent(agent_sys_msg, model=vllm_model, token_limit=4096)

user_msg = "Say hi to CAMEL AI"

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
```

### 4.3 Using SGLang to Set meta-llama/Llama Locally

Install [SGLang](https://sgl-project.github.io/start/install.html) first.

Create and run following script (more details please refer to this [example](https://github.com/camel-ai/camel/blob/master/examples/models/sglang_model_example.py)):

```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

sglang_model = ModelFactory.create(
    model_platform=ModelPlatformType.SGLANG,
    model_type="meta-llama/Llama-3.2-1B-Instruct",
    model_config_dict={"temperature": 0.0},
    api_key="sglang",
)

agent_sys_msg = "You are a helpful assistant."

agent = ChatAgent(agent_sys_msg, model=sglang_model, token_limit=4096)

user_msg = "Say hi to CAMEL AI"

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
```

## 5 Model Speed and Performance
Performance is critical for interactive AI applications. CAMEL-AI benchmarks tokens processed per second across various models:

In [this notebook](../cookbooks/model_speed_comparison.ipynb), we compared several models, including OpenAI’s GPT-4O Mini, GPT-4O, O1 Preview, and SambaNova's Llama series, by measuring the number of tokens each model processes per second.

- OpenAI GPT-4O Mini: Fast and efficient.
- SambaNova’s Llama 405B: High capacity but slower response.
- Local Inference: SGLang reached a peak of 220.98 tokens per second, compared to vLLM’s 107.2 tokens per second.

![Model Speed Comparison: Chart comparing tokens per second for various AI models](https://i.postimg.cc/4xByytyZ/model-speed.png)


For local inference, we conducted a straightforward comparison locally between vLLM and SGLang. SGLang demonstrated superior performance, with `meta-llama/Llama-3.2-1B-Instruct` reaching a peak speed of 220.98 tokens per second, compared to vLLM, which capped at 107.2 tokens per second.

## 6. Next Steps
You've now learned how to integrate various models into CAMEL AI.

Next, check out our guide covering basics of creating and converting [messages with BaseMessage.](https://docs.camel-ai.org/key_modules/messages.html) 