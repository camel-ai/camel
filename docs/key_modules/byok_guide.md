---
title: "Bring Your Own Key (BYOK) Guide"
description: "Configure and use your own API keys with CAMEL-AI to access various LLM providers"
icon: key
---

## What is BYOK?

**Bring Your Own Key (BYOK)** allows you to use your personal API keys from various LLM providers (OpenAI, Anthropic, Google, etc.) with CAMEL-AI. This gives you:

- **Full Control**: Use your own billing accounts and usage quotas
- **Flexibility**: Switch between providers without changing your code structure
- **Security**: Your API keys stay under your control

## OpenAI API Key Configuration

### Step 1: Obtain Your API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy and securely store your API key

### Step 2: Configure Your Environment

Choose one of the following methods:

**Option A: Environment Variable (Recommended)**

```bash
# macOS/Linux
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc

# Windows PowerShell
setx OPENAI_API_KEY "sk-your-api-key-here" /M
```

**Option B: .env File**

Create a `.env` file in your project root:

```dotenv
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE_URL=https://api.openai.com/v1  # Optional custom endpoint
```

**Option C: Direct Parameter**

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    api_key="sk-your-api-key-here",  # Pass directly
)
```

### Step 3: Verify Your Configuration

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent

# Create model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
)

# Test with a simple agent
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model
)

response = agent.step("Hello!")
print(response.msg.content)
```

## Supported Model Configuration Fields

### ChatGPTConfig (OpenAI)

| Field | Type | Description |
|-------|------|-------------|
| `temperature` | float (0-2) | Controls randomness. Higher = more creative |
| `top_p` | float (0-1) | Nucleus sampling threshold |
| `max_tokens` | int | Maximum response length |
| `stop` | str/list | Stop sequences (up to 4) |
| `presence_penalty` | float (-2 to 2) | Penalize new topics |
| `frequency_penalty` | float (-2 to 2) | Penalize repetition |
| `response_format` | dict | Output format (e.g., JSON mode) |
| `tool_choice` | str/dict | Tool calling behavior |
| `reasoning_effort` | str | For o1/o3 models: "low", "medium", "high" |
| `extra_headers` | dict | Custom HTTP headers |

### ModelFactory.create() Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_platform` | ModelPlatformType/str | Provider (e.g., OPENAI, ANTHROPIC) |
| `model_type` | ModelType/str | Model name (e.g., GPT_4O_MINI) |
| `model_config_dict` | dict | Configuration parameters |
| `api_key` | str | API key (optional if set in env) |
| `url` | str | Custom API endpoint |
| `timeout` | float | Request timeout in seconds (default: 180) |
| `max_retries` | int | Retry attempts (default: 3) |

## Common Errors and Solutions

### Missing API Key

**Error:**
```
ValueError: Missing or empty required API keys in environment variables: OPENAI_API_KEY.
You can obtain the API key from https://platform.openai.com/docs/overview
```

**Solution:** Set your API key using one of the methods in Step 2.

### Invalid API Key

**Error:**
```
openai.AuthenticationError: Incorrect API key provided
```

**Solution:** Verify your API key is correct and hasn't expired. Generate a new key if needed.

### Invalid Model Name

**Error:**
```
openai.NotFoundError: The model 'invalid-model' does not exist
```

**Solution:** Use a valid model name from the ModelType enum or check the provider's documentation for available models.

### Unknown Model Platform

**Error:**
```
ValueError: Unknown model platform: invalid-platform
```

**Solution:** Use a valid ModelPlatformType enum value (e.g., `ModelPlatformType.OPENAI`).

### Rate Limit Exceeded

**Error:**
```
openai.RateLimitError: Rate limit reached for requests
```

**Solution:** Reduce request frequency or upgrade your API plan.

### Unsupported Parameters for Reasoning Models

**Warning:** Some parameters are not supported for o1/o3 reasoning models:
- `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`
- `logprobs`, `top_logprobs`, `logit_bias`

These will be automatically filtered when using reasoning models.

## Supported BYOK Providers

### Direct Integrations

