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
ATOR_DA_POLITICA = "fabrica-agentica"
VERSAO_SDD_ENXUTA = "2.7.0"
LIMITE_DO_RESUMO = 200


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


def _versao(texto: str) -> tuple[int, ...]:
    return tuple(int(p) for p in texto.split("."))


def formato_da_sdd(repo: Path, origens: tuple | list, versao_framework: str) -> str:
    """SDD enxuta só com origem e projeto sob 2.7.0 ou maior: abaixo disso o kit não a confere."""
    if not origens:
        return "completa"
    registro = repo / DIR_SDD / "registry.yaml"
    dados = {}
    if registro.is_file():
        dados = yaml.safe_load(registro.read_text(encoding="utf-8")) or {}
    versao = str(dados.get("framework_version") or versao_framework)
    return "enxuta" if _versao(versao) >= _versao(VERSAO_SDD_ENXUTA) else "completa"


def _ler_registry_texto(repo: Path) -> str:
    registro = repo / DIR_SDD / "registry.yaml"
    return registro.read_text(encoding="utf-8") if registro.is_file() else ""


def montar_sdd(
    rascunho: dict,
    sdd_id: str,
    codigo: str,
    owner: str,
    hoje: str,
    status: str,
    origens: tuple | list = (),
) -> str:
    ids = [o["id"] for o in origens]
    if origens:
        fontes = "source_docs:\n" + "".join(
            f"  - id: {_texto(o['id'])}\n    url: {_texto(o['url'])}\n" for o in origens
        )
        decisao = f"Origem: {', '.join(ids)}, approved no central. "
        rastreio = ", ".join(ids)
    else:
        fontes = "source_docs: []\n"
        decisao = "Sem ADR: SDD nascida da descoberta da fábrica, sem documento de origem. "
        rastreio = "nenhum (descoberta da fábrica)"
    enxuta = rascunho["especificacao"] is None
    if enxuta:
        linhas_rf = "\n".join(
            f"| {r['id']} | {r['origem']} | {r['requisito']} | {_crases(r['arquivos'])} |"
            for r in rascunho["requisitos"]
        )
        requisitos = (
            "Desenho, decisão e critério EARS na SPEC e na ADR de source_docs, por referência.\n\n"
            "| RF-ID | Origem | Requisito (resumo) | Arquivos |\n"
            f"|---|---|---|---|\n{linhas_rf}"
        )
    else:
        linhas_rf = "\n".join(
            f"| {r['id']} | {r['requisito']} | {r['aceite']} | {_crases(r['arquivos'])} |"
            for r in rascunho["requisitos"]
        )
        requisitos = (
            "| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |\n"
            f"|---|---|---|---|\n{linhas_rf}"
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
    arquitetura = (
        ""
        if enxuta
        else f"## Decisão(ões) de arquitetura aplicável(is)\n\n{decisao}{rascunho['arquitetura']}\n\n"
    )
    especificacao = (
        "" if enxuta else f"## Especificação técnica consolidada\n\n{rascunho['especificacao']}\n\n"
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
{fontes}consumption_instructions: {_texto(INSTRUCAO_DE_CONSUMO)}
sizing: {rascunho["sizing"]}
supersedes: null
superseded_by: null
tags: [{TAG}]
---

# {rascunho["titulo"]}

## Resumo executivo

{rascunho["resumo"]}

{arquitetura}## Requisitos consolidados

{requisitos}

{especificacao}{tarefas}## Critérios de aceite / definição de pronto

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
| source_docs | {rastreio} |
"""


def _documents_em_bloco(texto: str) -> str:
    """Troca `documents` em fluxo (`[]`, `[{...}]`) por bloco; outro formato não muda."""
    raiz = yaml.compose(texto)
    if not isinstance(raiz, yaml.MappingNode):
        return texto
    for chave, valor in raiz.value:
        if isinstance(chave, yaml.ScalarNode) and chave.value == "documents":
            break
    else:
        return texto
    if not isinstance(valor, yaml.SequenceNode) or not valor.flow_style:
        return texto
    bloco = "documents:"
    lista = yaml.safe_load(texto)["documents"]
    if lista:
        itens = yaml.safe_dump(lista, allow_unicode=True, sort_keys=False, default_flow_style=False)
        bloco += "\n" + "\n".join(f"  {linha}" for linha in itens.rstrip("\n").split("\n"))
    return texto[: chave.start_mark.index] + bloco + texto[valor.end_mark.index :]


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
    texto = _documents_em_bloco(texto)
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
    origens: tuple | list = (),
) -> str:
    """Grava SDD e registry na cópia e devolve o caminho relativo da SDD."""
    sdd_id = sdd_id or f"SDD-{codigo}-{numero_seguinte(repo, codigo):04}"
    caminho = f"{DIR_SDD}/{sdd_id}.md"
    (repo / DIR_SDD).mkdir(parents=True, exist_ok=True)
    (repo / caminho).write_text(
        montar_sdd(rascunho, sdd_id, codigo, owner, hoje, status, origens), encoding="utf-8"
    )
    registrar(repo, sdd_id, rascunho["titulo"], codigo, owner, hoje, status, versao_framework)
    return caminho


def aprovar_por_politica(repo: Path, caminho_sdd: str, framework, agora: str) -> dict:
    """Grava `approved_by` de política no front-matter da SDD e o devolve (SPEC-DTF-0032, RF08).

    O hash é o do `approval_hash.py --json` do kit; as transições são do mesmo instante.
    """
    arquivo = repo / caminho_sdd
    resultado = framework._executar("approval_hash.py", str(arquivo), "--json", cwd=repo)
    if resultado.returncode != 0:
        raise RuntimeError(f"approval_hash.py: {(resultado.stdout + resultado.stderr)[-500:]}")
    approved_by = {
        "kind": "policy",
        "actor": ATOR_DA_POLITICA,
        "at": agora,
        "content_sha256": json.loads(resultado.stdout)["content_sha256"],
        "transitions": [
            {"from": "draft", "to": "in_review", "at": agora},
            {"from": "in_review", "to": "approved", "at": agora},
        ],
    }
    bloco = (
        "approved_by:\n"
        f"  kind: {approved_by['kind']}\n"
        f"  actor: {approved_by['actor']}\n"
        f"  at: {_texto(agora)}\n"
        f"  content_sha256: {_texto(approved_by['content_sha256'])}\n"
        "  transitions:\n"
        + "".join(
            f"    - {{from: {t['from']}, to: {t['to']}, at: {_texto(t['at'])}}}\n"
            for t in approved_by["transitions"]
        )
    )
    texto = arquivo.read_text(encoding="utf-8")
    texto = re.sub(r"^status: .*$", "status: approved", texto, count=1, flags=re.MULTILINE)
    texto = re.sub(
        r"^(status: approved\n)", lambda m: m.group(1) + bloco, texto, count=1, flags=re.MULTILINE
    )
    arquivo.write_text(texto, encoding="utf-8")
    return approved_by
