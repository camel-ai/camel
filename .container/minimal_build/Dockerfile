FROM python:3.10-bookworm

# Install uv
RUN pip install uv

COPY . /app/camel

WORKDIR /app/camel

# Setup virtual environment and install dependencies
RUN uv venv .venv --python=3.10 && \
    . .venv/bin/activate && \
    uv pip install -e ".[all, dev, docs]" && \
    pip install pre-commit mypy

CMD ["tail", "-f", "/dev/null"]