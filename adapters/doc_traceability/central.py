"""Escrita no central: rascunho de SPEC ou RFC por PR e aprovação pela review (ADR-0012).

O executor só escreve por PR `docs/<id>`. A regra de qual review vale é do `review_approval.py`
do kit; aqui só se busca a PR e as reviews, e se grava o `approved_by` que o kit devolve.
"""

import datetime
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

from adapters.doc_traceability.compilador import (
    _celulas,
    _sem_cercas_de_codigo,
    primeira_tabela,
    secao,
)
from adapters.doc_traceability.redacao import TAG, _texto
from adapters.doc_traceability.regras import Regras
from adapters.doc_traceability.validadores import Framework
from fabrica import publicacao
from fabrica.publicacao import Github

CORPO_PR = (
    "Rascunho {doc_id}, da descoberta da fábrica, em in_review.\n\n"
    'Para aprovar: review "Approve", ou review de comentário com o texto exato `Aprovado`, '
    "sobre o último commit desta PR. Mudança depois da review pede nova review.\n\n"
    "Depois da review: `uv run python -m fabrica central conferir <projeto> {doc_id}`."
)
CAMPOS_APPROVED_BY = ("kind", "actor", "at", "content_sha256", "evidence")
ESPERA_DO_HEAD_SEGUNDOS = 5
LIMITE_DO_HEAD_SEGUNDOS = 120
PARTE_1 = "# Parte 1 — Requisito (o QUÊ)"
PARTE_2 = "# Parte 2 — Desenho (o COMO e o ONDE)"
CABECALHO_RF = "| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |"
COLUNA_PROJETO = "projeto"


class EscritaRecusada(Exception):
    """A escrita no central não pode seguir. Nada foi enviado ao remoto."""


def _git(central: Path, *args: str) -> str:
    resultado = subprocess.run(
        ["git", "-C", str(central), *args], capture_output=True, text=True, check=False
    )
    if resultado.returncode != 0:
        raise publicacao.FalhaDePublicacao(f"git {args[0]}: {resultado.stderr[-500:]}")
    return resultado.stdout


def repositorio_do_central(central: Path) -> str:
    url = _git(central, "remote", "get-url", "origin").strip()
    for prefixo in ("git@github.com:", "https://github.com/"):
        if url.startswith(prefixo):
            return url.removeprefix(prefixo).removesuffix(".git")
    raise EscritaRecusada(f"remote origin de {central} não é do GitHub: {url}")


def _frontmatter(texto: str) -> dict:
    return yaml.safe_load(texto.split("---\n", 2)[1]) or {}


def _problemas_das_partes(texto: str) -> list[str]:
    sem_cercas = _sem_cercas_de_codigo(texto)
    parte_1 = re.search(r"^# Parte 1\b", sem_cercas, re.MULTILINE)
    parte_2 = re.search(r"^# Parte 2\b", sem_cercas, re.MULTILINE)
    problemas = []
    if not parte_1:
        problemas.append(f"SPEC sem a linha '{PARTE_1}' do template")
    if not parte_2:
        problemas.append(
            f"SPEC sem a linha '{PARTE_2}' do template: a SDD enxuta lê o desenho a partir dela"
        )
    if parte_1 and parte_2 and parte_2.start() < parte_1.start():
        problemas.append("SPEC com '# Parte 2' antes de '# Parte 1'")
    return problemas


def _problemas_da_tabela_rf(texto: str) -> list[str]:
    requisitos = secao(texto, "Requisitos funcionais")
    if requisitos is None:
        return []
    cabecalho = next((li for li in requisitos.splitlines() if li.startswith("|")), None)
    if cabecalho is None or _celulas(cabecalho) == _celulas(CABECALHO_RF):
        return []
    motivo = (
        "SPEC com a tabela de Requisitos funcionais fora do template: "
        f"o cabeçalho deve ser '{CABECALHO_RF}', com o critério EARS na 3ª coluna"
    )
    return [motivo]


