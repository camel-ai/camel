# syntax=docker/dockerfile:1

FROM ubuntu:22.04

# Set environment variable to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

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
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install Python 3.10 and its dependencies
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        python3.10-distutils \
        python3-pip \
    && ln -s /usr/bin/python3.10 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install R
RUN apt-get update && \
    apt-get install -y r-base && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get autoremove -y

# Install NodeJS 22.x
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get autoremove -y

# Install Poetry
RUN curl -fsSL https://install.python-poetry.org | python3.10 - && \
    ln -s ~/.local/bin/poetry /usr/local/bin/poetry

# Upgrade pip and install base Python packages
RUN python3.10 -m pip install --upgrade pip setuptools wheel

# Install uv using pip instead of the shell script
RUN pip install uv

# Setup working directory
WORKDIR /workspace

# Set default shell
CMD ["/bin/bash"]
