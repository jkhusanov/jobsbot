FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

RUN useradd -r -u 1001 jobsbot && \
    mkdir -p /data && chown -R jobsbot:jobsbot /data
USER jobsbot

ENV DATABASE_PATH=/data/bot.db

CMD ["python", "-m", "jobsbot"]
