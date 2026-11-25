"""Único ponto da fábrica que conhece o framework de rastreabilidade."""

import re
import subprocess
import tempfile
from pathlib import Path

import yaml

from adapters.doc_traceability.arquivo import DIR_ARQUIVO, arquivar_sdd
from adapters.doc_traceability.central import (
    EscritaNoCentral,
    EscritaRecusada,
    _projetos_da_spec,
    repositorio_do_central,
)
from adapters.doc_traceability.compilador import FRONTMATTER_RE, SddInvalida, compilar_sdd
from adapters.doc_traceability.evidencia import registrar_evidencia
from adapters.doc_traceability.redacao import aprovar_por_politica, escrever_sdd, formato_da_sdd
from adapters.doc_traceability.regras import Regras
from adapters.doc_traceability.validadores import Framework, ResultadoValidador, VersaoDivergente

__all__ = [
    "EscritaNoCentral",
    "EscritaRecusada",
    "FonteDocTraceability",
    "OrigemInvalida",
    "VersaoDivergente",
    "repositorio_do_central",
]


ID_DE_ORIGEM_RE = re.compile(r"^([A-Z]+)-([A-Z][A-Z0-9]*)-(\d{4})$")


def _ids_de_origem(sdd: Path) -> list[str]:
    """Ids de `source_docs` da SDD; vazio sem arquivo ou sem front-matter."""
    achado = FRONTMATTER_RE.match(sdd.read_text(encoding="utf-8")) if sdd.is_file() else None
    frente = (yaml.safe_load(achado.group(1)) or {}) if achado else {}
    return [str(d.get("id", "")) for d in frente.get("source_docs") or [] if isinstance(d, dict)]


class OrigemInvalida(Exception):
    """O id pedido como origem da descoberta não é SPEC ou ADR approved no central."""


