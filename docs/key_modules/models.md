The model is the brain of the intelligent agent, responsible for processing all input and output data. By calling different models, the agent can execute operations such as text analysis, image recognition, or complex reasoning according to task requirements. In this part, we will introduce models currently supported by CAMEL and the working principles and interaction methods of the model.

CAMEL offers a range of standard and customizable interfaces, as well as seamless integrations with various components, to facilitate the development of applications with Large Language Models (LLMs).

## Supported Model Platforms

The following table lists currently supported model platforms by CAMEL.

| Model Platform | Representative Model| Multi-modality |
| ----- | ----- | ----- |
| OpenAI | gpt-4o | Y |
| OpenAI | gpt-3.5-turbo | N |
| Anthropic | claude-3-5-sonnet-20240620 | Y |
| Gemini | gemini-1.5-pro | Y |
| ZhipuAI | glm-4v | Y |
| Nividia | nvidia/nemotron-4-340b-reward | N |
| Ollama | https://ollama.com/library | ----- |
| HuggingFace | https://huggingface.co/models | ----- |
| LiteLLM | https://docs.litellm.ai/docs/providers | ----- |

## Model calling template

Here is the example code to use a chosen model. To utilize a different model, you can simply change three parameters the define your model to be used: `model_platform`, `model_type`, `model_config_dict` .

```
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.message import BaseMessage

# Define the model, here in this case we use GPT3.5
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
    model_config_dict=ChatGPTConfig().__dict__,
)

# Define an assitant message
system_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
)

# Initialize the agent
ChatAgent(system_msg, model=model)
```

## Open source LLMs
In the current landscape, for those seeking highly stable content generation, OpenAI's GPT-3.5 turbo,  GPT-4o are often recommended. However, the field is rich with many other outstanding open-source models that also yield commendable results. CAMEL can support developers to delve into integrating these open-source large language models (LLMs) to achieve project outputs based on unique input ideas.

While proprietary models like GPT-3.5 turbo and GPT-4 have set high standards for content generation, open-source alternatives offer viable solutions for experimentation and practical use. These models, supported by active communities and continuous improvements, provide flexibility and cost-effectiveness for developers and researchers.

You can find the in-detail code tutorial of [how to connect to LLMs](https://www.notion.so/User-Service-Agent-Discord-auto-posting-to-be-confirmed-by-Backend-team-006ee7e719a5448faa0f5987d17273e9?pvs=21), we will walk you through the process of:

1. **Selecting an Open Source LLM**: Understand the strengths and capabilities of various models available in the open-source community. 
2. **Setting Up the Environment**: Learn how to set up your development environment to integrate these models. This includes installing necessary libraries, configuring runtime environments, and ensuring compatibility with your project requirements.
3. **Model Integration**: Step-by-step guidance on integrating your chosen LLM into your development workflow. We will cover API configurations, and leveraging pre-trained weights to maximize model performance for tasks.

While CAMEL implements some of models in-house, others are integrated through third-party providers. This hybrid approach enables CAMEL to provide a comprehensive and flexible toolkit for building with LLMs.


## Use your local models with Ollama (ex. set up Llama 3 locally)

1. Download [Ollama](https://ollama.com/download).
2. After setting up Ollama, pull the Llama3 model by typing the following command into the terminal:
   ```
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
    ```
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

## Use your local models with FastChat

Currently, we are using FastChat as our local model serving backend framework. Before you have a LLM launched on your local, you need to have FastChat installed.
```
pip install fschat
```

To launch the model, please run the following commands in three separate terminals. Here we pick llama-2 as an example. Please note the model-path could be a huggingface style model string (in the example below, it is `meta-llama/Llama-2-7b-chat-hf`, just like how you use their .from_pretrained() method!) or a simply a absolute or relative path. 
```
# Launch the controller
python -m fastchat.serve.controller

# Launch the model worker(s)
python3 -m fastchat.serve.model_worker --model-path meta-llama/Llama-2-7b-chat-hf

# Launch the RESTful API server
python3 -m fastchat.serve.openai_api_server --host localhost --port 8000
```

After you have the model successfully launched, you need to specify the following values in `OpenSourceConfig`  and pass it as one of the agent key word arguments when initializing a role play session.
```
from camel.configs import ChatGPTConfig, OpenSourceConfig

agent_kwargs = {
        role: dict(
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENSOURCE,
                model_type=ModelType.LLAMA_2,
                model_config_dict=OpenSourceConfig(
                    model_path="meta-llama/Llama-2-7b-chat-hf",
                    server_url="http://localhost:8000/v1",
                    api_params=ChatGPTConfig(temperature=0),
                ).__dict__,
            ),
    )
    for role in ["assistant", "user", "task-specify"]
}

role_play_session = RolePlaying(
    assistant_role_name="Python Programmer",
    assistant_agent_kwargs=agent_kwargs["assistant"],
    user_role_name="Stock Trader",
    user_agent_kwargs=agent_kwargs["user"],
    task_prompt=task_prompt,
    with_task_specify=True,
    task_specify_agent_kwargs=agent_kwargs["task-specify"],
)
```
