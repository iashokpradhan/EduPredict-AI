# syntax=docker/dockerfile:1
# ──────────────────────────────────────────────────────────────────────────────
# EduPredict AI — Production Dockerfile
# Builds model artifacts from synthetic data at image-build time so the
# container is fully self-contained with no private dataset required.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# ── Dependency layer (cached separately for faster rebuilds) ──────────────────
FROM base AS deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ── Application + model-build layer ──────────────────────────────────────────
FROM deps AS builder
COPY . .

# Build demo model artifacts from synthetic data (no private CSV needed).
# If the real dataset is present (e.g. mounted volume), prefer real models.
RUN if [ -f "data/raw/Student_data.csv" ]; then \
        echo "Real dataset found — building production models..."; \
        python -m src.build_models; \
    else \
        echo "No dataset found — building synthetic demo models for deployment..."; \
        python -m src.build_synthetic_demo_models; \
    fi

# ── Final runtime image ───────────────────────────────────────────────────────
FROM base AS runtime
WORKDIR /app

# Copy installed packages from deps layer
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source and built artifacts
COPY --from=builder /app /app

# Create non-root user for defense-in-depth
RUN useradd -u 1000 -m edupredict && \
    chown -R edupredict:edupredict /app
USER edupredict

# Railway sets $PORT dynamically; default to 8000 locally
ENV PORT=8000

EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

CMD ["sh", "-c", "python -m uvicorn src.api:app --host 0.0.0.0 --port ${PORT}"]
