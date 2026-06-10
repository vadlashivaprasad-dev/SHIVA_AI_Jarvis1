# syntax=docker/dockerfile:1

# Piper TTS container (placeholder local source build)
# Official repo: https://github.com/rhasspy/piper

FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Build piper (python-based build/install)
RUN git clone --depth 1 https://github.com/rhasspy/piper.git piper
WORKDIR /opt/piper
RUN pip install --no-cache-dir -e .

# Minimal API surface placeholder.
# For now, container is intended to be built and later wired by the gateway.
EXPOSE 9002

CMD ["python", "-c", "print('Piper container built. Wire gateway /api/v1/voice/synthesize when ENABLE_PIPER=true.')"]

