# syntax=docker/dockerfile:1

# Whisper STT container (placeholder local source build)
# Official repo: https://github.com/ggerganov/whisper.cpp

FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    python3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Build whisper.cpp
RUN git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git whisper.cpp
WORKDIR /opt/whisper.cpp
RUN cmake -B build -DGGML_NATIVE=OFF \
  && cmake --build build -j2

# Runtime image
FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary
COPY --from=0 /opt/whisper.cpp/build/bin/whisper-cli /app/whisper-cli

# Minimal API surface (left as interface placeholder).
# For now, container is intended to be built and later wired by the gateway.
EXPOSE 9001

CMD ["/app/whisper-cli", "--help"]

