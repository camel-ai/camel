# Install with Docker Compose

## Prerequisites
- Docker：https://docs.docker.com/engine/install/
- Docker Compose：https://docs.docker.com/compose/install/

## Install
```bash
git clone https://github.com/camel-ai/camel.git

cd camel/docker

# Create a .env file with your OpenAI API key
# See .env.example for other optional keys
echo OPENAI_API_KEY=your_openai_api_key > .env

docker compose up
```


Then you can see the build process of the docker image, and after the build 
is completed, you can see the output from 
[examples/ai_society/role_playing.py](../examples/ai_society/role_playing.py).

## Persistence
By adding path mapping in docker-compose.yaml, you can map the local camel 
folder to the container to achieve persistence.

```
version: "3.9"
services:
  camel:
    image: camel:py3.10
    container_name: camel
    build:
      context: ../
      dockerfile: ./docker/Dockerfile
    env_file:
      - .env
    volumes:
      - ../:/app/camel
    command: ["python", "ai_society/role_playing.py"]
```
