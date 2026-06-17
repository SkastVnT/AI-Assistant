# ------ Base stage ------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for asyncpg, psycopg
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------ Runtime stage ------
FROM base AS runtime

RUN useradd -m -u 1001 appuser

COPY --chown=appuser:appuser libs/ libs/
COPY --chown=appuser:appuser apps/ apps/

ENV PYTHONPATH=/app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
