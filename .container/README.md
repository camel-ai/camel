# Install CAMEL with Docker

Docker offers an easy way to create a consistent and isolated virtual
environment, containers, for setting up the dependencies of CAMEL. This guide
will show you how to quickly set up CAMEL, run the examples, and also
develop on it, with Docker.

## Prerequisites
- Docker：https://docs.docker.com/engine/install/
- Docker Compose：https://docs.docker.com/compose/install/

## Configure Environment
Before starting the container, you need to navigate into the
[.container](../.container) folder and create a `.env` file **with your own 
API 
keys**, so that these keys will be present in the environment variables of 
the container, which will later be used by CAMEL. The list of API keys that 
can be found in the `.env.example` file.

```bash
cd .container

# YOU SHOULD EDIT .env FILE TO ADD YOUR OWN API KEYS AFTER THIS
cp .env.example .env
```

## Start Container
After configuring the API keys, simply run the following command to start 
up the working container. This will automatically set up the environment and
dependencies for CAMEL. It may take some time, please be patient.

```bash
docker compose up -d
```

After the build is completed, you can see the image `camel:localdev` in the 
list of images, along with a started container, `camel-localdev`.

```bash
# check the list of images
docker images

# check the list of running containers
docker ps
```

## Enter Container
You can enter the container with the following command.

```bash
docker compose exec camel bash
```

Then you will be in the container environment under the CAMEL directory, with
all the dependencies installed.

Then You can try running the 
[role_playing.py](../examples/ai_society/role_playing.py)
example.

```bash
python examples/ai_society/role_playing.py
```

If you see the agents interacting with each other, this means you are all set.
Have fun with CAMEL in Docker!

## Save Your Progress
We support volume mounting in the started container, which means that all 
of your changes in the CAMEL directory inside the container will be synced 
into the CAMEL repo on your host system. Therefore, you don't need to worry
about losing your progress when you exit the container.

## Exit, Stop and Delete the Container
You can simply press `Ctrl + D` or use the `exit` command to exit the
container.

After exiting the container, under normal cases the container will still be 
running in the background. If you don't need the container anymore, you can 
stop and delete the container with the following command.

```bash
docker compose down
```

## Online Images
For users who only want to have a quick tryout on CAMEL, we also provide the 
pre-built images on
[our GitHub Container Registry](https://github.com/camel-ai/camel/pkgs/container/camel).
Considering the size of the image, we only offer the image with the basic 
dependencies.

Note that there are some key differences between the local development 
image and the pre-built image that you should be aware of.
1. The pre-built image is built upon the source code of each release of CAMEL. 
   This means that they are not suitable for development, as they don't 
   contain the git support. If you want to develop on CAMEL, please build 
   the image by yourself according to the instructions above.
2. The pre-built image only contains the basic dependencies for running the 
   examples. If you want to run the examples that require additional 
   dependencies, you need to install them according to the 
   installation guide in CAMEL's [README](../README.md).
3. The pre-built image doesn't contain the API keys. You need to set up the 
   API keys by yourself in the container environment.
4. The pre-built image does not support volume mounting. This means that all 
   of your changes in the container will be lost when you delete the container.

To quickly start a container with the pre-built image, you can use the
following command.

```bash
docker run -it -d --name camel ghcr.io/camel-ai/camel:latest
```

Attach to the container with the following command.

```bash
docker exec -it camel bash
```

After setting the environment, you can run the example with the following
command.

```bash
python examples/ai_society/role_playing.py
```