# Strands Decider só para a comparação da Fase 3. Roda sem rede: pacote e pesos entram na construção.
FROM python:3.12-slim

ARG DECIDER_VERSAO=0.2.0
ARG DECIDER_SHA256=0db271286469f747e3c5d91a018d0d48801b56ea2dd9fea0f2d9384dd4f1781c
ARG DECIDER_URL=https://files.pythonhosted.org/packages/40/78/2faba02db16433eaa445174ba2d4551bf1378b4fadabc0b6674687cf6aef/strands_decider-0.2.0-py3-none-any.whl
ARG MODELO=StrandsAgents/strands-decider-2B-qwen3.5-v1-2610
ARG MODELO_REVISAO=216d1ccb46a9e9b036eb9187b248db98480f77d4
ARG BASE=Qwen/Qwen3.5-2B-Base
ARG BASE_REVISAO=b1485b2fa6dfa1287294f269f5fb618e03d52d7c

ENV HF_HOME=/modelos

RUN pip install --no-cache-dir "torch==2.15.0" --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir "strands-decider @ ${DECIDER_URL}#sha256=${DECIDER_SHA256}" "transformers==5.22.1" \
 && python -c "from huggingface_hub import snapshot_download as s; s('${MODELO}', revision='${MODELO_REVISAO}'); s('${BASE}', revision='${BASE_REVISAO}')" \
 && chmod -R a+rX /modelos \
 && mkdir -p /trabalho /home/agente

ENV HF_HUB_OFFLINE=1
WORKDIR /trabalho
