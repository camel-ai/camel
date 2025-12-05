FROM python:3.10-bookworm@sha256:7dd2fbef5caa5ad7be66474411cff3a6a2dcf7f9f9cb16fd962e819f4f57b85f

RUN pip install uv
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY . /app/camel
WORKDIR /app/camel
RUN chown -R appuser:appuser /app/camel

RUN uv venv .venv --python=3.10 && \
    . .venv/bin/activate && \
    uv pip install -e ".[all, dev, docs]" && \
    pip install pre-commit mypy

USER appuser

CMD ["tail", "-f", "/dev/null"]
