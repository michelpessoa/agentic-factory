"""Execução de agentes em contêiner, sem credencial do host.

O processo da fábrica fica no host e tem as credenciais. O agente fica no contêiner e
recebe só um diretório de trabalho descartável.
"""

import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

IMAGEM_AGENTE = "fabrica-agente:0.1"
IMAGEM_GATES = "fabrica-gates:0.1"
REDE_INTERNA = "fabrica-interna"
URL_PROXY = "http://fabrica-proxy:8888"
IMAGEM_SEMGREP = "semgrep/semgrep:1.97.0"
REGRAS_SEMGREP = Path(__file__).resolve().parent.parent / "rules" / "semgrep.yaml"
ETIQUETA_DIRETORIO = "fabrica.diretorio"
CODIGOS_DE_FALHA_DO_DOCKER = {125, 126}
CAMINHO_TOKEN = Path.home() / ".config" / "fabrica" / "claude-token"
TEMPO_MAXIMO_SEGUNDOS = 1800
LIMITE_PATCH_BYTES = 20 * 1024 * 1024
TERMOS_LIMITE_DE_USO = ("usage limit", "rate limit", "limit reached", "hit your limit")


class AmbienteInvalido(Exception):
    """O host não está em condição segura para rodar agentes."""


class FalhaDeExecucao(Exception):
    def __init__(self, causa: str, detalhe: str):
        super().__init__(f"{causa}: {detalhe}")
        self.causa = causa
        self.detalhe = detalhe


def verificar_host(env: Mapping[str, str] | None = None) -> None:
    env = os.environ if env is None else env
    if env.get("ANTHROPIC_API_KEY"):
        raise AmbienteInvalido("ANTHROPIC_API_KEY definida: o uso seria cobrado por API")


def carregar_token(caminho: Path = CAMINHO_TOKEN) -> str:
    if not caminho.is_file():
        raise AmbienteInvalido(f"token da fábrica não encontrado em {caminho}")
    if caminho.stat().st_mode & 0o077:
        raise AmbienteInvalido(f"{caminho} precisa ter permissão 600")
    return caminho.read_text(encoding="utf-8").strip()


def argumentos_de_isolamento(
    dir_trabalho: Path | None,
    rede: str,
    uid: int | None = None,
    gid: int | None = None,
    somente_leitura: bool = False,
) -> list[str]:
    """Opções de `docker run` comuns a todo contêiner que executa código do agente."""
    uid = os.getuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    args = [
        "--rm",
        "--interactive",
        "--network",
        rede,
        "--user",
        f"{uid}:{gid}",
        "--cap-drop=ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--pids-limit",
        "512",
        "--memory",
        "4g",
        "--tmpfs",
        "/tmp:rw,size=512m",
        "--tmpfs",
        f"/home/agente:rw,size=256m,uid={uid},gid={gid},mode=700",
        "--env",
        "HOME=/home/agente",
        "--workdir",
        "/trabalho",
    ]
    if dir_trabalho is not None:
        modo = ",readonly" if somente_leitura else ""
        args += ["--mount", f"type=bind,source={dir_trabalho},target=/trabalho{modo}"]
    return args


def ambiente_minimo_docker(extras: Mapping[str, str] | None = None) -> dict[str, str]:
    """Ambiente do CLI do Docker: nada do host segue para o contêiner sem ser nomeado."""
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "")}
    if "DOCKER_HOST" in os.environ:
        env["DOCKER_HOST"] = os.environ["DOCKER_HOST"]
    env.update(extras or {})
    return env


@dataclass(frozen=True)
class ResultadoAgente:
    resposta: dict
    custo_usd: float | None = None
    duracao_ms: int | None = None
    bruto: dict = field(default_factory=dict)


class AgentRunner(Protocol):
    def executar(
        self, prompt: str, schema: dict, dir_trabalho: Path, modelo: str, ferramentas: list[str]
    ) -> ResultadoAgente: ...


def interpretar_saida_do_claude(codigo: int, stdout: str, stderr: str) -> ResultadoAgente:
    texto_de_erro = f"{stdout}\n{stderr}".lower()
    try:
        bruto = json.loads(stdout)
    except json.JSONDecodeError:
        causa = (
            "limite_uso" if any(t in texto_de_erro for t in TERMOS_LIMITE_DE_USO) else "ambiente"
        )
        raise FalhaDeExecucao(causa, f"saída não é JSON (exit {codigo}): {stderr[-500:]}") from None
    if bruto.get("is_error") or codigo != 0:
        causa = (
            "limite_uso" if any(t in texto_de_erro for t in TERMOS_LIMITE_DE_USO) else "ambiente"
        )
        raise FalhaDeExecucao(causa, str(bruto.get("result") or stderr)[-500:])
    resposta = bruto.get("structured_output")
    if not isinstance(resposta, dict):
        raise FalhaDeExecucao("fora_do_contrato", "sem structured_output na saída")
    return ResultadoAgente(resposta, bruto.get("total_cost_usd"), bruto.get("duration_ms"), bruto)


