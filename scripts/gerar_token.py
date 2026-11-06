#!/usr/bin/env python3
"""Roda `claude setup-token` e salva o token gerado, sem passar pela área de transferência.

Uso: uv run python scripts/gerar_token.py
O código do navegador, se pedido, é colado no próprio comando. O token não é reimpresso aqui.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DESTINO = Path.home() / ".config" / "fabrica" / "claude-token"
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\^_])")
TOKEN_RE = re.compile(r"sk-ant-oat[A-Za-z0-9_-]+")


def extrair_token(saida: str) -> str | None:
    """Último token da saída. A tela pode ter quebrado o token em várias linhas."""
    limpa = ANSI_RE.sub("", saida).replace("\r", "")
    sem_quebras = re.sub(r"(?<=[A-Za-z0-9_-])\n(?=[A-Za-z0-9_-])", "", limpa)
    achados = TOKEN_RE.findall(sem_quebras)
    return achados[-1] if achados else None


def main() -> int:
    os.umask(0o077)
    DESTINO.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=DESTINO.parent, prefix="saida-") as registro:
        subprocess.run(["script", "-qfc", "claude setup-token", registro.name], check=False)
        saida = Path(registro.name).read_text(encoding="utf-8", errors="replace")
    token = extrair_token(saida)
    if token is None:
        print("\nToken não encontrado na saída. Nada foi alterado.")
        return 1
    DESTINO.write_text(token, encoding="utf-8")
    DESTINO.chmod(0o600)
    print(f"\nToken salvo em {DESTINO} ({len(token)} caracteres). Avise para eu validar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
