# Ubuntu Docker Runtime Example

This example demonstrates how to use the CAMEL framework with Docker runtime in an Ubuntu environment.

## Prerequisites

- Docker installed and running
- Python 3.10 or later
- CAMEL package installed

## Directory Structure

```
ubuntu_docker_runtime/
├── README.md
├── manage_camel_docker.sh
└── test_camel_docker.py
```

## Setup and Running

1. First, build and manage the Docker image:

```bash
cd camel/examples/runtime/ubuntu_docker_runtime
chmod +x manage_camel_docker.sh
./manage_camel_docker.sh build
```

2. Verify the image was created:

```bash
docker images | grep my-camel
```

You should see `my-camel:latest` in the list.

3. Run the test script:

```bash
python test_camel_docker.py
```

The test will:
- Start a Docker container with the CAMEL runtime
- Initialize the API server
- Run basic math operations to verify functionality

## Expected Output

You should see output similar to this:

```
Waiting for runtime to start...

Testing math operations...

Add 1 + 2: 3

Subtract 5 - 3: 2

Multiply 2 * 3: 6
```

## Troubleshooting

If you encounter issues:

1. Check Docker status:
```bash
docker ps -a
```

2. Check container logs:
```bash
docker logs <container_id>
```

3. Clean up and rebuild:
```bash
./manage_camel_docker.sh clean
./manage_camel_docker.sh build
```

## Additional Commands

- Stop all containers: `./manage_camel_docker.sh stop`
- Remove all containers: `./manage_camel_docker.sh clean`
- Rebuild image: `./manage_camel_docker.sh rebuild`

## Notes

- The container uses port 8000 by default
- Python path is set to `/usr/bin/python3`
- The API server runs inside the container 