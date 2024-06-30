# Install CAMEL with Docker

Docker offers an easy way to create a consistent and isolated virtual
environment, containers, for setting up the dependencies of CAMEL. This guide
will show you how to quickly set up CAMEL, run the examples, and also
develop on it, with Docker.

## Prerequisites
- Docker：https://docs.docker.com/engine/install/
- Docker Compose：https://docs.docker.com/compose/install/

## Build Image
To build the image of CAMEL, first you need to navigate into the
[docker](../docker) folder and create a `.env` file with your API keys.

```bash
cd docker

# Create a .env file with your OpenAI API key only
# For other optional keys that can be added into .env, see .env.example
echo OPENAI_API_KEY=your_openai_api_key > .env
```

Then you can build the image with the following command. This will 
automatically set up the environment and dependencies for CAMEL.

```bash
docker compose build
```

After the build is completed, you can see the image `camel` in the list
of images.

```bash
docker images
```

## Container Management

### Create Container
A container is where we are going to run the CAMEL code and develop with it.
To start a container, you can use the following command.

```bash
docker run -it -d --name camel camel:py3.10
```

A container named `camel` would be created and started in the background. You
can check the status of the container with the following command.

```bash
docker ps
```

### Attach to Running Container
To enter the running container, simply run the following command.

```bash
docker exec -it camel bash
```

Then you will be in the container environment under the CAMEL directory, with
all the dependencies installed.

### Stop & Restart Container
You can stop the container when it's not being used, and restart it later with
the following commands.

```bash
docker stop camel
docker start camel
```

## Run Examples
We offer some examples in the [examples](../examples) folder. You can
quickly run [examples/ai_society/role_playing.py](../examples/ai_society/role_playing.py), the example that
best demonstrates our system, with the following command.

```bash
docker compose up
```

This will start a new container named `camel-example` and run the example. You
can see the output of the example once the container is started.
