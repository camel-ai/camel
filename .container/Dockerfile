FROM python:3.14-bookworm@sha256:14ab73bd56794689c00cce8162da1eb71925b188299f35f81717ec23816a5dea

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
