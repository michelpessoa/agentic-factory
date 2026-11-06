FROM node:22-slim

ARG GITLEAKS_VERSAO=8.21.2
ARG GITLEAKS_SHA256=5bc41815076e6ed6ef8fbecc9d9b75bcae31f39029ceb55da08086315316e3ba

RUN apt-get update \
 && apt-get install -y --no-install-recommends git python3 curl ca-certificates \
 && curl -fsSL -o /tmp/gitleaks.tgz "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSAO}/gitleaks_${GITLEAKS_VERSAO}_linux_x64.tar.gz" \
 && echo "${GITLEAKS_SHA256}  /tmp/gitleaks.tgz" | sha256sum -c - \
 && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
 && rm -f /tmp/gitleaks.tgz \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /trabalho /home/agente

WORKDIR /trabalho
