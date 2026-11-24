"""Chama os validadores do framework como subprocesso, em modo somente leitura."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# Clone do framework, por exemplo de https://github.com/michelpessoa/doc-traceability-framework.
FRAMEWORK_PADRAO = Path(
    os.environ.get("FABRICA_FRAMEWORK") or Path.home() / "doc-traceability-central"
).expanduser()


SCHEMA_RESULTADO = "dtf.resultado-validador/1"
SCHEMA_REVIEW = "dtf.review-approval/1"


class VersaoDivergente(Exception):
    """O clone do framework não é a versão que o projeto exige."""


@dataclass(frozen=True)
class ResultadoValidador:
    nome: str
    ok: bool
    saida: str
    problemas: tuple[str, ...] = ()


class Framework:
    def __init__(self, raiz: Path = FRAMEWORK_PADRAO):
        self.raiz = raiz
        self.scripts = raiz / "_framework" / "scripts"
        if not self.scripts.is_dir():
            raise FileNotFoundError(f"framework não encontrado em {raiz}")

    def sha(self) -> str:
        resultado = subprocess.run(
            ["git", "-C", str(self.raiz), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return resultado.stdout.strip()

    def _executar(self, script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        # Sem bytecode, para não escrever nada dentro do repositório do framework.
        env = {"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run(
            [sys.executable, str(self.scripts / script), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _rodar(self, script: str, *args: str, cwd: Path) -> ResultadoValidador:
        resultado = self._executar(script, *args, "--json", cwd=cwd)
        saida = resultado.stdout + resultado.stderr
        try:
            dados = json.loads(resultado.stdout)
        except json.JSONDecodeError:
            dados = None
        if not isinstance(dados, dict) or dados.get("schema") != SCHEMA_RESULTADO:
            return ResultadoValidador(
                script,
                False,
                saida,
                (f"saída fora do contrato {SCHEMA_RESULTADO}: {saida[-300:]}",),
            )
        problemas = tuple(p["mensagem"] for p in dados.get("problemas", []))
        return ResultadoValidador(script, dados.get("ok") is True, saida, problemas)

    def versao(self) -> str:
        regras = self.raiz / "_framework" / "rules" / "workflow-rules.yaml"
        return yaml.safe_load(regras.read_text(encoding="utf-8"))["framework"]["version"]

    def exigir_versao(self, exigida: str) -> None:
        """Recusa rodar com uma versão do framework diferente da declarada no projeto."""
        if not exigida:
            raise VersaoDivergente(
                "o projeto não declara a versão do framework: preencha `framework` em projetos/<nome>.yaml"
            )
        atual = self.versao()
        if atual != exigida:
            raise VersaoDivergente(
                f"o projeto exige o framework {exigida}, e o clone em {self.raiz} está na {atual}"
            )

    def exigir_central(self, central: Path, exigida: str) -> None:
        """Recusa rodar se o `_framework/` do central não for a versão declarada no projeto."""
        if central == Path(""):
            raise VersaoDivergente(
                "o projeto não declara o caminho do central: preencha `central` em projetos/<nome>.yaml"
            )
        if not (central / "_framework" / "scripts").is_dir():
            raise VersaoDivergente(f"central não encontrado em {central}")
        atual = Framework(central).versao()
        if atual != exigida:
            raise VersaoDivergente(
                f"o projeto exige o framework {exigida}, e o central em {central} está na {atual}"
            )

    def validar_estado(self, repo: Path, sdd: Path) -> ResultadoValidador:
        return self._rodar("validate_state.py", str(sdd), cwd=repo)

    def validar_entrada(
        self, repo: Path, sdd: Path, docs_central: Path
    ) -> list[ResultadoValidador]:
        return [
            self._rodar("validate_doc.py", str(sdd), cwd=repo),
            self._rodar("registry_tools.py", "validate", str(sdd.parent), cwd=repo),
            self._rodar("check_source_docs.py", str(sdd), str(docs_central), cwd=repo),
        ]

    def validar_documento(self, cwd: Path, documento: Path) -> ResultadoValidador:
        return self._rodar("validate_doc.py", str(documento), cwd=cwd)

    def validar_registry(self, cwd: Path, docs: Path) -> ResultadoValidador:
        return self._rodar("registry_tools.py", "validate", str(docs), cwd=cwd)

    def gerar_registry_md(self, docs: Path) -> None:
        # Sem `--json`: o script não está em `machine_outputs`.
        resultado = self._executar("generate_registry_md.py", str(docs), cwd=docs)
        if resultado.returncode != 0:
            raise RuntimeError(f"generate_registry_md.py: {resultado.stderr[-500:]}")

    def decidir_review(self, documento: Path, reviews: Path, head: str, pr_url: str) -> dict:
        resultado = self._executar(
            "review_approval.py",
            str(documento),
            "--reviews",
            str(reviews),
            "--head",
            head,
            "--pr-url",
            pr_url,
            "--json",
            cwd=documento.parent,
        )
        saida = resultado.stdout + resultado.stderr
        try:
            dados = json.loads(resultado.stdout)
        except json.JSONDecodeError:
            dados = None
        if isinstance(dados, dict) and dados.get("schema") == SCHEMA_REVIEW:
            return dados
        return {
            "valida": False,
            "motivos": [f"saída fora do contrato {SCHEMA_REVIEW}: {saida[-300:]}"],
            "approved_by": None,
        }