| Provider | Environment Variable | API Documentation |
|----------|---------------------|-------------------|
| **OpenAI** | `OPENAI_API_KEY` | [OpenAI API Docs](https://platform.openai.com/docs/overview) |
| **Anthropic** | `ANTHROPIC_API_KEY` | [Anthropic API Docs](https://docs.anthropic.com/en/api/getting-started) |
| **Google Gemini** | `GEMINI_API_KEY` | [Gemini API Docs](https://ai.google.dev/gemini-api/docs) |
| **Mistral AI** | `MISTRAL_API_KEY` | [Mistral API Docs](https://docs.mistral.ai/) |
| **DeepSeek** | `DEEPSEEK_API_KEY` | [DeepSeek API Docs](https://platform.deepseek.com/api-docs) |
| **Cohere** | `COHERE_API_KEY` | [Cohere API Docs](https://docs.cohere.com/) |
| **Qwen** | `QWEN_API_KEY` | [Qwen API Docs](https://help.aliyun.com/zh/model-studio/developer-reference/api-reference) |
| **Moonshot (Kimi)** | `MOONSHOT_API_KEY` | [Moonshot API Docs](https://platform.moonshot.cn/docs/) |
| **ZhipuAI (GLM)** | `ZHIPUAI_API_KEY` | [ZhipuAI API Docs](https://open.bigmodel.cn/dev/api) |
| **Yi (Lingyiwanwu)** | `YI_API_KEY` | [Yi API Docs](https://platform.lingyiwanwu.com/docs) |
| **Reka** | `REKA_API_KEY` | [Reka API Docs](https://docs.reka.ai/quick-start) |
| **InternLM** | `INTERNLM_API_KEY` | [InternLM API Docs](https://internlm.intern-ai.org.cn/api/document) |
| **xAI (Grok)** | `XAI_API_KEY` | [xAI API Docs](https://docs.x.ai/api) |

### API & Connector Platforms

| Provider | Environment Variable | API Documentation |
|----------|---------------------|-------------------|
| **Azure OpenAI** | `AZURE_OPENAI_API_KEY` | [Azure OpenAI Docs](https://learn.microsoft.com/en-us/azure/ai-services/openai/) |
| **AWS Bedrock** | AWS credentials | [Bedrock Docs](https://docs.aws.amazon.com/bedrock/) |
| **Groq** | `GROQ_API_KEY` | [Groq API Docs](https://console.groq.com/docs/quickstart) |
| **Together AI** | `TOGETHER_API_KEY` | [Together Docs](https://docs.together.ai/docs/quickstart) |
| **SambaNova** | `SAMBA_API_KEY` | [SambaNova Docs](https://docs.sambanova.ai/) |
| **NVIDIA NIM** | `NVIDIA_API_KEY` | [NVIDIA NIM Docs](https://docs.api.nvidia.com/nim/reference/llm-apis) |
| **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter Docs](https://openrouter.ai/docs) |
| **CometAPI** | `COMETAPI_KEY` | [CometAPI Docs](https://api.cometapi.com/docs) |
| **Nebius** | `NEBIUS_API_KEY` | [Nebius Docs](https://nebius.com/docs/) |
| **AIML API** | `AIML_API_KEY` | [AIML Docs](https://docs.aimlapi.com/) |
| **SiliconFlow** | `SILICONFLOW_API_KEY` | [SiliconFlow Docs](https://docs.siliconflow.cn/) |
| **Novita** | `NOVITA_API_KEY` | [Novita Docs](https://novita.ai/docs) |
| **ModelScope** | `MODELSCOPE_API_KEY` | [ModelScope Docs](https://www.modelscope.cn/docs/model-service/API-Inference/intro) |
| **IBM WatsonX** | `WATSONX_API_KEY` | [WatsonX Docs](https://cloud.ibm.com/apidocs/watsonx-ai) |
| **Qianfan (ERNIE)** | `QIANFAN_ACCESS_KEY` | [Qianfan Docs](https://cloud.baidu.com/doc/WENXINWORKSHOP/) |
| **Volcano Engine** | `VOLCANO_API_KEY` | [Volcano Docs](https://www.volcengine.com/docs/82379) |
| **Crynux** | `CRYNUX_API_KEY` | [Crynux Docs](https://docs.crynux.ai/) |
| **AihubMix** | `AIHUBMIX_API_KEY` | [AihubMix Docs](https://doc.aihubmix.com/) |
| **MiniMax** | `MINIMAX_API_KEY` | [MiniMax Docs](https://platform.minimaxi.com/document/Guides) |
| **Cerebras** | `CEREBRAS_API_KEY` | [Cerebras Docs](https://inference-docs.cerebras.ai/) |
| **AMD** | `AMD_API_KEY` | [AMD LLM API](https://llm-api.amd.com/) |
| **PPIO** | `PPIO_API_KEY` | [PPIO Docs](https://ppioai.com/docs) |
| **NetMind** | `NETMIND_API_KEY` | [NetMind Docs](https://www.netmind.ai/docs) |

### Local/Self-Hosted Platforms

| Platform | Documentation |
|----------|---------------|
| **Ollama** | [Ollama Docs](https://ollama.com/library) |
| **vLLM** | [vLLM Docs](https://docs.vllm.ai/en/latest/) |
| **SGLang** | [SGLang Docs](https://docs.sglang.ai/) |
| **LMStudio** | [LMStudio Docs](https://lmstudio.ai/docs/) |
| **LiteLLM** | [LiteLLM Docs](https://docs.litellm.ai/docs/) |
| **Function Gemma** | Local Ollama model for function calling |
| **OpenAI Compatible** | Any OpenAI-compatible API endpoint |

## Quick Reference: Model Platform Types

```python
from camel.types import ModelPlatformType

# Direct providers
ModelPlatformType.OPENAI
ModelPlatformType.ANTHROPIC
ModelPlatformType.GEMINI
ModelPlatformType.MISTRAL
ModelPlatformType.DEEPSEEK
ModelPlatformType.COHERE
ModelPlatformType.QWEN
ModelPlatformType.MOONSHOT
ModelPlatformType.ZHIPU
ModelPlatformType.YI
ModelPlatformType.REKA
ModelPlatformType.INTERNLM

# API platforms
ModelPlatformType.AZURE
ModelPlatformType.AWS_BEDROCK
ModelPlatformType.GROQ
ModelPlatformType.TOGETHER
ModelPlatformType.SAMBA
ModelPlatformType.NVIDIA
ModelPlatformType.OPENROUTER
ModelPlatformType.COMETAPI
ModelPlatformType.NEBIUS
ModelPlatformType.AIML
ModelPlatformType.SILICONFLOW
ModelPlatformType.NOVITA
ModelPlatformType.MODELSCOPE
ModelPlatformType.WATSONX
ModelPlatformType.QIANFAN
ModelPlatformType.VOLCANO
ModelPlatformType.CRYNUX
ModelPlatformType.AIHUBMIX
ModelPlatformType.PPIO
ModelPlatformType.NETMIND
ModelPlatformType.CEREBRAS
ModelPlatformType.MINIMAX

# Local/Self-hosted
ModelPlatformType.OLLAMA
ModelPlatformType.VLLM
ModelPlatformType.SGLANG
ModelPlatformType.LMSTUDIO
ModelPlatformType.LITELLM
ModelPlatformType.OPENAI_COMPATIBLE_MODEL
```
