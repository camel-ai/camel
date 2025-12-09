FROM python:3.14-bookworm@sha256:b58ea3b4b4206bef0f640c44b51aa6160056b48526bf2cca5e62525bf542cefe

RUN pip install uv
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app/camel
COPY . .
RUN chown -R appuser:appuser /app/camel

RUN uv venv .venv --python=3.10 && \
    . .venv/bin/activate && \
    uv pip install -e ".[all, dev, docs]" && \
    pip install pre-commit mypy && \
    pre-commit install

ENV VIRTUAL_ENV=/app/camel/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

USER appuser

CMD ["bash"]
