# Multi-stage build for optimized production image
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip && pip install --no-cache-dir .

# ── Production stage ──────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Berlin

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data /app/userconfig && \
    chown -R botuser:botuser /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=botuser:botuser src ./src

USER botuser

VOLUME ["/app/data", "/app/userconfig"]

# Health check verifies config loadable + Telegram API reachable
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "src/healthcheck.py"]

CMD ["python", "-m", "bot.main"]
