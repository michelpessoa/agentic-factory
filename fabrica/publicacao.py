"""Tudo o que escreve no GitHub. Só este módulo usa a credencial da fábrica.

Limites deste módulo: push só em `feature/*` e `release/*`; merge só com destino `develop`.
Não existe caminho de merge em `main`: esse merge é do humano. A única escrita em `develop` fora
de PR é o fast-forward depois da release, que não traz conteúdo novo.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from fabrica.versao import proxima_versao

RAMO_PUBLICAVEL = re.compile(r"^(feature|release)/[A-Za-z0-9._/-]+$")
RAMO_RELEASE = re.compile(r"^release/(?P<versao>\d+\.\d+\.\d+)$")
BASE_DE_MERGE_PERMITIDA = "develop"
APROVADOS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
PENDENTES = {"", "PENDING", "EXPECTED"}
LIMITE_CORPO_PR = 60000
RODAPE_COMMIT = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
RODAPE_PR = "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
GIT_SEM_HOOKS = [
    "git",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "user.name=Fábrica Agêntica",
    "-c",
    "user.email=fabrica@localhost",
]


class PublicacaoRecusada(Exception):
    """A fábrica tentou algo fora dos seus limites. Nunca deve ser contornado."""


class FalhaDePublicacao(Exception):
    pass


def _rodar(comando: list[str], cwd: Path | None = None) -> str:
    resultado = subprocess.run(comando, cwd=cwd, capture_output=True, text=True, check=False)
    if resultado.returncode != 0:
        raise FalhaDePublicacao(f"{' '.join(comando[:3])}: {resultado.stderr[-500:]}")
    return resultado.stdout


def exigir_ramo_publicavel(ramo: str) -> None:
    if not RAMO_PUBLICAVEL.match(ramo):
        raise PublicacaoRecusada(f"push recusado para o ramo {ramo!r}")


def commit(repo: Path, mensagem: str) -> str:
    _rodar([*GIT_SEM_HOOKS, "-C", str(repo), "add", "-A"])
    _rodar([*GIT_SEM_HOOKS, "-C", str(repo), "commit", "-q", "-m", mensagem + RODAPE_COMMIT])
    return _rodar(["git", "-C", str(repo), "rev-parse", "HEAD"]).strip()


def enviar_ramo(repo: Path, url: str, ramo: str) -> None:
    exigir_ramo_publicavel(ramo)
    _rodar([*GIT_SEM_HOOKS, "-C", str(repo), "push", "--quiet", url, f"HEAD:refs/heads/{ramo}"])


def montar_corpo_pr(resumo: str, sdd_texto: str, sha_sdd: str, caminho_sdd: str, repo: str) -> str:
    """Corpo com a SDD completa; acima do limite do GitHub, corta e aponta o arquivo."""
    cabecalho = f"{resumo}\n\n<details><summary>SDD completa</summary>\n\n"
    fim = f"\n\n</details>{RODAPE_PR}"
    disponivel = LIMITE_CORPO_PR - len(cabecalho) - len(fim) - 200
    if len(sdd_texto) > disponivel:
        link = f"https://github.com/{repo}/blob/{sha_sdd}/{caminho_sdd}"
        sdd_texto = f"{sdd_texto[:disponivel]}\n\n**SDD cortada. Completa em:** {link}"
    return cabecalho + sdd_texto + fim


class Github:
    """Operações via `gh`, sempre com o repositório explícito."""

    def __init__(self, repo: str, espera_segundos: int = 20, tempo_maximo_segundos: int = 1800):
        self.repo = repo
        self._espera = espera_segundos
        self._tempo_maximo = tempo_maximo_segundos

    def _gh(self, *args: str) -> str:
        env = {
            "PATH": os.environ["PATH"],
            "HOME": os.environ.get("HOME", ""),
            "GH_PROMPT_DISABLED": "1",
        }
        resultado = subprocess.run(
            ["gh", *args], capture_output=True, text=True, env=env, check=False
        )
        if resultado.returncode != 0:
            raise FalhaDePublicacao(
                f"gh {args[0]} {args[1] if len(args) > 1 else ''}: {resultado.stderr[-500:]}"
            )
        return resultado.stdout

    def quem_mergeou_o_commit(self, sha: str) -> str | None:
        """Quem fez o merge da PR que levou este commit à base. Sem PR, None."""
        saida = self._gh("api", f"repos/{self.repo}/commits/{sha}/pulls")
        for pr in json.loads(saida):
            if pr.get("merged_at"):
                detalhe = json.loads(self._gh("api", f"repos/{self.repo}/pulls/{pr['number']}"))
                return (detalhe.get("merged_by") or {}).get("login")
        return None

    def abrir_pr(self, ramo: str, base: str, titulo: str, corpo: str) -> int:
        existentes = json.loads(
            self._gh(
                "pr", "list", "-R", self.repo, "--head", ramo, "--state", "open", "--json", "number"
            )
        )
        if existentes:
            return existentes[0]["number"]
        with tempfile.NamedTemporaryFile("w", suffix=".md") as arquivo:
            arquivo.write(corpo)
            arquivo.flush()
            url = self._gh(
                "pr",
                "create",
                "-R",
                self.repo,
                "--head",
                ramo,
                "--base",
                base,
                "--title",
                titulo,
                "--body-file",
                arquivo.name,
            ).strip()
        return int(url.rsplit("/", 1)[-1])

    def comentar(self, numero: int, texto: str) -> None:
        self._gh("api", f"repos/{self.repo}/issues/{numero}/comments", "-f", f"body={texto}")

    def _pr(self, numero: int, campos: str) -> dict:
        return json.loads(self._gh("pr", "view", str(numero), "-R", self.repo, "--json", campos))

    def checks(self, numero: int) -> tuple[str, str]:
        """Devolve ('passou' | 'falhou' | 'pendente' | 'sem_checks', detalhe)."""
        itens = self._pr(numero, "statusCheckRollup")["statusCheckRollup"]
        if not itens:
            return "sem_checks", ""
        falhos, pendentes = [], False
        for item in itens:
            nome = item.get("name") or item.get("context") or "check"
            # Workflows trazem status e conclusion; status de commit traz só state.
            resultado = item.get("conclusion") or item.get("state") or ""
            concluido = (
                item.get("status", "COMPLETED") == "COMPLETED" and resultado not in PENDENTES
            )
            if not concluido:
                pendentes = True
            elif resultado not in APROVADOS:
                falhos.append(nome)
        if falhos:
            return "falhou", ", ".join(falhos)
        return ("pendente", "") if pendentes else ("passou", "")

    def esperar_checks(self, numero: int, dormir=time.sleep) -> tuple[str, str]:
        decorrido = 0
        while decorrido <= self._tempo_maximo:
            situacao, detalhe = self.checks(numero)
            sem_checks_cedo = situacao == "sem_checks" and decorrido < 120
            if situacao not in {"pendente"} and not sem_checks_cedo:
                return situacao, detalhe
            dormir(self._espera)
            decorrido += self._espera
        return "pendente", "tempo máximo de espera do CI"

    def fazer_merge_em_develop(self, numero: int) -> str:
        """O único merge da fábrica. A base é lida do GitHub, não informada por quem chama."""
        pr = self._pr(numero, "baseRefName,headRefOid,state")
        if pr["baseRefName"] != BASE_DE_MERGE_PERMITIDA:
            raise PublicacaoRecusada(f"merge recusado com destino {pr['baseRefName']!r}")
        if pr["state"] == "MERGED":
            return pr["headRefOid"]
        self._gh(
            "pr",
            "merge",
            str(numero),
            "-R",
            self.repo,
            "--merge",
            "--match-head-commit",
            pr["headRefOid"],
        )
        return pr["headRefOid"]

    def release_aberta(self, principal: str) -> tuple[int, str] | None:
        abertas = json.loads(
            self._gh(
                "pr",
                "list",
                "-R",
                self.repo,
                "--base",
                principal,
                "--state",
                "open",
                "--json",
                "number,headRefName",
            )
        )
        for pr in abertas:
            if RAMO_RELEASE.match(pr["headRefName"]):
                return pr["number"], pr["headRefName"]
        return None

    def fechar_pr(self, numero: int, comentario: str) -> None:
        self._gh("pr", "close", str(numero), "-R", self.repo, "--comment", comentario)


def _ja_em(repo: Path, ref: str, destino: str) -> bool:
    """`ref` existe e já está contido em `destino`."""
    existe = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        check=False,
    )
    if existe.returncode != 0:
        return False
    contido = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ref, destino], check=False
    )
    return contido.returncode == 0


def preparar_release(github: Github, url: str, base: str, principal: str) -> tuple[int, str]:
    """Abre ou atualiza a PR de release. Só o humano faz o merge dela em `principal`."""
    with tempfile.TemporaryDirectory(prefix="fabrica-release-") as temporario:
        repo = Path(temporario) / "repo"
        _rodar([*GIT_SEM_HOOKS, "clone", "--quiet", "--no-checkout", url, str(repo)])
        _rodar([*GIT_SEM_HOOKS, "-C", str(repo), "fetch", "--quiet", "--tags"])
        tag = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "describe",
                "--tags",
                "--abbrev=0",
                "--match",
                "v*",
                f"origin/{principal}",
            ],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        faixa = f"origin/{principal}..origin/{base}"
        mensagens = _rodar(
            ["git", "-C", str(repo), "log", "--no-merges", "--format=%B%x00", faixa]
        ).split("\0")
        mensagens = [m.strip() for m in mensagens if m.strip()]
        if not mensagens:
            raise FalhaDePublicacao("nada novo em develop para a release")
        versao = proxima_versao(tag or None, mensagens)
        ramo = f"release/{versao}"
        exigir_ramo_publicavel(ramo)
        if _ja_em(repo, f"origin/{ramo}", f"origin/{principal}"):
            # Sem a tag, a conta repetiria o número e o ramo já mergeado andaria para a frente.
            raise FalhaDePublicacao(f"release {versao} já está em {principal}: rode a pós-release")
        aberta = github.release_aberta(principal)
        if aberta and aberta[1] != ramo:
            github.fechar_pr(aberta[0], f"Substituída pela release {versao}.")
        _rodar(
            [
                *GIT_SEM_HOOKS,
                "-C",
                str(repo),
                "push",
                "--quiet",
                "origin",
                f"origin/{base}:refs/heads/{ramo}",
            ]
        )
        assuntos = "\n".join(f"- {m.splitlines()[0]}" for m in mensagens)
        corpo = (
            f"Release {versao}, aberta pela fábrica. **Merge só com aprovação humana.**\n\n"
            f"## Inclui\n\n{assuntos}{RODAPE_PR}"
        )
        return github.abrir_pr(ramo, principal, f"Release {versao}", corpo), versao


def concluir_release(url: str, base: str, principal: str, github: Github, versao: str) -> None:
    """Depois do merge humano: cria a tag e leva `principal` de volta a `base` por fast-forward."""
    with tempfile.TemporaryDirectory(prefix="fabrica-pos-release-") as temporario:
        repo = Path(temporario) / "repo"
        _rodar([*GIT_SEM_HOOKS, "clone", "--quiet", "--no-checkout", url, str(repo)])
        sha = _rodar(["git", "-C", str(repo), "rev-parse", f"origin/{principal}"]).strip()
        ancestral = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "merge-base",
                "--is-ancestor",
                f"origin/release/{versao}",
                sha,
            ],
            check=False,
        )
        if ancestral.returncode != 0:
            raise PublicacaoRecusada(
                f"release/{versao} ainda não está em {principal}: falta o merge humano"
            )
        _rodar(
            [
                *GIT_SEM_HOOKS,
                "-C",
                str(repo),
                "tag",
                "-a",
                f"v{versao}",
                "-m",
                f"Release {versao}",
                sha,
            ]
        )
        _rodar([*GIT_SEM_HOOKS, "-C", str(repo), "push", "--quiet", "origin", f"v{versao}"])
        if not _ja_em(repo, f"origin/{base}", sha):
            # `base` recebeu trabalho depois da release: o fast-forward seria recusado, e não falta nada.
            return
        _rodar(
            [
                *GIT_SEM_HOOKS,
                "-C",
                str(repo),
                "push",
                "--quiet",
                "origin",
                f"{sha}:refs/heads/{base}",
            ]
        )
