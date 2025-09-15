#!/bin/bash

# Set image name and tag
IMAGE_NAME="my-camel"
TAG="latest"
FULL_NAME="${IMAGE_NAME}:${TAG}"

# Get CAMEL project root directory absolute path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CAMEL_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Display help information
show_help() {
    echo "CAMEL Docker Image Management Script"
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  build    - Build new Docker image"
    echo "  clean    - Clean related containers and images"
    echo "  rebuild  - Clean and rebuild image"
    echo "  list     - List related containers and images"
    echo "  help     - Show this help message"
}

# Build Docker image
build_image() {
    echo "Starting Docker image build..."
    echo "Using CAMEL source path: $CAMEL_ROOT"
    
    # Build in temporary directory
    TEMP_DIR=$(mktemp -d)
    echo "Creating temporary build directory: $TEMP_DIR"
    
    # Copy necessary files to temporary directory
    cp "$SCRIPT_DIR/Dockerfile" "$TEMP_DIR/"
    cp -r "$CAMEL_ROOT" "$TEMP_DIR/camel_source"
    
    # Ensure API file exists
    if [ ! -f "$CAMEL_ROOT/camel/runtime/api.py" ]; then
        echo "Error: API file not found at $CAMEL_ROOT/camel/runtime/api.py"
        exit 1
    fi
    
    # Copy API file to a known location
    mkdir -p "$TEMP_DIR/api"
    cp "$CAMEL_ROOT/camel/runtime/api.py" "$TEMP_DIR/api/"
    
    # Modify Dockerfile COPY commands - fix the sed command
    sed -i '' 's|COPY ../../../|COPY camel_source/|g' "$TEMP_DIR/Dockerfile"
    sed -i '' 's|COPY camel/runtime/api.py|COPY api/api.py|g' "$TEMP_DIR/Dockerfile"
    
    # Build in temporary directory
    (cd "$TEMP_DIR" && docker build -t ${FULL_NAME} .)
    
    BUILD_RESULT=$?
    
    # Clean temporary directory
    rm -rf "$TEMP_DIR"
    
    if [ $BUILD_RESULT -eq 0 ]; then
        echo "Docker image build successful!"
        echo "Image name: ${FULL_NAME}"
        echo ""
        echo "You can use this image in your code as follows:"
        echo "runtime = DockerRuntime(\"${FULL_NAME}\")"
    else
        echo "Docker image build failed!"
        exit 1
    fi
}

# Add this function after build_image
check_container() {
    container_id=$1
    echo "Checking container logs..."
    docker logs $container_id
    
    echo "Checking container status..."
    docker inspect $container_id --format='{{.State.Status}}'
    
    echo "Checking if API is responding..."
    curl -v http://localhost:8000/docs
}

# Clean containers and images
clean() {
    echo "Starting cleanup..."
    
    # Stop and remove related containers
    echo "Finding and stopping related containers..."
    containers=$(docker ps -a --filter "ancestor=${FULL_NAME}" --format "{{.ID}}")
    if [ ! -z "$containers" ]; then
        echo "Found following containers:"
        docker ps -a --filter "ancestor=${FULL_NAME}"
        echo "Stopping and removing containers..."
        docker stop $containers 2>/dev/null
        docker rm $containers 2>/dev/null
    else
        echo "No related containers found"
    fi

    # Remove image
    echo "Removing image..."
    if docker images ${FULL_NAME} --format "{{.ID}}" | grep -q .; then
        docker rmi ${FULL_NAME}
        echo "Image removed"
    else
        echo "No related image found"
    fi

    # Clean unused images and build cache
    echo "Cleaning unused images and build cache..."
    docker system prune -f
    
    echo "Cleanup complete"
}

# List related resources
list_resources() {
    echo "Related Docker resources:"
    echo ""
    echo "Container list:"
    docker ps -a --filter "ancestor=${FULL_NAME}"
    echo ""
    echo "Image information:"
    docker images ${FULL_NAME}
}

# Main program
case "$1" in
    "build")
        build_image
        ;;
    "clean")
        clean
        ;;
    "rebuild")
        clean
        build_image
        ;;
    "list")
        list_resources
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac 