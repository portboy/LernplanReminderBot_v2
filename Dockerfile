# Multi-stage optional (hier Single-stage für Einfachheit)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (falls nötig später erweitern)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and sources first (src-layout)
COPY pyproject.toml ./
COPY src ./src

# Install dependencies (editable not nötig im Container, aber sorgt für klaren Importpfad)
RUN pip install --upgrade pip && pip install .[dev]

# Create data directory for runtime use
RUN mkdir -p /app/data

VOLUME ["/app/data"]

CMD ["python", "-m", "bot.main"]
