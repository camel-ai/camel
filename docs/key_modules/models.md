# Models

## 1. Concept
The model is the brain of the intelligent agent, responsible for intelligent agent, processing all input and output data to execute tasks such as text analysis, image recognition, and complex reasoning. With customizable interfaces and multiple integration options, CAMEL AI enables rapid development with leading LLMs.  

> **Explore the Code:** Check out our [Colab Notebook](https://colab.research.google.com/drive/18hQLpte6WW2Ja3Yfj09NRiVY-6S2MFu7?usp=sharing) for a hands-on demonstration.


## 2. Supported Model Platforms in CAMEL

CAMEL supports a wide range of models, including [OpenAI’s GPT series](https://platform.openai.com/docs/models), [Meta’s Llama models](https://www.llama.com/), [DeepSeek models](https://www.deepseek.com/) (R1 and other variants), and more. The table below lists all supported model platforms:

| Model Platform | Model Type(s) |
|---------------|--------------|
| **OpenAI** | gpt-4.5-preview, gpt-4o, gpt-4o-mini, o1, o1-preview, o1-mini, o3-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| **Azure OpenAI** | gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| **Mistral AI** | mistral-large-latest, pixtral-12b-2409, ministral-8b-latest, ministral-3b-latest, open-mistral-nemo, codestral-latest, open-mistral-7b, open-mixtral-8x7b, open-mixtral-8x22b, open-codestral-mamba |
| **Moonshot** | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k |
| **Anthropic** | claude-2.1, claude-2.0, claude-instant-1.2, claude-3-opus-latest, claude-3-sonnet-20240229, claude-3-haiku-20240307, claude-3-5-sonnet-latest, claude-3-5-haiku-latest |
| **Gemini** | gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash, gemini-exp-1114 |
| **Lingyiwanwu** | yi-lightning, yi-large, yi-medium, yi-large-turbo, yi-vision, yi-medium-200k, yi-spark, yi-large-rag, yi-large-fc |
| **Qwen** | qwq-32b-preview, qwen-max, qwen-plus, qwen-turbo, qwen-long, qwen-vl-max, qwen-vl-plus, qwen-math-plus, qwen-math-turbo, qwen-coder-turbo, qwen2.5-coder-32b-instruct, qwen2.5-72b-instruct, qwen2.5-32b-instruct, qwen2.5-14b-instruct |
| **DeepSeek** | deepseek-chat, deepseek-reasoner |
| **ZhipuAI** | glm-4, glm-4v, glm-4v-flash, glm-4v-plus-0111, glm-4-plus, glm-4-air, glm-4-air-0111, glm-4-airx, glm-4-long, glm-4-flashx, glm-zero-preview, glm-4-flash, glm-3-turbo |
| **InternLM** | internlm3-latest, internlm3-8b-instruct, internlm2.5-latest, internlm2-pro-chat |
| **Reka** | reka-core, reka-flash, reka-edge |
| **COHERE** | command-r-plus, command-r, command-light, command, command-nightly |
| **GROQ** | [supported models](https://console.groq.com/docs/models) |
| **TOGETHER AI** | [supported models](https://docs.together.ai/docs/chat-models) |
| **SambaNova** | [supported models](https://docs.sambanova.ai/cloud/docs/get-started/supported-models) |
| **Ollama** |  [supported models](https://ollama.com/library) |
| **OpenRouter** | [supported models](https://openrouter.ai/models) |
| **PPIO** | [supported models](https://ppinfra.com/model-api/product/llm-api?utm_source=github_owl) |
| **LiteLLM** | [supported models](https://docs.litellm.ai/docs/providers) |
| **vLLM** |  [supported models](https://docs.vllm.ai/en/latest/models/supported_models.html) |
| **SGLANG** | [supported models](https://sgl-project.github.io/references/supported_models.html) |
| **NVIDIA** | [supported models](https://docs.api.nvidia.com/nim/reference/llm-apis) |
| **AIML** | [supported models](https://docs.aimlapi.com/api-overview/model-database/text-models) |
| **ModelScope** | [supported models](https://www.modelscope.cn/docs/model-service/API-Inference/intro) |

## 3. How to Use Models via API Calls

Easily integrate your chosen model with CAMEL AI using straightforward API calls. For example, to use the **gpt-4o-mini** model:

> If you want to use another model, you can simply change these three parameters: `model_platform`, `model_type`, `model_config_dict` .
| Model Platform | Available Models| Multi-modality |
| ----- | ----- | ----- |
| OpenAI | gpt-4o | Y |
| OpenAI | gpt-4o-mini | Y |
| OpenAI | o1 | Y |
| OpenAI | o1-preview | N |
| OpenAI | o1-mini | N |
| OpenAI | gpt-4-turbo | Y |
| OpenAI | gpt-4 | Y |
| OpenAI | gpt-3.5-turbo | N |
| Azure OpenAI | gpt-4o | Y |
| Azure OpenAI | gpt-4-turbo | Y |
| Azure OpenAI | gpt-4 | Y |
| Azure OpenAI | gpt-3.5-turbo | Y |
| OpenAI Compatible | Depends on the provider | ----- |
| Mistral AI | mistral-large-2 | N |
| Mistral AI | pixtral-12b-2409 | Y |
| Mistral AI | ministral-8b-latest | N |
| Mistral AI | ministral-3b-latest | N |
| Mistral AI | open-mistral-nemo | N |
| Mistral AI | codestral | N |
| Mistral AI | open-mistral-7b | N |
| Mistral AI | open-mixtral-8x7b | N |
| Mistral AI | open-mixtral-8x22b | N |
| Mistral AI | open-codestral-mamba | N |
| Anthropic | claude-3-5-sonnet-latest | Y |
| Anthropic | claude-3-5-haiku-latest | N |
| Anthropic | claude-3-haiku-20240307 | Y |
| Anthropic | claude-3-sonnet-20240229 | Y |
| Anthropic | claude-3-opus-latest | Y |
| Anthropic | claude-2.0 | N |
| Gemini | gemini-1.5-pro | Y |
| Gemini | gemini-1.5-flash | Y |
| Gemini | gemini-exp-1114 | Y |
| Lingyiwanwu | yi-lightning | N |
| Lingyiwanwu | yi-large | N |
| Lingyiwanwu | yi-medium | N |
| Lingyiwanwu | yi-large-turbo | N |
| Lingyiwanwu | yi-vision | Y |
| Lingyiwanwu | yi-medium-200k | N |
| Lingyiwanwu | yi-spark | N |
| Lingyiwanwu | yi-large-rag | N |
| Lingyiwanwu | yi-large-fc | N |
| Qwen | qwq-32b-preview | N |
| Qwen | qwen-max | N |
| Qwen | qwen-plus | N |
| Qwen | qwen-turbo | N |
| Qwen | qwen-long | N |
| Qwen | qwen-vl-max | Y |
| Qwen | qwen-vl-plus | Y |
| Qwen | qwen-math-plus | N |
| Qwen | qwen-math-turbo | N |
| Qwen | qwen-coder-turbo | N |
| Qwen | qwen2.5-coder-32b-instruct | N |
| Qwen | qwen2.5-72b-instruct | N |
| Qwen | qwen2.5-32b-instruct | N |
| Qwen | qwen2.5-14b-instruct | N |
| DeepSeek | deepseek-chat | N |
| DeepSeek | deepseek-reasoner | N |
| ZhipuAI | glm-4v | Y |
| ZhipuAI | glm-4 | N |
| ZhipuAI | glm-3-turbo | N |
| InternLM | internlm3-latest | N |
| InternLM | internlm3-8b-instruct | N |
| InternLM | internlm2.5-latest	| N |
| InternLM | internlm2-pro-chat	| N |
| Reka | reka-core | Y |
| Reka | reka-flash | Y |
| Reka | reka-edge | Y |
| Nvidia | https://docs.api.nvidia.com/nim/reference/llm-apis | ----- |
| SambaNova| https://community.sambanova.ai/t/supported-models/193 | ----- |
| Groq | https://console.groq.com/docs/models | ----- |
| Ollama | https://ollama.com/library | ----- |
| vLLM | https://docs.vllm.ai/en/latest/models/supported_models.html | ----- |
| Together AI | https://docs.together.ai/docs/chat-models | ----- |
| LiteLLM | https://docs.litellm.ai/docs/providers | ----- |
| SGLang | https://sgl-project.github.io/references/supported_models.html | ----- |
| AWSBedrock | https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html | ----- |
## 3. Using Models by API calling

Here is an example code to use a specific model (gpt-4o-mini). If you want to use another model, you can simply change these three parameters: `model_platform`, `model_type`, `model_config_dict` .

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

# Define an assistant message
system_msg = "You are a helpful assistant."

# Initialize the agent
ChatAgent(system_msg, model=model)
```

> And if you want to use an OpenAI-compatible API, you can replace the `model` with the following code:

```python
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="a-string-representing-the-model-type",
    api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY"),
    url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"),
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

**Key Insights:** Smaller models like SambaNova’s Llama 8B and OpenAI's GPT-4O Mini typically offer faster responses. Larger models like SambaNova’s Llama 405B, while more powerful, tend to generate output more slowly due to their complexity. OpenAI models demonstrate relatively consistent performance, while SambaNova's Llama 8B significantly outperforms others in speed. The chart below illustrates the tokens per second achieved by each model during our tests:

![Model Speed Comparison: Chart comparing tokens per second for various AI models](https://i.postimg.cc/4xByytyZ/model-speed.png)


For local inference, we conducted a straightforward comparison locally between vLLM and SGLang. SGLang demonstrated superior performance, with `meta-llama/Llama-3.2-1B-Instruct` reaching a peak speed of 220.98 tokens per second, compared to vLLM, which capped at 107.2 tokens per second.

## 6. Next Steps
You've now learned how to integrate various models into CAMEL AI.

Next, check out our guide covering basics of creating and converting [messages with BaseMessage.](https://docs.camel-ai.org/key_modules/messages.html) 