class FonteDocTraceability:
    """Implementa `FonteDeContrato` para SDDs do framework."""

    def __init__(
        self, framework: Framework | None = None, central: Path | None = None, codigo: str = ""
    ):
        self._framework = framework or Framework()
        self._central = central
        self._codigo = codigo
        self._regras = Regras(self._framework.raiz)

    def exigir_versao(self, exigida: str) -> None:
        self._framework.exigir_versao(exigida)
        self._framework.exigir_central(self._central or Path(""), exigida)

    def identificador(self) -> str:
        return f"doc-traceability@{self._framework.sha()}"

    def problemas_de_entrada(self, repo: Path, caminho_sdd: str) -> list[str]:
        """Junta os validadores e o compilador numa só decisão."""
        sdd = repo / caminho_sdd
        pasta, problemas_de_pasta = self.pasta_das_origens(_ids_de_origem(sdd))
        if problemas_de_pasta and pasta != self._codigo:
            return problemas_de_pasta
        docs_central = (self._central or Path("")) / "docs" / pasta
        problemas = [
            f"{r.nome}: {mensagem}"
            for r in self._framework.validar_entrada(repo, sdd, docs_central)
            if not r.ok
            for mensagem in r.problemas
        ]
        problemas += self._problemas_de_sizing(sdd)
        try:
            compilar_sdd(sdd, repo, self._textos_de_origem(sdd))
        except SddInvalida as erro:
            problemas += erro.problemas
        return problemas

    def formato_da_sdd(self, repo: Path, origens) -> str:
        return formato_da_sdd(repo, origens, self._framework.versao())

    def problemas_de_redacao(self, repo: Path, caminho_sdd: str) -> list[str]:
        """`validate_doc.py` sobre a SDD como ela está escrita, em draft: confere a SDD enxuta."""
        resultado = self._framework.validar_documento(repo, repo / caminho_sdd)
        return [] if resultado.ok else [f"{resultado.nome}: {m}" for m in resultado.problemas]

    def fidelidade_a_origem(self, repo: Path, caminho_sdd: str) -> tuple[bool, dict]:
        """`check_source_docs.py` contra a pasta das origens em `origin/main` do central, depois
        de `git fetch` (SPEC-DTF-0033, RF01; SPEC-DTF-0034, RF06). Levanta `CalledProcessError`
        se o `fetch` falhar. Problema de pasta das origens reprova sem rodar o kit."""
        central = self._central or Path("")
        subprocess.run(
            ["git", "-C", str(central), "fetch", "-q", "origin", "main"],
            capture_output=True,
            text=True,
            check=True,
        )
        with tempfile.TemporaryDirectory(prefix="fabrica-fidelidade-") as temporario:
            arvore = Path(temporario) / "main"
            subprocess.run(
                ["git", "-C", str(central), "worktree", "add", "-q", "--detach", str(arvore),
                 "origin/main"],
                capture_output=True,
                text=True,
                check=True,
            )  # fmt: skip
            try:
                em_main = FonteDocTraceability(self._framework, arvore, self._codigo)
                pasta, problemas = em_main.pasta_das_origens(_ids_de_origem(repo / caminho_sdd))
                if problemas and pasta != self._codigo:
                    resultado = ResultadoValidador(
                        "check_source_docs.py", False, "\n".join(problemas), tuple(problemas)
                    )
                else:
                    resultado = self._framework._rodar(
                        "check_source_docs.py",
                        str(repo / caminho_sdd),
                        str(arvore / "docs" / pasta),
                        cwd=repo,
                    )
            finally:
                subprocess.run(
                    ["git", "-C", str(central), "worktree", "remove", "--force", str(arvore)],
                    capture_output=True,
                    check=False,
                )
        script = self._framework.scripts / "check_source_docs.py"
        linha = {
            "numero": "Fidelidade à origem (check_source_docs)",
            "comando": f"python3 {script} {caminho_sdd} {central / 'docs' / (pasta or self._codigo)} "
            "(em origin/main)",
            "saida": resultado.saida,
            "sensor": "sem teste automatizado (script do kit)",
            "passou": resultado.ok,
            "assertion": "n/a",
            "perfil": "n/a",
        }
        return resultado.ok, linha

    def textos_de_origem(self, repo: Path, caminho_sdd: str) -> dict[str, str]:
        return self._textos_de_origem(repo / caminho_sdd)

    def _textos_de_origem(self, sdd: Path) -> dict[str, str]:
        """Texto de cada `source_docs` no clone do central, pelo `path` do registry, sem olhar status."""
        if self._central is None or not sdd.is_file():
            return {}
        achado = FRONTMATTER_RE.match(sdd.read_text(encoding="utf-8"))
        if not achado:
            return {}
        frente = yaml.safe_load(achado.group(1)) or {}
        registry = self._registry_central(self.pasta_das_origens(_ids_de_origem(sdd))[0])
        textos = {}
        for doc in frente.get("source_docs") or []:
            doc_id = doc.get("id") if isinstance(doc, dict) else None
            entrada = registry.get(doc_id)
            arquivo = self._central / entrada["path"] if entrada and entrada.get("path") else None
            if arquivo is not None and arquivo.is_file():
                textos[doc_id] = arquivo.read_text(encoding="utf-8")
        return textos

    def pasta_das_origens(self, ids: list[str]) -> tuple[str, list[str]]:
        """Pasta do central comum aos ids de origem e os problemas (SPEC-DTF-0034, RF01 a RF03).

        Sem ids, a pasta é a do projeto. De outra pasta, só vale SPEC que declara o projeto na
        coluna Projeto, ou ADR que é `parent_adr` de uma SPEC aceita assim.
        """
        if not ids:
            return self._codigo, []
        partes = {doc_id: ID_DE_ORIGEM_RE.match(doc_id) for doc_id in ids}
        fora = [
            doc_id
            for doc_id, parte in partes.items()
            if parte is None or (parte[2] != self._codigo and parte[1] not in {"SPEC", "ADR"})
        ]
        if fora:
            return "", [
                f"{doc_id} está fora do formato SPEC-<CODE>-<SEQ4> ou ADR-<CODE>-<SEQ4>"
                for doc_id in fora
            ]
        pastas = sorted({parte[2] for parte in partes.values()})
        if len(pastas) > 1:
            return "", [f"source_docs em mais de uma pasta do central: {', '.join(pastas)}"]
        pasta = pastas[0]
        registry = self._registry_central(pasta)
        problemas = [
            f"{doc_id} não está no registry do central em docs/{pasta}"
            for doc_id in ids
            if doc_id not in registry
        ]
        if problemas or pasta == self._codigo:
            return pasta, problemas
        adrs_aceitas = set()
        for doc_id in ids:
            if partes[doc_id][1] != "SPEC":
                continue
            arquivo = (self._central or Path("")) / registry[doc_id]["path"]
            texto = arquivo.read_text(encoding="utf-8") if arquivo.is_file() else ""
            if self._codigo in _projetos_da_spec(texto):
                adrs_aceitas.add(self._frontmatter_central(registry[doc_id]).get("parent_adr"))
            else:
                problemas.append(
                    f"{doc_id} é de docs/{pasta}/ e não declara {self._codigo} na coluna Projeto"
                )
        problemas += [
            f"{doc_id} é de docs/{pasta}/ e não é parent_adr de SPEC aceita nas origens"
            for doc_id in ids
            if partes[doc_id][1] == "ADR" and doc_id not in adrs_aceitas
        ]
        return pasta, problemas

    def _registry_central(self, pasta: str | None = None) -> dict:
        arquivo = (self._central or Path("")) / "docs" / (pasta or self._codigo) / "registry.yaml"
        if not arquivo.is_file():
            return {}
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        return {d["id"]: d for d in dados.get("documents") or []}

    def _frontmatter_central(self, entrada: dict) -> dict:
        arquivo = (self._central or Path("")) / entrada["path"]
        if not arquivo.is_file():
            return {}
        achado = FRONTMATTER_RE.match(arquivo.read_text(encoding="utf-8"))
        return (yaml.safe_load(achado.group(1)) or {}) if achado else {}

    def _problemas_de_sizing(self, sdd: Path) -> list[str]:
        achado = FRONTMATTER_RE.match(sdd.read_text(encoding="utf-8")) if sdd.is_file() else None
        frente = (yaml.safe_load(achado.group(1)) or {}) if achado else {}
        sizing = frente.get("sizing")
        niveis = self._regras.niveis()
        if sizing not in niveis:
            return [f"sizing {sizing!r} não é nível do framework: use {', '.join(niveis)}"]
        ids = [str(d.get("id", "")) for d in frente.get("source_docs") or [] if isinstance(d, dict)]
        specs = [i for i in ids if i.startswith("SPEC-")]
        if "SPEC" in self._regras.documentos(sizing) and not specs:
            return [f"sizing {sizing} exige SPEC approved em source_docs"]
        problemas = []
        registry = self._registry_central(self.pasta_das_origens(ids)[0]) if specs else {}
        for spec_id in specs:
            if spec_id not in registry:
                continue
            spec = self._frontmatter_central(registry[spec_id])
            spec_sizing = spec.get("sizing")
            if spec_sizing != sizing:
                problemas.append(f"sizing {sizing} difere do sizing {spec_sizing} da {spec_id}")
            adr_id = spec.get("parent_adr")
            if adr_id and adr_id not in ids:
                problemas.append(f"a {spec_id} vem da {adr_id}, que falta em source_docs")
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
        origens=(),
    ) -> str:
        return escrever_sdd(
            repo, rascunho, codigo, owner, hoje, status, self._framework.versao(), sdd_id, origens
        )

    def origem(self, doc_id: str) -> dict:
        """SPEC ou ADR approved do central, com a url e o texto que a descoberta usa."""
        central = self._central or Path("")
        pasta, problemas = self.pasta_das_origens([doc_id])
        if problemas:
            raise OrigemInvalida("; ".join(problemas))
        entrada = self._registry_central(pasta)[doc_id]
        tipo, status = entrada.get("type"), entrada.get("status")
        if tipo not in {"SPEC", "ADR"}:
            raise OrigemInvalida(f"{doc_id} é {tipo}: a origem da descoberta é SPEC ou ADR")
        if status != "approved":
            raise OrigemInvalida(f"{doc_id} está {status}: a origem precisa estar approved")
        base = subprocess.run(
            ["git", "-C", str(central), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        base = base.replace("git@github.com:", "https://github.com/").removesuffix(".git")
        return {
            "id": doc_id,
            "url": f"{base}/blob/main/{entrada['path']}",
            "tipo": tipo,
            "titulo": entrada.get("title"),
            "sizing": self._frontmatter_central(entrada).get("sizing"),
            "texto": (central / entrada["path"]).read_text(encoding="utf-8"),
        }

    def compilar(self, repo: Path, caminho_sdd: str) -> dict:
        sdd = repo / caminho_sdd
        return compilar_sdd(sdd, repo, self._textos_de_origem(sdd))

    def caminhos_historicos(self) -> tuple[str, ...]:
        return (DIR_ARQUIVO,)

    def sdds_aprovadas(self, repo: Path) -> list[str]:
        aprovadas = []
        for caminho in sorted((repo / "docs" / "sdd").glob("SDD-*.md")):
            achado = FRONTMATTER_RE.match(caminho.read_text(encoding="utf-8"))
            if achado and (yaml.safe_load(achado.group(1)) or {}).get("status") == "approved":
                aprovadas.append(str(caminho.relative_to(repo)))
        return aprovadas

    def sdd_com_origem(self, repo: Path, spec_id: str) -> str | None:
        """SDD da base com a SPEC em `source_docs` (SPEC-DTF-0032, RF06); None se não houver."""
        for caminho in sorted((repo / "docs" / "sdd").glob("SDD-*.md")):
            achado = FRONTMATTER_RE.match(caminho.read_text(encoding="utf-8"))
            frente = (yaml.safe_load(achado.group(1)) or {}) if achado else {}
            ids = [d.get("id") for d in frente.get("source_docs") or [] if isinstance(d, dict)]
            if spec_id in ids:
                return str(caminho.relative_to(repo))
        return None

    def aprovar_por_politica(self, repo: Path, caminho_sdd: str, agora: str) -> dict:
        """A descoberta não conhece o kit: o hash e a gravação ficam na redação."""
        return aprovar_por_politica(repo, caminho_sdd, self._framework, agora)

    def aprovacao_por_politica(self, repo: Path, caminho_sdd: str) -> tuple[bool, list[str]]:
        """(True, []) com kind policy e validate_state verde; (False, motivos) com kind policy e
        problema; (False, []) sem kind policy (SPEC-DTF-0032, RF09)."""
        arquivo = repo / caminho_sdd
        achado = (
            FRONTMATTER_RE.match(arquivo.read_text(encoding="utf-8")) if arquivo.is_file() else None
        )
        frente = (yaml.safe_load(achado.group(1)) or {}) if achado else {}
        if (frente.get("approved_by") or {}).get("kind") != "policy":
            return False, []
        estado = self._framework.validar_estado(repo, arquivo)
        return (True, []) if estado.ok else (False, list(estado.problemas))

    def arquivar(self, repo: Path, caminho_sdd: str, pr: int, data: str) -> bool:
        return arquivar_sdd(repo, caminho_sdd, pr, data)

    def registrar_verificacao(
        self,
        repo: Path,
        caminho_sdd: str,
        validacao: dict,
        base: str,
        head: str,
        linhas_extras: list[dict] = (),
    ) -> list[str]:
        """Devolve os problemas apontados pelo `validate_state` do framework."""
        achado = FRONTMATTER_RE.match((repo / caminho_sdd).read_text(encoding="utf-8"))
        status = ((yaml.safe_load(achado.group(1)) or {}) if achado else {}).get("status")
        if not self._regras.transicao_permitida(status, "implemented"):
            return [f"o framework não permite {status} → implemented"]
        registrar_evidencia(repo, caminho_sdd, validacao, base, head, linhas_extras)
        resultado = self._framework.validar_estado(repo, repo / caminho_sdd)
        return [] if resultado.ok else list(resultado.problemas)
