"""Grava a verificação na própria SDD, no formato que o framework cobra.

A tabela de evidência e a `validation-*.md` saem do JSON do revisor, nunca do desenvolvedor.
"""

import re
from pathlib import Path

import yaml

FRONTMATTER_STATUS_RE = re.compile(r"^status: approved$", re.MULTILINE)
SECAO_EVIDENCIA_RE = re.compile(
    r"(^## Evidência de verificação.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)
CABECALHO = (
    "| # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |\n"
    "|---|---|---|---|---|---|---|\n"
)
LIMITE_CELULA = 400


def _celula(texto: str) -> str:
    limpo = " ".join(str(texto).split()).replace("|", "\\|")
    return limpo[:LIMITE_CELULA]


def _linhas(validacao: dict) -> str:
    return "".join(
        f"| {_celula(c['numero'])} | `{_celula(c['comando'])}` | {_celula(c['saida'])} | "
        f"{_celula(c['sensor'])} | {'Sim' if c['passou'] else 'Não'} | "
        f"{_celula(c['assertion'])} | {_celula(c['perfil'])} |\n"
        for c in validacao["criterios"]
    )


def registrar_evidencia(repo: Path, caminho_sdd: str, validacao: dict, base: str, head: str) -> str:
    """Passa a SDD para `implemented`. Devolve o caminho do relatório de validação."""
    if validacao["status"] != "aprovado":
        raise ValueError("só verificação aprovada vira evidência")
    arquivo = repo / caminho_sdd
    texto = arquivo.read_text(encoding="utf-8")
    sdd_id = yaml.safe_load(texto.split("---\n", 2)[1])["id"]

    secao = (
        "## Evidência de verificação (preencher antes de status `implemented`)\n\n"
        f"Verificação independente em `validation-{sdd_id}.md`. Veredito: **PASS**.\n\n"
        "**Verificador independente:** sim\n\n"
        f"{CABECALHO}{_linhas(validacao)}\n"
    )
    texto, trocas = SECAO_EVIDENCIA_RE.subn(lambda _: secao, texto, count=1)
    if trocas != 1:
        raise ValueError(f"{caminho_sdd} sem seção de evidência")
    texto, trocas = FRONTMATTER_STATUS_RE.subn("status: implemented", texto, count=1)
    if trocas != 1:
        raise ValueError(f"{caminho_sdd} não está approved")
    arquivo.write_text(texto.replace("- [ ]", "- [x]"), encoding="utf-8")

    registro = arquivo.parent / "registry.yaml"
    _atualizar_registry(registro, sdd_id)

    relatorio = arquivo.parent / f"validation-{sdd_id}.md"
    descompassos = "\n".join(f"- {d}" for d in validacao["descompassos"]) or "nenhum"
    relatorio.write_text(
        f"# Verificação — {sdd_id}\n\n"
        "- **Veredito:** PASS\n"
        f"- **Diff verificado:** {base}..{head}\n"
        "- **Verificador independente:** sim\n\n"
        f"{CABECALHO}{_linhas(validacao)}\n"
        f"## Descompassos encontrados\n\n{descompassos}\n",
        encoding="utf-8",
    )
    return str(relatorio.relative_to(repo))


def _atualizar_registry(registro: Path, sdd_id: str) -> None:
    texto = registro.read_text(encoding="utf-8")
    padrao = re.compile(rf"(- id: {re.escape(sdd_id)}\n(?:[ \t]+[^\n]*\n)*?[ \t]+status: )approved")
    texto, trocas = padrao.subn(r"\1implemented", texto, count=1)
    if trocas != 1:
        raise ValueError(f"{sdd_id} não está approved em {registro}")
    registro.write_text(texto, encoding="utf-8")
