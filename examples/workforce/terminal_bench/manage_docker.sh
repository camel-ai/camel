#!/bin/bash

# --- Configuration ---
# Name for the common base image
BASE_IMAGE_NAME="camel-base"
BASE_TAG="latest"

# Set default task name (used if no argument is provided)
DEFAULT_TASK="play-zork"

# Get task name from command line argument. Use the second argument ($2) for the task name.
TASK=${2:-$DEFAULT_TASK}
FULL_NAME=$TASK # The final image will be named after the task

# --- Path Setup ---
# Get absolute paths for script and project root directories
BASH_SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CAMEL_ROOT="$( cd "$BASH_SOURCE_DIR/../../.." && pwd )" # Assumes script is in a subdir of the project root
TASK_DIR="$BASH_SOURCE_DIR/tasks/$TASK"

# --- Help Information ---
show_help() {
    echo "CAMEL Docker Image Management Script"
    echo ""
    echo "This script uses a two-stage build process:"
    echo "1. A common base image ('$BASE_IMAGE_NAME:$BASE_TAG') is built with shared dependencies."
    echo "2. A final, task-specific image is built on top of the base image."
    echo ""
    echo "Usage: $0 [command] [task_name]"
    echo ""
    echo "Commands:"
    echo "  build-base        - Build the common base Docker image ('$BASE_IMAGE_NAME')."
    echo "  build [task]      - Build a new Docker image for a specific task (e.g., 'play-zork')."
    echo "                      Builds the base image first if it doesn't exist."
    echo "  rebuild [task]    - Clean and rebuild the task-specific image."
    echo "  clean [task]      - Clean containers and image for a specific task."
    echo "  clean-base        - Clean the common base image."
    echo "  clean-all [task]  - Clean both the task-specific and the common base images."
    echo "  list [task]       - List related containers and images for a task."
    echo "  help              - Show this help message."
    echo ""
    echo "Example: $0 build play-zork"
}

# --- Function to build the common base image ---
build_base_image() {
    echo "----------------------------------------------------"
    echo "Building common base image: $BASE_IMAGE_NAME:$BASE_TAG"
    echo "----------------------------------------------------"
    
    # Use Dockerfile_camel from the script's directory
    local dockerfile_camel_path="$BASH_SOURCE_DIR/Dockerfile_camel"
    if [ ! -f "$dockerfile_camel_path" ]; then
        echo "Error: Base Dockerfile not found at $dockerfile_camel_path"
        exit 1
    fi

    echo "Using CAMEL source path: $CAMEL_ROOT"
    
    # Build with the CAMEL_ROOT as the context to allow COPY ../../..
    # We pass the Dockerfile path using the -f flag.
    docker build -t "$BASE_IMAGE_NAME:$BASE_TAG" -f "$dockerfile_camel_path" "$CAMEL_ROOT"
    
    local build_result=$?
    
    if [ $build_result -eq 0 ]; then
        echo "✅ Base image '$BASE_IMAGE_NAME:$BASE_TAG' built successfully."
    else
        echo "❌ Base image build failed!"
        exit 1
    fi
}


