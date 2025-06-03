# syntax=docker/dockerfile:1

FROM ubuntu:22.04

# Update and install base utilities
RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    curl \
    wget \
    git \
    git-lfs \
    netcat \
    sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install Python 3.10 and its dependencies
RUN add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        python3.10-distutils \
        python3-pip \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# Install NodeJS 22.x
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs

# Install Poetry
RUN curl -fsSL https://install.python-poetry.org | python3.10 - \
    && ln -s ~/.local/bin/poetry /usr/local/bin/poetry

# Install NVM and latest LTS Node.js
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash && \
    export NVM_DIR="$HOME/.nvm" && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    nvm install --lts


# Install Python packages
RUN python3.10 -m pip install --upgrade pip setuptools wheel 

# Create version check script

# Setup working directory
WORKDIR /workspace

# Set default shell
CMD ["/bin/bash"]
