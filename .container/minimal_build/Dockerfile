FROM python:3.10-bookworm

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Configurate Poetry
RUN poetry config virtualenvs.create false

COPY . /app/camel

WORKDIR /app/camel

RUN poetry install

CMD ["tail", "-f", "/dev/null"]