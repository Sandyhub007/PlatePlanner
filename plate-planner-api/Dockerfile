# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:$PATH"

# Install system packages needed for build
RUN apt-get update && apt-get install -y \
    curl build-essential netcat-openbsd git zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Poetry (pin version for reproducible builds)
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=2.3.2 python3 -

# Install Taskfile binary
RUN curl -sL https://taskfile.dev/install.sh | sh && \
    mv ./bin/task /usr/local/bin/task

WORKDIR /app

# Copy dependency management files
COPY pyproject.toml poetry.lock Taskfile.yml ./

# Install main dependencies without virtualenv
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

# Download spaCy language model
RUN python -m spacy download en_core_web_sm

# Copy source code
COPY src/ ./src/

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim

ENV PYTHONPATH="/app/src:/usr/local/lib/python3.11/site-packages"
ENV PYTHONUNBUFFERED=1

# Install only runtime system deps
RUN apt-get update && apt-get install -y \
    netcat-openbsd zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/task /usr/local/bin/task

# Copy app source
COPY --from=builder /app /app

WORKDIR /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
