# Mind IPTV Backend — container image for Koyeb / Fly.io / Cloud Run / local.
# (Render uses render.yaml, not this file.)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# curl_cffi / cryptography ship manylinux wheels; only CA certs needed at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Run as non-root; keep /app writable for runtime addon-config.json edits
RUN useradd -m -u 1000 user
COPY --chown=user:user . /app
USER user

EXPOSE 8000

# main.py reads PORT from env and binds uvicorn on 0.0.0.0
CMD ["python", "main.py"]
