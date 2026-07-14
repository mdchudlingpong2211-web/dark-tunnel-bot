# Minimal, production-ready image for the Dark Tunnel decryptor bot.
FROM python:3.12-slim

# System deps for `cryptography` (build against OpenSSL) and `tgcrypto`
# (a native C extension that needs standard libc headers to compile).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/downloads
ENV DOWNLOAD_DIR=/app/downloads \
    PYTHONUNBUFFERED=1

# The container restarts the process itself (see main.py); the platform's
# restart policy (Docker `--restart unless-stopped`, Fly/Render/Railway
# auto-restart) provides the outer safety net if the whole process exits.
CMD ["python", "main.py"]
