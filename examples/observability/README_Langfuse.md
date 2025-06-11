# Langfuse Usage Guide

Langfuse is an open-source LLM engineering platform that provides tracing, evaluation, prompt management, and metrics analysis. This guide covers how to use Langfuse with the CAMEL project and how to start a Docker self-hosted service.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Docker Self-Hosted Deployment](#docker-self-hosted-deployment)
- [Related Links](#related-links)

## Quick Start

### 1. Install Dependencies

```bash
pip install 'camel-ai[all]'
```

### 2. Environment Variables Configuration

Before using Langfuse, set the following environment variables:

```bash
# Enable Langfuse tracing
export LANGFUSE_ENABLED="true"

# Langfuse service configuration (optional, if using cloud service)
export LANGFUSE_PUBLIC_KEY="pk-lf-your-public-key"
export LANGFUSE_SECRET_KEY="sk-lf-your-secret-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"  # or your self-hosted address

# Debug mode (optional)
export LANGFUSE_DEBUG="false"
```

### 3. Basic Usage Example

```python
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1_MINI,
)

# Define system message
sys_msg = "You are a helpful AI assistant, skilled at answering questions."

# Create agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# User message
user_msg = "Calculate the square root after adding 222991 and 1111"

# Execute conversation (automatically traced)
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
```

## Environment Configuration

### Environment Variables Description

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_ENABLED` | Yes | `false` | Enable/disable Langfuse tracing |
| `LANGFUSE_PUBLIC_KEY` | No* | - | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | No* | - | Langfuse secret key |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Langfuse service address |
| `LANGFUSE_DEBUG` | No | `false` | Enable debug mode |

*Note: Required when using cloud service or authenticated self-hosted service

## Docker Self-Hosted Deployment

If you want to self-host the Langfuse service, you can quickly deploy it using Docker Compose.

### Requirements

- git
- docker & docker compose -> Use Docker Desktop on Mac or Windows

### Clone Langfuse Repository

Get a copy of the latest Langfuse repository:

```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
```

### Start the Application

Update the secrets in the docker-compose.yml and then run the langfuse docker compose using:

```bash
docker compose up
```

Watch the containers being started and the logs flowing in. After about 2-3 minutes, the langfuse-web-1 container should log "Ready". At this point you can proceed to the next step.

### Done

And you are ready to go! Open `http://localhost:3000` in your browser to access the Langfuse UI.

## Related Links

- [Langfuse Official Documentation](https://langfuse.com/docs)
- [Langfuse GitHub Repository](https://github.com/langfuse/langfuse)
- [Docker Compose Deployment Guide](https://langfuse.com/self-hosting/docker-compose)
