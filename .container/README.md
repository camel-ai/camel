# Install CAMEL with Docker

Docker offers an easy way to create a consistent and isolated virtual
environment, containers, for setting up the dependencies of CAMEL. This guide
will show you how to quickly set up CAMEL, run the examples, and also
develop on it, with Docker.

## Prerequisites
- Docker：https://docs.docker.com/engine/install/
- Docker Compose：https://docs.docker.com/compose/install/

## Cnfigure Environment
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
dependencies for CAMEL.

```bash
docker compose up -d
```

After the build is completed, you can see the image `camel:latest` in the list
of images, along with a started container, `camel`.

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
We don't support volume mounting in the Docker container currently (you are 
welcomed to do this though), which means that **if you delete the 
container, all the local changes you made will be LOST**. To save your
progress, committing and pushing your changes to a remote repository is a 
must before deleting the container, and this is also recommended each time 
before you exit the container.

## Exit, Stop and Delete the Container
You can simply press `Ctrl + D` or use the `exit` command to exit the
container.

After exiting the container, under normal cases the container will still be 
running in the background. If you don't need the container anymore, you can 
stop and delete the container with the following command.

```bash
docker compose down
```

As mentioned in the previous section, all the local changes you made will be
lost after deleting the container. So remember to save your progress!


