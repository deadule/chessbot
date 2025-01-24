FROM python:3.13-slim-bookworm

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry install

COPY ./ ./

CMD ["poetry", "run", "python", "/app/main/bot.py"]
