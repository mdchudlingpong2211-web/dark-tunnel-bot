# Minimal, production-ready image for the Dark Tunnel decryptor bot.
FROM python:3.12-slim

# System deps for `cryptography` and `tgcrypto` (native C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libc6-dev \
        python3-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/downloads
ENV DOWNLOAD_DIR=/app/downloads \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
