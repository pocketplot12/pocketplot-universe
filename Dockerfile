# =============================================================================
# PocketPlot — production Dockerfile
# Lightweight, single-stage, non-root, gunicorn
# =============================================================================
# Build:   docker build -t pocketplot:latest .
# Run:     docker run -d -p 5000:5000 --env-file .env --name pocketplot \
#             -v pocketplot_data:/app/data \
#             -v pocketplot_outbox:/app/outbox \
#             pocketplot:latest
# =============================================================================

FROM python:3.12-slim AS runtime

# ---- metadata ----
LABEL org.opencontainers.image.title="PocketPlot" \
      org.opencontainers.image.description="Personalised bedtime stories, delivered every night" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/pocketplot/pocketplot"

# ---- system deps ----
#   - build-essential: needed by some wheels (cryptography, cffi) during pip install
#   - libffi-dev / libssl-dev: common native deps
#   - tini: tiny init that forwards signals and reaps zombies (clean shutdown for gunicorn)
# We install them, then strip them out at the end with --no-install-recommends.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- non-root user (security baseline) ----
# Run as a dedicated user so a container escape can't write to /
RUN groupadd --system --gid 1001 pocketplot \
    && useradd  --system --uid 1001 --gid pocketplot --home /app --shell /sbin/nologin pocketplot

# ---- app layout ----
WORKDIR /app

# ---- python deps (separate layer, cached on py change) ----
# Copying requirements.txt first lets Docker cache the pip install layer
# even when app.py changes — most of the time you only change code, not deps.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt gunicorn==22.0.0

# ---- app source ----
# (Excludes handled by .dockerignore: outbox/, *.db, .env, __pycache__, venv/, .git/)
COPY app.py /app/app.py
COPY README.md /app/README.md
COPY guide.html /app/guide.html

# ---- runtime directories (mounted as volumes in production) ----
# /app/data     -> SQLite database (pocketplot.db)
# /app/outbox   -> saved email files when SMTP is not configured
# Both are created with the right ownership for the non-root user.
RUN mkdir -p /app/data /app/outbox \
    && chown -R pocketplot:pocketplot /app

# ---- health check ----
# Docker uses this to mark the container healthy once /healthz returns 200.
# gunicorn's readiness is implicit — the worker is ready when the server is listening.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail --silent http://localhost:5000/healthz || exit 1

# ---- gunicorn settings ----
# - 1 worker: APScheduler runs in-process and must not be duplicated.
#   PocketPlot is I/O-bound (SMTP sends, Stripe API calls); for 10k+ users
#   you'd switch to gevent or a proper task queue, not more workers.
# - 4 threads: handle small bursts of concurrent requests within the single worker.
# - 120s timeout: enough for slow SMTP calls but not pathologically long.
# - bind 0.0.0.0:5000: standard container networking.
ENV GUNICORN_CMD_ARGS="--workers=1 --threads=4 --timeout=120 --access-logfile=- --error-logfile=-"

# ---- env defaults (override via docker-compose env_file or -e) ----
ENV PORT=5000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Where SQLite + outbox live inside the container — mount these as volumes
    # by binding /app/data and /app/outbox to host paths or named volumes.
    POCKETPLOT_DB_PATH=/app/data/pocketplot.db \
    POCKETPLOT_OUTBOX_DIR=/app/outbox

# EXPOSE documents the port; the actual binding is in the CMD.
EXPOSE 5000

# ---- volume declarations (data persists across container restarts) ----
VOLUME ["/app/data", "/app/outbox"]

# ---- run as non-root ----
USER pocketplot

# ---- entrypoint ----
# tini reaps zombies and forwards SIGTERM so gunicorn shuts down gracefully.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--access-logfile=-", "app:app"]
