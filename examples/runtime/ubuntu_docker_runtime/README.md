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
├── test_camel_docker.py
├── test_ubuntu_docker.py
└── test_docker_roleplaying.py
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

Before running the role-playing test, you need to set up your ModelScope API key in `test_docker_roleplaying.py`:

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
python test_ubuntu_docker.py
```

This will:
- Use the Docker container to run a role-playing scenario
- Initialize the Qwen model for AI interactions
- Execute a sample task with AI agents communication

## Expected Output

For `test_camel_docker.py`:
```
Waiting for runtime to start...
Docker environment test completed successfully.
```

For `test_ubuntu_docker.py`:
```
AI Assistant sys message: [System message content]
AI User sys message: [System message content]
[Role-playing interaction content]
```

## Troubleshooting

If you encounter issues:

1. Docker Related:
```bash
# Check Docker status
docker ps -a

# Check container logs
docker logs <container_id>

# Clean up and rebuild
./manage_camel_docker.sh clean
./manage_camel_docker.sh build
```

2. API Key Issues:
- Verify your ModelScope API key is valid
- Check network connectivity to ModelScope API
- Ensure the API key is correctly set in `test_docker_roleplaying.py`

3. Common Problems:
- If the script hangs: Check Docker logs and network connectivity
- If model initialization fails: Verify API key and internet access
- If container fails to start: Check Docker daemon status and port availability

## Additional Commands

- Stop all containers: `./manage_camel_docker.sh stop`
- Remove all containers: `./manage_camel_docker.sh clean`
- Rebuild image: `./manage_camel_docker.sh rebuild`

## Notes

- The container uses port 8000 by default
- Python path is set to `/usr/bin/python3`
- The Qwen model requires a valid ModelScope API key
- Role-playing functionality requires successful Docker environment setup
- Make sure to have stable internet connection for model API calls 