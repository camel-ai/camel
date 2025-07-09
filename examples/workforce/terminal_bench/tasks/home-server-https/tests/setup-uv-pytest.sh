#!/bin/bash

# Install curl and net-tools for network testing (if needed)
which curl >/dev/null || apt-get update && apt-get install -y curl
which netstat >/dev/null || apt-get install -y net-tools

# Python testing dependencies are already installed in the container
echo "Testing dependencies are pre-installed"
