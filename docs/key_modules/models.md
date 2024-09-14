# Models

## 1. Concept
The model is the brain of the intelligent agent, responsible for processing all input and output data. By calling different models, the agent can execute operations such as text analysis, image recognition, or complex reasoning according to task requirements. CAMEL offers a range of standard and customizable interfaces, as well as seamless integrations with various components, to facilitate the development of applications with Large Language Models (LLMs). In this part, we will introduce models currently supported by CAMEL and the working principles and interaction methods with models. All the codes are also available on colab notebook [here](https://colab.research.google.com/drive/18hQLpte6WW2Ja3Yfj09NRiVY-6S2MFu7?usp=sharing).


## 2. Supported Model Platforms

The following table lists currently supported model platforms by CAMEL.

| Model Platform | Representative Model| Multi-modality |
| ----- | ----- | ----- |
| OpenAI | gpt-4o | Y |
| Azure OpenAI | gpt-4o | Y |
| Mistral AI | mistral-large-2 | N |
| Anthropic | claude-3-5-sonnet-20240620 | Y |
| Gemini | gemini-1.5-pro | Y |
| ZhipuAI | glm-4v | Y |
| Reka | reka-core | Y |
| Nividia | nemotron-4-340b-reward | N |
| SambaNova| https://sambaverse.sambanova.ai/models | ----- |
| Groq | https://console.groq.com/docs/models | ----- |
| Ollama | https://ollama.com/library | ----- |
| vLLM | https://docs.vllm.ai/en/latest/models/supported_models.html | ----- |
| Together AI | https://docs.together.ai/docs/chat-models | ----- |
| LiteLLM | https://docs.litellm.ai/docs/providers | ----- |

## 3. Model calling template

Here is the example code to use a chosen model. To utilize a different model, you can simply change three parameters the define your model to be used: `model_platform`, `model_type`, `model_config_dict` .

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
system_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
)

# Initialize the agent
ChatAgent(system_msg, model=model)
```

## 4. Open Source LLMs
In the current landscape, for those seeking highly stable content generation, OpenAI’s gpt-4o-mini, gpt-4o are often recommended. However, the field is rich with many other outstanding open-source models that also yield commendable results. CAMEL can support developers to delve into integrating these open-source large language models (LLMs) to achieve project outputs based on unique input ideas.

While proprietary models like gpt-4o-mini and gpt-4o have set high standards for content generation, open-source alternatives offer viable solutions for experimentation and practical use. These models, supported by active communities and continuous improvements, provide flexibility and cost-effectiveness for developers and researchers.

### 4.1 Using Ollama to Set Llama 3 Locally

1. Download [Ollama](https://ollama.com/download).
2. After setting up Ollama, pull the Llama3 model by typing the following command into the terminal:

```bash
ollama pull llama3
```

3. Create a `ModelFile` similar the one below in your project directory.

```
FROM llama3

# Set parameters
PARAMETER temperature 0.8
PARAMETER stop Result

# Sets a custom system message to specify the behavior of the chat assistant
# Leaving it blank for now.

SYSTEM """ """
```

4. Create a script to get the base model (llama3) and create a custom model using the `ModelFile` above. Save this as a `.sh` file:

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
    url="http://localhost:8000/v1",
    model_config_dict={"temperature": 0.0},
    api_key="vllm",
)

assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)
agent = ChatAgent(assistant_sys_msg, model=vllm_model, token_limit=4096)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Say hi to CAMEL AI",
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
```

## 5. Conclusion
In conclusion, CAMEL empowers developers to explore and integrate these diverse models, unlocking new possibilities for innovative AI applications. The world of large language models offers a rich tapestry of options beyond just the well-known proprietary solutions. By guiding users through model selection, environment setup, and integration, CAMEL bridges the gap between cutting-edge AI research and practical implementation. Its hybrid approach, combining in-house implementations with third-party integrations, offers unparalleled flexibility and comprehensive support for LLM-based development. Don't just watch this transformation that is happening from the sidelines.

Dive into the CAMEL documentation, experiment with different models, and be part of shaping the future of AI. The era of truly flexible and powerful AI is here - are you ready to make your mark?
