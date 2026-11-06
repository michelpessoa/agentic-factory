"""Único ponto da fábrica que conhece o framework de rastreabilidade."""

from pathlib import Path

import yaml

from adapters.doc_traceability.arquivo import DIR_ARQUIVO, arquivar_sdd
from adapters.doc_traceability.compilador import FRONTMATTER_RE, SddInvalida, compilar_sdd
from adapters.doc_traceability.evidencia import registrar_evidencia
from adapters.doc_traceability.redacao import escrever_sdd
from adapters.doc_traceability.validadores import Framework


class FonteDocTraceability:
    """Implementa `FonteDeContrato` para SDDs do framework."""

    def __init__(self, framework: Framework | None = None):
        self._framework = framework or Framework()

    def identificador(self) -> str:
        return f"doc-traceability@{self._framework.sha()}"

    def problemas_de_entrada(self, repo: Path, caminho_sdd: str) -> list[str]:
        """Junta os validadores e o compilador numa só decisão."""
        sdd = repo / caminho_sdd
        problemas = [
            f"{r.nome}: {r.saida.strip()[-500:]}"
            for r in self._framework.validar_entrada(repo, sdd)
            if not r.ok
        ]
        try:
            compilar_sdd(sdd, repo)
        except SddInvalida as erro:
            problemas += erro.problemas
        return problemas

    def escrever_sdd(
        self,
        repo: Path,
        rascunho: dict,
        codigo: str,
        owner: str,
        hoje: str,
        status: str,
        sdd_id: str | None = None,
    ) -> str:
        return escrever_sdd(
            repo, rascunho, codigo, owner, hoje, status, self._framework.versao(), sdd_id
        )

    def compilar(self, repo: Path, caminho_sdd: str) -> dict:
        return compilar_sdd(repo / caminho_sdd, repo)

    def caminhos_historicos(self) -> tuple[str, ...]:
        return (DIR_ARQUIVO,)

    def sdds_aprovadas(self, repo: Path) -> list[str]:
        aprovadas = []
        for caminho in sorted((repo / "docs" / "sdd").glob("SDD-*.md")):
            achado = FRONTMATTER_RE.match(caminho.read_text(encoding="utf-8"))
            if achado and (yaml.safe_load(achado.group(1)) or {}).get("status") == "approved":
                aprovadas.append(str(caminho.relative_to(repo)))
        return aprovadas

    def arquivar(self, repo: Path, caminho_sdd: str, pr: int, data: str) -> bool:
        return arquivar_sdd(repo, caminho_sdd, pr, data)

    def registrar_verificacao(
        self, repo: Path, caminho_sdd: str, validacao: dict, base: str, head: str
    ) -> list[str]:
        """Devolve os problemas apontados pelo `validate_state` do framework."""
        registrar_evidencia(repo, caminho_sdd, validacao, base, head)
        resultado = self._framework.validar_estado(repo, repo / caminho_sdd)
        return [] if resultado.ok else [resultado.saida.strip()[-800:]]
