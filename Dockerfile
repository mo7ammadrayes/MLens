# MLens backend (FastAPI) image.
#
# Build:  docker build -t mlens-api .
# Run:    docker run --rm -p 8000:8000 --env-file .env mlens-api
#
# Secrets are never copied into the image (see .dockerignore); they are
# passed in at run time with --env-file or the host's environment settings.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    PORT=8000

WORKDIR /app

# Install dependencies first: this layer is cached and only rebuilt when
# requirements.txt changes, so code edits rebuild in seconds.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code only (the frontend is deployed separately).
COPY backend ./backend

# COPY keeps the files' permissions from the build machine. Make the code
# readable (and folders enterable) by everyone, while it stays owned by root,
# so the app user below can read it but not modify it.
RUN chmod -R a+rX /app/backend

# Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 10001 mlens
USER mlens

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"

# PORT is set by most hosting platforms; defaults to 8000 locally.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