# --- Function to build the task-specific image ---
build_task_image() {
    echo "----------------------------------------------------"
    echo "Building task image for: $TASK"
    echo "----------------------------------------------------"

    # 1. Check if the base image exists, if not, build it.
    if ! docker image inspect "$BASE_IMAGE_NAME:$BASE_TAG" &> /dev/null; then
        echo "Base image '$BASE_IMAGE_NAME:$BASE_TAG' not found. Building it first."
        build_base_image
    else
        echo "Using existing base image: $BASE_IMAGE_NAME:$BASE_TAG"
    fi

    local task_dockerfile_path="$TASK_DIR/Dockerfile"
    if [ ! -f "$task_dockerfile_path" ]; then
        # try to find in $TASK_DIR/client
        task_dockerfile_path="$TASK_DIR/client/Dockerfile"
        if [ -f "$task_dockerfile_path" ]; then
            # try to find in $TASK_DIR/server
            task_dockerfile_path="$TASK_DIR/client/Dockerfile"
            TASK_DIR="$TASK_DIR/client"
        else
            echo "Error: Task Dockerfile not found at $task_dockerfile_path"
            exit 1
        fi
    fi

    # 2. Create a temporary Dockerfile to avoid modifying the original
    local temp_dir=$(mktemp -d)
    local temp_dockerfile="$temp_dir/Dockerfile"
    
    echo "Creating temporary build directory: $temp_dir"
    cp "$task_dockerfile_path" "$temp_dockerfile"

    # 3. Replace the FROM line in the task's Dockerfile with our base image
    # This uses sed to find a line starting with FROM (case-insensitive) and replace it.
    sed -i.bak "s/^[Ff][Rr][Oo][Mm].*/FROM $BASE_IMAGE_NAME:$BASE_TAG/" "$temp_dockerfile"
    cat "$temp_dockerfile"
    # exit 0
    echo "Modified Dockerfile to use '$BASE_IMAGE_NAME:$BASE_TAG' as base."
    
    # 4. Build the task image
    # The build context is the task's own directory to allow for relative COPY commands.
    echo "Using build context: $TASK_DIR"
    docker build -t "$FULL_NAME" -f "$temp_dockerfile" "$TASK_DIR"
    
    local build_result=$?
    
    # 5. Clean up the temporary directory
    rm -rf "$temp_dir"
    
    if [ $build_result -eq 0 ]; then
        echo ""
        echo "✅ Docker image build for task '$TASK' successful!"
        echo "Image name: $FULL_NAME"
        echo ""
        echo "You can use this image in your code as follows:"
        echo "runtime = DockerRuntime(\"$FULL_NAME\")"
    else
        echo "❌ Docker image build for task '$TASK' failed!"
        exit 1
    fi
}

# --- Cleanup Functions ---
clean_task() {
    echo "Cleaning up resources for task: $FULL_NAME"
    
    # Stop and remove related containers
    local containers=$(docker ps -a --filter "ancestor=${FULL_NAME}" --format "{{.ID}}")
    if [ -n "$containers" ]; then
        echo "Stopping and removing containers..."
        docker stop $containers >/dev/null 2>&1
        docker rm $containers >/dev/null 2>&1
    else
        echo "No related containers found."
    fi

    # Remove task image
    if docker image inspect "$FULL_NAME" &> /dev/null; then
        echo "Removing image: $FULL_NAME"
        docker rmi "$FULL_NAME"
    else
        echo "No image found for '$FULL_NAME'."
    fi
    echo "Task cleanup complete."
}

clean_base() {
    echo "Cleaning up base image: $BASE_IMAGE_NAME:$BASE_TAG"

    # Check if any task images depend on the base image
    local dependent_images=$(docker images --filter "reference=*/*" --format '{{.Repository}}:{{.Tag}} {{.ID}}' | \
                             while read -r repo tag id; do \
                                 if docker image inspect --format '{{.Parent}}' "$id" | grep -q "$(docker image inspect --format '{{.Id}}' "$BASE_IMAGE_NAME:$BASE_TAG")"; then \
                                     echo "$repo:$tag"; \
                                 fi; \
                             done)

    if [ -n "$dependent_images" ]; then
        echo "Warning: Cannot remove base image as other images depend on it:"
        echo "$dependent_images"
        echo "Please clean the task images first."
        return
    fi

    if docker image inspect "$BASE_IMAGE_NAME:$BASE_TAG" &> /dev/null; then
        echo "Removing base image..."
        docker rmi "$BASE_IMAGE_NAME:$BASE_TAG"
    else
        echo "Base image not found."
    fi
    echo "Base image cleanup complete."
}


# --- List Resources Function ---
list_resources() {
    echo "--- Docker Resources for Task: $FULL_NAME ---"
    echo ""
    echo "Container(s):"
    docker ps -a --filter "ancestor=${FULL_NAME}"
    echo ""
    echo "Image Information:"
    docker images "$FULL_NAME"
    echo ""
    echo "--- Base Image Information ---"
    docker images "$BASE_IMAGE_NAME:$BASE_TAG"
}

# --- Main Execution Logic ---
case "$1" in
    "build-base")
        build_base_image
        ;;
    "build")
        build_task_image
        ;;
    "rebuild")
        clean_task
        build_task_image
        ;;
    "clean")
        clean_task
        ;;
    "clean-base")
        clean_base
        ;;
    "clean-all")
        clean_task
        clean_base
        ;;
    "list")
        list_resources
        ;;
    "help"|""|*)
        show_help
        exit 1
        ;;
esac