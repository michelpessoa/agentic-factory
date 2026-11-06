FROM node:22-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ripgrep curl ca-certificates python3 \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code@2.1.318 \
 && mkdir -p /trabalho /home/agente

ENV DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

WORKDIR /trabalho