class EscritaNoCentral:
    def __init__(self, central: Path, codigo: str, framework: Framework, github: Github):
        self.central = central
        self.codigo = codigo
        self.framework = framework
        self.github = github
        self.regras = Regras(framework.raiz)

    @property
    def _docs(self) -> Path:
        return self.central / "docs" / self.codigo

    def _ramo(self, doc_id: str) -> str:
        return f"docs/{doc_id.lower()}"

    def tipo_do_central(self, sizing: str) -> str | None:
        return self.regras.tipo_do_central(sizing)

    def _registry_de_main(self) -> str:
        _git(self.central, "fetch", "-q", "origin", "main")
        return _git(self.central, "show", f"origin/main:docs/{self.codigo}/registry.yaml")

    def _exigir_executor_fora_de_approvers(self) -> None:
        approvers = (yaml.safe_load(self._registry_de_main()) or {}).get("approvers")
        if not approvers:
            raise EscritaRecusada(
                f"approvers não declarado no registry de docs/{self.codigo}: "
                "a fábrica não abre PR nesse projeto"
            )
        login = self.github.login()
        if login in approvers:
            raise EscritaRecusada(
                f"a conta do executor {login} está em approvers de docs/{self.codigo}: "
                "o executor não pode ser aprovador"
            )

    def proximo_id(self, tipo: str) -> str:
        padrao = re.compile(rf"^{re.escape(tipo)}-{re.escape(self.codigo)}-(\d{{4}})$")
        registry = yaml.safe_load(self._registry_de_main()) or {}
        usados = [
            int(achado.group(1))
            for item in registry.get("documents") or []
            if (achado := padrao.match(str(item.get("id", ""))))
        ]
        prefixo = f"docs/{tipo.lower()}-{self.codigo.lower()}-"
        remotos = _git(self.central, "ls-remote", "--heads", "origin", f"{prefixo}*")
        for linha in remotos.splitlines():
            ramo = linha.split("refs/heads/", 1)[-1]
            numero = ramo.removeprefix(prefixo)
            if ramo.startswith(prefixo) and re.fullmatch(r"\d{4}", numero):
                usados.append(int(numero))
        return f"{tipo}-{self.codigo}-{max(usados, default=0) + 1:04}"

    def montar(self, documento: dict, owner: str, hoje: str) -> tuple[str, str]:
        tipo = documento["tipo"]
        doc_id = self.proximo_id(tipo)
        linhas = [
            f"id: {doc_id}",
            f"type: {tipo}",
            f"title: {_texto(documento['titulo'])}",
            "status: in_review",
            f"project: {_texto(self.codigo)}",
            f"owner: {_texto(owner)}",
            f"created: {_texto(hoje)}",
            f"updated: {_texto(hoje)}",
            "relates_to: []",
        ]
        if tipo == "SPEC":
            linhas += ["parent_rfc: null", "parent_adr: null"]
        linhas += [
            f"sizing: {_texto(documento['sizing'])}",
            "supersedes: null",
            "superseded_by: null",
            f"tags: [{TAG}]",
        ]
        corpo = documento["corpo"].rstrip("\n")
        return doc_id, "---\n" + "\n".join(linhas) + "\n---\n\n" + corpo + "\n"

    def problemas(self, texto: str) -> list[str]:
        dados = _frontmatter(texto)
        with tempfile.TemporaryDirectory(prefix="fabrica-documento-") as temporario:
            raiz = Path(temporario)
            registry = raiz / "docs" / self.codigo / "registry.yaml"
            registry.parent.mkdir(parents=True)
            registry.write_text(self._registry_de_main(), encoding="utf-8")
            arquivo = raiz / self.regras.pasta(dados["type"], self.codigo) / f"{dados['id']}.md"
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(texto, encoding="utf-8")
            problemas = list(self.framework.validar_documento(raiz, arquivo).problemas)
        if dados["type"] == "SPEC":
            problemas += _problemas_das_partes(texto)
            problemas += _problemas_da_tabela_rf(texto)
        return problemas

    def _exigir_clone_limpo_em_main(self) -> None:
        if _git(self.central, "status", "--porcelain").strip():
            raise EscritaRecusada(f"clone do central em {self.central} tem mudança local")
        ramo = _git(self.central, "branch", "--show-current").strip()
        if ramo != "main":
            raise EscritaRecusada(f"clone do central em {self.central} está em {ramo}, não em main")

    def _url(self) -> str:
        return _git(self.central, "remote", "get-url", "origin").strip()

    def _registrar(self, doc_id: str, tipo: str, titulo: str, caminho: str, hoje: str) -> None:
        registro = self._docs / "registry.yaml"
        texto = registro.read_text(encoding="utf-8")
        # Registry sem documentos vem como `documents: []`; a entrada nova vira item de lista.
        texto = re.sub(r"^documents: \[\]\s*$", "documents:", texto, count=1, flags=re.MULTILINE)
        if not texto.endswith("\n"):
            texto += "\n"
        dados = _frontmatter(Path(self.central / caminho).read_text(encoding="utf-8"))
        texto += (
            f"  - id: {doc_id}\n"
            f"    type: {tipo}\n"
            f"    title: {_texto(titulo)}\n"
            "    status: in_review\n"
            f"    owner: {_texto(dados['owner'])}\n"
            f'    created: "{hoje}"\n'
            f'    updated: "{hoje}"\n'
            "    relates_to: []\n"
            f'    path: "{caminho}"\n'
            f"    tags: [{TAG}]\n"
        )
        registro.write_text(texto, encoding="utf-8")

    def _validar_registry(self) -> list[str]:
        resultado = self.framework.validar_registry(self.central, self._docs)
        return [] if resultado.ok else list(resultado.problemas)

    def abrir_pr(self, doc_id: str, tipo: str, texto: str, titulo: str) -> int:
        self._exigir_executor_fora_de_approvers()
        self._exigir_clone_limpo_em_main()
        ramo = self._ramo(doc_id)
        _git(self.central, "fetch", "-q", "origin", "main")
        if _git(self.central, "ls-remote", "--heads", "origin", ramo).strip():
            raise EscritaRecusada(
                f"{ramo} já existe no central: retome a descoberta para pegar o id seguinte"
            )
        try:
            _git(self.central, "switch", "-q", "-C", ramo, "origin/main")
            caminho = f"{self.regras.pasta(tipo, self.codigo)}/{doc_id}.md"
            arquivo = self.central / caminho
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(texto, encoding="utf-8")
            self._registrar(doc_id, tipo, titulo, caminho, str(_frontmatter(texto)["created"]))
            self.framework.gerar_registry_md(self._docs)
            problemas = self._validar_registry()
            if problemas:
                raise EscritaRecusada(f"registry_tools validate: {'; '.join(problemas)}")
            publicacao.commit(
                self.central,
                f"docs({self.codigo}): {doc_id} em in_review, da descoberta da fábrica",
            )
            publicacao.enviar_ramo_documento(self.central, self._url(), ramo)
            corpo = CORPO_PR.format(doc_id=doc_id) + publicacao.RODAPE_PR
            return self.github.abrir_pr_documento(
                ramo, f"docs({self.codigo}): {doc_id} — {titulo}", corpo
            )
        finally:
            _git(self.central, "switch", "-q", "main")

    def prs_da_fabrica(self) -> list[tuple[str, int]]:
        """Pares (id, número) das PRs `docs/<id>` abertas no central pela conta do executor com a
        etiqueta. O número vai até o aviso do vigia (SDD-FAB-0010, RF02)."""
        abertas = json.loads(
            self.github._gh("api", f"repos/{self.github.repo}/pulls?state=open&per_page=100")
        )
        login = self.github.login()
        ids = []
        for pr in abertas:
            ramo = pr["head"]["ref"]
            etiquetas = {e["name"] for e in pr.get("labels") or []}
            if (
                ramo.startswith("docs/")
                and pr["user"]["login"] == login
                and publicacao.ETIQUETA_PR in etiquetas
            ):
                ids.append((ramo.removeprefix("docs/").upper(), pr["number"]))
        return ids

    def _caminho_no_registry(self, raiz: Path, doc_id: str) -> str:
        registry = yaml.safe_load(
            (raiz / "docs" / self.codigo / "registry.yaml").read_text(encoding="utf-8")
        )
        for item in registry.get("documents") or []:
            if item.get("id") == doc_id:
                return item["path"]
        raise EscritaRecusada(f"{doc_id} não está no registry de {self._ramo(doc_id)}")

    def conferir(self, doc_id: str) -> dict:
        self._exigir_executor_fora_de_approvers()
        ramo = self._ramo(doc_id)
        pr = self.github.pr_aberta_do_ramo(ramo)
        if pr is None:
            raise EscritaRecusada(f"nenhuma PR aberta para {ramo}")
        head = pr["head"]["sha"]
        _git(self.central, "fetch", "-q", "origin", ramo)
        with tempfile.TemporaryDirectory(prefix="fabrica-conferir-") as temporario:
            arvore = Path(temporario) / "head"
            _git(self.central, "worktree", "add", "--detach", str(arvore), head)
            try:
                documento = arvore / self._caminho_no_registry(arvore, doc_id)
                dados = _frontmatter(documento.read_text(encoding="utf-8"))
                if dados.get("status") == "approved" and dados.get("approved_by"):
                    return {
                        "schema": "dtf.review-approval/1",
                        "documento": doc_id,
                        "valida": True,
                        "motivos": [],
                        "head": head,
                        "approved_by": dados["approved_by"],
                    }
                reviews = Path(temporario) / "reviews.json"
                reviews.write_text(
                    json.dumps(self.github.reviews(pr["number"]), ensure_ascii=False),
                    encoding="utf-8",
                )
                return self.framework.decidir_review(documento, reviews, head, pr["html_url"])
            finally:
                _git(self.central, "worktree", "remove", "--force", str(arvore))

    def _aprovar_texto(self, texto: str, approved_by: dict, hoje: str) -> str:
        bloco = "approved_by:\n" + "".join(
            f"  {campo}: {_texto(str(approved_by[campo]))}\n" for campo in CAMPOS_APPROVED_BY
        )
        texto = re.sub(
            r"^status: in_review$", "status: approved", texto, count=1, flags=re.MULTILINE
        )
        texto = re.sub(
            r"^updated: .*$", f"updated: {_texto(hoje)}", texto, count=1, flags=re.MULTILINE
        )
        return re.sub(
            r"^(sizing: .*\n)", lambda m: m.group(1) + bloco, texto, count=1, flags=re.MULTILINE
        )

    def _aprovar_no_registry(self, doc_id: str, hoje: str) -> None:
        registro = self._docs / "registry.yaml"
        texto = registro.read_text(encoding="utf-8")
        entrada = rf"(- id: {re.escape(doc_id)}\n(?:[ \t]+[^\n]*\n)*?[ \t]+"
        texto = re.sub(entrada + r"status: )in_review", r"\1approved", texto, count=1)
        texto = re.sub(entrada + r"updated: ).*", rf'\g<1>"{hoje}"', texto, count=1)
        registro.write_text(texto, encoding="utf-8")

    def _esperar_head(self, ramo: str, dormir) -> int:
        """Espera o GitHub reportar o commit enviado como head da PR; devolve o número dela.

        Logo após o push, o GitHub ainda reporta o head anterior, com os checks dele, e
        `esperar_checks` lê o `statusCheckRollup` desse head.
        """
        enviado = _git(self.central, "rev-parse", "HEAD").strip()
        esperado = 0
        while True:
            pr = self.github.pr_aberta_do_ramo(ramo)
            if pr is None:
                raise EscritaRecusada(f"nenhuma PR aberta para {ramo}")
            if pr["head"]["sha"] == enviado:
                return pr["number"]
            if esperado >= LIMITE_DO_HEAD_SEGUNDOS:
                raise EscritaRecusada(
                    f"head da PR #{pr['number']} segue em {pr['head']['sha']}, não em {enviado}, "
                    f"depois de {LIMITE_DO_HEAD_SEGUNDOS}s: rode conferir de novo"
                )
            dormir(ESPERA_DO_HEAD_SEGUNDOS)
            esperado += ESPERA_DO_HEAD_SEGUNDOS

    def integrar(self, doc_id: str, decisao: dict, dormir=time.sleep) -> str:
        if not decisao.get("valida"):
            raise EscritaRecusada("aprovação inválida")
        ramo = self._ramo(doc_id)
        self._exigir_clone_limpo_em_main()
        try:
            _git(self.central, "fetch", "-q", "origin", ramo)
            _git(self.central, "switch", "-q", "-C", ramo, f"origin/{ramo}")
            documento = self.central / self._caminho_no_registry(self.central, doc_id)
            texto = documento.read_text(encoding="utf-8")
            if _frontmatter(texto).get("status") == "in_review":
                sha = _git(self.central, "rev-parse", "HEAD").strip()
                if sha != decisao["head"]:
                    raise EscritaRecusada(f"head de {ramo} mudou para {sha}: rode conferir de novo")
                hoje = datetime.datetime.now(datetime.UTC).date().isoformat()
                approved_by = decisao["approved_by"]
                documento.write_text(
                    self._aprovar_texto(texto, approved_by, hoje), encoding="utf-8"
                )
                self._aprovar_no_registry(doc_id, hoje)
                self.framework.gerar_registry_md(self._docs)
                estado = self.framework.validar_estado(self.central, documento)
                problemas = ([] if estado.ok else list(estado.problemas)) + self._validar_registry()
                if problemas:
                    _git(self.central, "reset", "-q", "--hard", f"origin/{ramo}")
                    raise EscritaRecusada(f"validação antes do push: {'; '.join(problemas)}")
                publicacao.commit(
                    self.central,
                    f"docs({self.codigo}): {doc_id} approved por review de {approved_by['actor']}",
                )
                publicacao.enviar_ramo_documento(self.central, self._url(), ramo)
            numero = self._esperar_head(ramo, dormir)
            situacao, detalhe = self.github.esperar_checks(numero)
            if situacao not in {"passou", "sem_checks"}:
                raise EscritaRecusada(f"checks da PR #{numero}: {situacao} {detalhe}")
            sha = self.github.fazer_merge_de_documento(numero)
        finally:
            _git(self.central, "switch", "-q", "main")
        _git(self.central, "pull", "-q", "--ff-only", "origin", "main")
        return sha


