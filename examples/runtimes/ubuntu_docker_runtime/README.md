# Ubuntu Docker Runtime Example

This example demonstrates how to use the CAMEL framework with Docker runtime in an Ubuntu environment, including role-playing capabilities with the Qwen model.

## Prerequisites

- Docker installed and running
- Python 3.10 or later
- CAMEL package installed
- ModelScope API key for Qwen model access

## Directory Structure

```
ubuntu_docker_runtime/
├── README.md
├── manage_camel_docker.sh
├── Dockerfile
└── ubuntu_docker_example.py
```

## Setup and Running

### 1. Docker Environment Setup

First, build and manage the Docker image:

```bash
cd camel/examples/runtime/ubuntu_docker_runtime
chmod +x manage_camel_docker.sh
./manage_camel_docker.sh build
```

Verify the image was created:
```bash
docker images | grep my-camel
```
You should see `my-camel:latest` in the list.

### 2. Test Docker Environment

Run the basic test script to verify the Docker environment:
```bash
python test_camel_docker.py
```

This test will:
- Start a Docker container with the CAMEL runtime
- Initialize the API server
- Run basic operations to verify functionality

### 3. Configure ModelScope API Key

Before running the role-playing test, you need to set up your ModelScope API key in `docker_roleplaying.py`:

```python
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="Qwen/Qwen2.5-72B-Instruct",
    url='https://api-inference.modelscope.cn/v1/',
    api_key="YOUR_MODELSCOPE_API_KEY_HERE",  # Replace with your API key
)
```

### 4. Run Role-Playing Test

After setting up the API key, run the role-playing test:
```bash
python ubuntu_docker_example.py
```

This will:
- Use the Docker container to run a role-playing scenario
- Initialize the Qwen model for AI interactions
- Execute a sample task with AI agents communication