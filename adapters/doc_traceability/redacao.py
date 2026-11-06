"""Transforma o rascunho estruturado da descoberta numa SDD do framework e na entrada do registry.

O agente não escreve Markdown: devolve campos, e a forma sai daqui, igual toda vez. Assim o que os
validadores reprovam é conteúdo, não formatação.
"""

import json
import re
from pathlib import Path

import yaml

DIR_SDD = "docs/sdd"
INSTRUCAO_DE_CONSUMO = (
    "Leia a SDD inteira antes de implementar. Não implemente se o status não for approved."
)
TAG = "fabrica-descoberta"


def _texto(valor: str) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _crases(itens: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in itens)


def numero_seguinte(repo: Path, codigo: str) -> int:
    """Maior número já usado no registry ou em arquivo, mais um. Arquivadas também contam."""
    padrao = re.compile(rf"SDD-{re.escape(codigo)}-(\d+)")
    usados = [int(m) for m in padrao.findall(_ler_registry_texto(repo))]
    usados += [
        int(achado.group(1))
        for caminho in (repo / DIR_SDD).rglob("SDD-*.md")
        if (achado := padrao.search(caminho.name))
    ]
    return max(usados, default=0) + 1


def _ler_registry_texto(repo: Path) -> str:
    registro = repo / DIR_SDD / "registry.yaml"
    return registro.read_text(encoding="utf-8") if registro.is_file() else ""


def montar_sdd(rascunho: dict, sdd_id: str, codigo: str, owner: str, hoje: str, status: str) -> str:
    requisitos = "\n".join(
        f"| {r['id']} | {r['requisito']} | {r['aceite']} | {_crases(r['arquivos'])} |"
        for r in rascunho["requisitos"]
    )
    criterios = "\n".join(
        f"| {i} | {c['criterio']} | `{c['comando']}` | {c['esperado']} | automatizado |"
        for i, c in enumerate(rascunho["criterios"], 1)
    )
    tarefas = ""
    if rascunho.get("tarefas"):
        linhas = "\n".join(
            f"| {i} | {t['descricao']} | {', '.join(t['requisitos'])} | {_crases(t['arquivos'])} "
            f"| {', '.join(t['depende_de']) or '-'} |"
            for i, t in enumerate(rascunho["tarefas"], 1)
        )
        tarefas = (
            "## Decomposição em tasks\n\n"
            "| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |\n"
            f"|---|---|---|---|---|\n{linhas}\n\n"
        )
    return f"""---
id: {sdd_id}
type: SDD
title: {_texto(rascunho["titulo"])}
status: {status}
project: {_texto(codigo)}
owner: {_texto(owner)}
created: "{hoje}"
updated: "{hoje}"
relates_to: []
source_docs: []
consumption_instructions: {_texto(INSTRUCAO_DE_CONSUMO)}
sizing: {rascunho["sizing"]}
supersedes: null
superseded_by: null
tags: [{TAG}]
---

# {rascunho["titulo"]}

## Resumo executivo

{rascunho["resumo"]}

## Decisão(ões) de arquitetura aplicável(is)

Sem ADR: SDD nascida da descoberta da fábrica, sem documento de origem. {rascunho["arquitetura"]}

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
{requisitos}

## Especificação técnica consolidada

{rascunho["especificacao"]}

{tarefas}## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
{criterios}

## Instruções específicas para a IA implementadora

Toque só nos arquivos listados. {rascunho["instrucoes"]}

## Verificação de escopo (nada a mais, nada a menos)

- [ ] Todo requisito consolidado acima tem código correspondente.
- [ ] Todo arquivo tocado aparece nesta SDD.
- [ ] Nenhuma abstração, config, feature flag ou refactor extra.

## Evidência de verificação (preencher antes de status `implemented`)

**Verificador independente:** sim

| # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (descoberta da fábrica) |
"""


def registrar(
    repo: Path,
    sdd_id: str,
    titulo: str,
    codigo: str,
    owner: str,
    hoje: str,
    status: str,
    versao_framework: str,
) -> None:
    """Acrescenta a SDD ao registry, criando-o num projeto que ainda não tem nenhuma."""
    registro = repo / DIR_SDD / "registry.yaml"
    registro.parent.mkdir(parents=True, exist_ok=True)
    texto = (
        registro.read_text(encoding="utf-8")
        if registro.is_file()
        else (
            f"project: {_texto(codigo)}\nframework_version: {_texto(versao_framework)}\ndocuments:\n"
        )
    )
    existentes = yaml.safe_load(texto) or {}
    if any(d.get("id") == sdd_id for d in existentes.get("documents") or []):
        raise ValueError(f"{sdd_id} já está no registry")
    if not texto.endswith("\n"):
        texto += "\n"
    texto += (
        f"  - id: {sdd_id}\n"
        "    type: SDD\n"
        f"    title: {_texto(titulo)}\n"
        f"    status: {status}\n"
        f"    owner: {_texto(owner)}\n"
        f'    created: "{hoje}"\n'
        f'    updated: "{hoje}"\n'
        "    relates_to: []\n"
        f'    path: "{DIR_SDD}/{sdd_id}.md"\n'
        f"    tags: [{TAG}]\n"
    )
    registro.write_text(texto, encoding="utf-8")


def escrever_sdd(
    repo: Path,
    rascunho: dict,
    codigo: str,
    owner: str,
    hoje: str,
    status: str,
    versao_framework: str,
    sdd_id: str | None = None,
) -> str:
    """Grava SDD e registry na cópia e devolve o caminho relativo da SDD."""
    sdd_id = sdd_id or f"SDD-{codigo}-{numero_seguinte(repo, codigo):04}"
    caminho = f"{DIR_SDD}/{sdd_id}.md"
    (repo / DIR_SDD).mkdir(parents=True, exist_ok=True)
    (repo / caminho).write_text(
        montar_sdd(rascunho, sdd_id, codigo, owner, hoje, status), encoding="utf-8"
    )
    registrar(repo, sdd_id, rascunho["titulo"], codigo, owner, hoje, status, versao_framework)
    return caminho