def _projetos_da_spec(texto: str) -> set[str]:
    """Códigos da coluna Projeto da tabela de Requisitos funcionais; vazio sem a coluna."""
    tabela = primeira_tabela(secao(texto, "Requisitos funcionais"))
    indice = None if tabela is None else tabela.indice(COLUNA_PROJETO)
    if indice is None:
        return set()
    return {
        codigo.strip()
        for linha in tabela.linhas
        if indice < len(linha)
        for codigo in linha[indice].split(",")
        if codigo.strip()
    }


class LeituraDoCentral:
    """SPECs aprovadas por humano em `origin/main` do central, para o vigia compilar (RF05)."""

    def __init__(self, central: Path, codigo: str, framework: Framework):
        self.central = central
        self.codigo = codigo
        self.framework = framework
        self.recusadas: dict[str, list[str]] = {}
        self._caminhos: dict[str, str] = {}

    def specs_aprovadas(self) -> list[tuple[str, str]]:
        """Pares (id, content_sha256), depois de `git fetch` em `origin/main`.

        SPEC com `validate_state.py` vermelho fica fora, com os motivos em `recusadas`.
        """
        _git(self.central, "fetch", "-q", "origin", "main")
        self.recusadas = {}
        aprovadas = []
        with tempfile.TemporaryDirectory(prefix="fabrica-leitura-") as temporario:
            arvore = Path(temporario) / "main"
            _git(self.central, "worktree", "add", "--detach", str(arvore), "origin/main")
            try:
                for registry in sorted((arvore / "docs").glob("*/registry.yaml")):
                    pasta = registry.parent.name
                    dados = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
                    for item in dados.get("documents") or []:
                        if item.get("type") != "SPEC" or item.get("status") != "approved":
                            continue
                        arquivo = arvore / str(item.get("path", ""))
                        if not arquivo.is_file():
                            continue
                        texto = arquivo.read_text(encoding="utf-8")
                        frente = _frontmatter(texto)
                        approved_by = frente.get("approved_by") or {}
                        if approved_by.get("kind") != "human":
                            continue
                        if pasta != self.codigo and self.codigo not in _projetos_da_spec(texto):
                            continue
                        estado = self.framework.validar_estado(arvore, arquivo)
                        if not estado.ok:
                            self.recusadas[item["id"]] = list(estado.problemas)
                            continue
                        self._caminhos[item["id"]] = item["path"]
                        aprovadas.append((item["id"], str(approved_by.get("content_sha256"))))
            finally:
                _git(self.central, "worktree", "remove", "--force", str(arvore))
        return aprovadas

    def url(self, doc_id: str) -> str:
        """A mesma url de `source_docs`: o arquivo em `main` do central."""
        base = _git(self.central, "remote", "get-url", "origin").strip()
        base = base.replace("git@github.com:", "https://github.com/").removesuffix(".git")
        return f"{base}/blob/main/{self._caminhos[doc_id]}"
