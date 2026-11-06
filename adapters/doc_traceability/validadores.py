"""Chama os validadores do framework como subprocesso, em modo somente leitura."""

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


@dataclass(frozen=True)
class ResultadoValidador:
    nome: str
    ok: bool
    saida: str


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

    def _rodar(self, script: str, *args: str, cwd: Path) -> ResultadoValidador:
        # Sem bytecode, para não escrever nada dentro do repositório do framework.
        env = {"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}
        resultado = subprocess.run(
            [sys.executable, str(self.scripts / script), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return ResultadoValidador(
            script, resultado.returncode == 0, resultado.stdout + resultado.stderr
        )

    def versao(self) -> str:
        regras = self.raiz / "_framework" / "rules" / "workflow-rules.yaml"
        return yaml.safe_load(regras.read_text(encoding="utf-8"))["framework"]["version"]

    def validar_estado(self, repo: Path, sdd: Path) -> ResultadoValidador:
        return self._rodar("validate_state.py", str(sdd), cwd=repo)

    def validar_entrada(
        self, repo: Path, sdd: Path, docs_central: Path | None = None
    ) -> list[ResultadoValidador]:
        resultados = [
            self._rodar("validate_doc.py", str(sdd), cwd=repo),
            self._rodar("registry_tools.py", "validate", str(sdd.parent), cwd=repo),
        ]
        if docs_central is not None:
            resultados.append(
                self._rodar("check_source_docs.py", str(sdd), str(docs_central), cwd=repo)
            )
        return resultados
