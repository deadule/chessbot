FROM python:3.13-slim-bookworm

RUN pip install poetry

# Install FFmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry install

COPY ./ ./

CMD ["poetry", "run", "python", "/app/web-server.py"]
