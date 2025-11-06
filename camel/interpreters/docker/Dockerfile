# syntax=docker/dockerfile:1
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

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

RUN apt-get update && \
    apt-get install -y r-base && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get autoremove -y

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get autoremove -y

RUN curl -fsSL https://install.python-poetry.org | python3.10 - && \
    ln -s ~/.local/bin/poetry /usr/local/bin/poetry

RUN python3.10 -m pip install --upgrade pip setuptools wheel
RUN pip install uv

RUN groupadd -r devuser && useradd -r -m -g devuser devuser
WORKDIR /workspace
RUN chown -R devuser:devuser /workspace
USER devuser

CMD ["/bin/bash"]
