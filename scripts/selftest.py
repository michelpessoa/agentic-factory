#!/usr/bin/env python3
"""Mutação dos gates: enfraquece cada proteção e exige que o teste falhe.

Trabalha numa cópia do repositório, nunca nos arquivos reais. Derivado do `selftest.py` do
framework. Uso: uv run python scripts/selftest.py [trecho do arquivo da mutação]
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
ITENS_DA_COPIA = [
    "fabrica",
    "adapters",
    "avaliacao",
    "contracts",
    "agents",
    "rules",
    "scripts",
    "tests",
    "pyproject.toml",
]


def rodar_teste(copia: Path, teste: str) -> int:
    comando = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", teste]
    resultado = subprocess.run(comando, cwd=copia, capture_output=True, text=True, check=False)
    return resultado.returncode


def main() -> int:
    mutacoes = yaml.safe_load((RAIZ / "tests" / "mutacoes.yaml").read_text(encoding="utf-8"))
    if len(sys.argv) > 1:
        mutacoes = [m for m in mutacoes if sys.argv[1] in m["arquivo"]]
    sobreviventes = 0
    with tempfile.TemporaryDirectory(prefix="fabrica-selftest-") as temporario:
        copia = Path(temporario)
        for item in ITENS_DA_COPIA:
            origem = RAIZ / item
            destino = copia / item
            if origem.is_dir():
                shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy(origem, destino)
        for mutacao in mutacoes:
            arquivo = copia / mutacao["arquivo"]
            original = arquivo.read_text(encoding="utf-8")
            if mutacao["procurar"] not in original:
                print(f"NÃO APLICADA  {mutacao['descricao']}")
                sobreviventes += 1
                continue
            arquivo.write_text(
                original.replace(mutacao["procurar"], mutacao["trocar"]), encoding="utf-8"
            )
            codigo = rodar_teste(copia, mutacao["teste"])
            arquivo.write_text(original, encoding="utf-8")
            if codigo == 1:
                print(f"morta         {mutacao['descricao']}")
            else:
                print(f"SOBREVIVEU    {mutacao['descricao']} (pytest exit {codigo})")
                sobreviventes += 1
    print(f"{len(mutacoes) - sobreviventes}/{len(mutacoes)} mutações mortas")
    return 1 if sobreviventes else 0


if __name__ == "__main__":
    sys.exit(main())