CHAVES_RECUSADAS_PELA_CLI = {"$schema", "$id", "allOf", "anyOf", "oneOf"}


def schema_para_cli(schema: dict) -> dict:
    """Schema aceito pela CLI e pela API, sem dialeto nem combinadores no topo.

    As regras retiradas continuam valendo: a fábrica revalida com o schema completo.
    """
    return {
        chave: valor for chave, valor in schema.items() if chave not in CHAVES_RECUSADAS_PELA_CLI
    }


def encerrar_conteineres_de(dir_trabalho: Path) -> None:
    """Depois de uma queda, o contêiner antigo não pode seguir rodando com o token."""
    listados = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"label={ETIQUETA_DIRETORIO}={dir_trabalho}"],
        env=ambiente_minimo_docker(),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    if listados:
        subprocess.run(
            ["docker", "rm", "-f", *listados],
            env=ambiente_minimo_docker(),
            capture_output=True,
            check=False,
        )


class ClaudeDockerRunner:
    """Roda `claude -p` no contêiner do agente, com saída de rede só pela lista do proxy."""

    def __init__(self, token: str | None = None, imagem: str = IMAGEM_AGENTE):
        verificar_host()
        self._token = token if token is not None else carregar_token()
        self._imagem = imagem

    def montar_comando(
        self, schema: dict, dir_trabalho: Path, modelo: str, ferramentas: list[str]
    ) -> list[str]:
        return [
            "docker", "run",
            *argumentos_de_isolamento(dir_trabalho, REDE_INTERNA),
            "--label", f"{ETIQUETA_DIRETORIO}={dir_trabalho}",
            "--env", "CLAUDE_CODE_OAUTH_TOKEN",
            "--env", f"HTTPS_PROXY={URL_PROXY}",
            "--env", f"HTTP_PROXY={URL_PROXY}",
            "--env", "NO_PROXY=",
            self._imagem,
            "claude", "-p",
            "--output-format", "json",
            "--json-schema", json.dumps(schema_para_cli(schema)),
            "--tools", ",".join(ferramentas),
            "--permission-mode", "bypassPermissions",
            "--setting-sources", "user",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--model", modelo,
        ]  # fmt: skip

    def executar(
        self, prompt: str, schema: dict, dir_trabalho: Path, modelo: str, ferramentas: list[str]
    ) -> ResultadoAgente:
        encerrar_conteineres_de(dir_trabalho)
        try:
            resultado = subprocess.run(
                self.montar_comando(schema, dir_trabalho, modelo, ferramentas),
                input=prompt,
                env=ambiente_minimo_docker({"CLAUDE_CODE_OAUTH_TOKEN": self._token}),
                capture_output=True,
                text=True,
                timeout=TEMPO_MAXIMO_SEGUNDOS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise FalhaDeExecucao("ambiente", "agente passou do tempo máximo") from None
        return interpretar_saida_do_claude(resultado.returncode, resultado.stdout, resultado.stderr)


class AmbienteDocker:
    """Executa em contêiner, sem rede e sem token, tudo o que roda código do agente."""

    def __init__(self, imagem: str = IMAGEM_GATES, imagem_semgrep: str = IMAGEM_SEMGREP):
        self._imagem = imagem
        self._imagem_semgrep = imagem_semgrep

    def extrair_patch(self, dir_trabalho: Path, base: str, excluir: tuple[str, ...] = ()) -> str:
        return extrair_patch(dir_trabalho, base, self._imagem, excluir)

    def rodar(self, dir_trabalho: Path, comando: str, tempo_segundos: int = 900) -> tuple[int, str]:
        return self._docker(
            argumentos_de_isolamento(dir_trabalho, "none"),
            [self._imagem, "sh", "-c", comando],
            tempo_segundos,
        )

    def procurar_segredos(self, dir_trabalho: Path) -> tuple[int, str]:
        comando = "gitleaks dir /trabalho --no-banner --redact --exit-code 1"
        return self.rodar(dir_trabalho, comando, 300)

    def analisar_codigo(self, dir_trabalho: Path) -> tuple[int, str]:
        args = argumentos_de_isolamento(dir_trabalho, "none")
        args += [
            "--mount", f"type=bind,source={REGRAS_SEMGREP},target=/regras.yaml,readonly",
            "--env", "SEMGREP_SEND_METRICS=off",
            "--env", "XDG_CONFIG_HOME=/tmp",
        ]  # fmt: skip
        comando = [
            self._imagem_semgrep, "semgrep", "scan", "--quiet", "--error", "--metrics=off",
            "--disable-version-check", "--config", "/regras.yaml", "/trabalho",
        ]  # fmt: skip
        return self._docker(args, comando, 600)

    def _docker(self, args: list[str], comando: list[str], tempo: int) -> tuple[int, str]:
        try:
            resultado = subprocess.run(
                ["docker", "run", *args, *comando],
                env=ambiente_minimo_docker(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=tempo,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 124, f"tempo máximo de {tempo}s"
        if resultado.returncode in CODIGOS_DE_FALHA_DO_DOCKER:
            raise FalhaDeExecucao(
                "ambiente", f"exit {resultado.returncode}: {resultado.stderr[-500:]}"
            )
        return resultado.returncode, (resultado.stdout + resultado.stderr)[-4000:]


def aplicar_patch(repo: Path, patch: str) -> None:
    """Aplica no clone limpo do host. `git apply` recusa caminho fora da árvore e `.git`."""
    subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(repo),
            "apply",
            "--binary",
            "--index",
            "-",
        ],
        input=patch,
        text=True,
        capture_output=True,
        check=True,
    )


def preparar_copia(
    repo: Path | str, ref: str, destino: Path, ocultar: tuple[str, ...] = ()
) -> Path:
    """Cópia descartável do código: sem remoto e sem hooks, com o histórico para o diff.

    `ocultar` tira caminhos da árvore de trabalho: histórico não é contexto.
    """
    git = ["git", "-c", "core.hooksPath=/dev/null"]
    subprocess.run(
        [*git, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(repo), str(destino)],
        check=True,
    )
    subprocess.run([*git, "-C", str(destino), "fetch", "--quiet", "origin", ref], check=True)
    subprocess.run(
        [*git, "-C", str(destino), "checkout", "--quiet", "--detach", "FETCH_HEAD"], check=True
    )
    subprocess.run([*git, "-C", str(destino), "remote", "remove", "origin"], check=True)
    if ocultar:
        regras = ["/*", *[f"!/{caminho}/" for caminho in ocultar]]
        subprocess.run(
            [*git, "-C", str(destino), "sparse-checkout", "set", "--no-cone", *regras], check=True
        )
    shutil.rmtree(destino / ".git" / "hooks", ignore_errors=True)
    return destino


def extrair_patch(
    dir_trabalho: Path, base: str, imagem: str = IMAGEM_GATES, excluir: tuple[str, ...] = ()
) -> str:
    """Extrai o diff num contêiner sem rede e sem token.

    Rodar `git` no host sobre um `.git` alterado pelo agente executaria o que ele tivesse
    plantado na configuração, como `core.fsmonitor`, com as credenciais do host.
    """
    script = (
        "set -e; mkdir -p /tmp/obj; "
        "export GIT_INDEX_FILE=/tmp/indice GIT_OBJECT_DIRECTORY=/tmp/obj "
        "GIT_ALTERNATE_OBJECT_DIRECTORIES=/trabalho/.git/objects; "
        "G='git -c safe.directory=* -c core.fsmonitor=false -c core.hooksPath=/dev/null'; "
        'B="$1"; shift; $G read-tree "$B"; $G add -A -- . "$@"; $G diff --cached --binary "$B" -- . "$@"'
    )
    pathspecs = [f":(exclude){caminho}" for caminho in excluir]
    resultado = subprocess.run(
        [
            "docker",
            "run",
            *argumentos_de_isolamento(dir_trabalho, "none", somente_leitura=True),
            imagem,
            "sh",
            "-c",
            script,
            "extrair",
            base,
            *pathspecs,
        ],
        env=ambiente_minimo_docker(),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if resultado.returncode != 0:
        raise FalhaDeExecucao("ambiente", f"falha ao extrair o patch: {resultado.stderr[-500:]}")
    if len(resultado.stdout.encode()) > LIMITE_PATCH_BYTES:
        raise FalhaDeExecucao("fora_do_contrato", "patch acima do limite")
    return resultado.stdout
