import os
import subprocess
import sys
from pathlib import Path

CODIGO = "from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO as F; print(F)"


def caminho(valor: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "FABRICA_FRAMEWORK"}
    if valor is not None:
        env["FABRICA_FRAMEWORK"] = valor
    raiz = Path(__file__).resolve().parents[1]
    saida = subprocess.run(
        [sys.executable, "-c", CODIGO],
        cwd=raiz,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return saida.stdout.strip()


def test_framework_vem_da_variavel():
    assert caminho("~/outro-framework") == str(Path.home() / "outro-framework")


def test_framework_padrao_sem_variavel():
    assert caminho(None) == str(Path.home() / "doc-traceability-central")
    assert caminho("") == str(Path.home() / "doc-traceability-central")
