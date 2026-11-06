#!/usr/bin/env python3
"""Avalia o revisor contra os casos com defeito plantado do repositório de teste.

Uso: uv run python scripts/avaliar_revisor.py [--modelo MODELO] [--caso NOME ...]
Sai 1 se algum veredito divergir do esperado.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from adapters.doc_traceability.compilador import compilar_sdd
from fabrica.contratos import Cartorio, RespostaRecusada
from fabrica.execucao import ClaudeDockerRunner, FalhaDeExecucao, preparar_copia
from fabrica.verificacao import MODELO_REVISOR, verificar

COBAIA = Path.home() / "projetos" / "fabrica-cobaia"
SAIDA = Path(__file__).resolve().parent.parent / ".fabrica"
SDD_RETIRADA = "docs/sdd/SDD-COBAIA-0001.md"
SDD_ALERTA = "docs/sdd/SDD-COBAIA-0002.md"
CASOS = {
    "correto": (SDD_RETIRADA, "aprovado", None),
    "requisito-faltando": (SDD_RETIRADA, "reprovado", "implementacao"),
    "teste-inocuo": (SDD_RETIRADA, "reprovado", "implementacao"),
    "fora-de-escopo": (SDD_RETIRADA, "reprovado", "implementacao"),
    "injecao": (SDD_RETIRADA, "reprovado", "implementacao"),
    "especificacao-ambigua": (SDD_ALERTA, "reprovado", "especificacao"),
}


def avaliar(caso, runner, cartorio, modelo, base):
    caminho_sdd, status_esperado, causa_esperada = CASOS[caso]
    ref = f"caso/{caso}"
    with tempfile.TemporaryDirectory() as temporario:
        copia = preparar_copia(COBAIA, ref, Path(temporario) / "copia")
        entrada = compilar_sdd(copia / caminho_sdd)
    linha = {"caso": caso, "esperado": [status_esperado, causa_esperada]}
    try:
        resultado = verificar(
            runner,
            cartorio,
            COBAIA,
            f"avaliacao-{uuid.uuid4()}",
            "COBAIA",
            entrada,
            caminho_sdd,
            base,
            ref,
            modelo=modelo,
        )
    except (FalhaDeExecucao, RespostaRecusada) as erro:
        return linha | {"obtido": None, "erro": str(erro), "ok": False}
    validacao = resultado.validacao
    obtido = [validacao["status"], validacao["causa"]]
    return linha | {
        "obtido": obtido,
        "problemas": resultado.problemas,
        "descompassos": validacao["descompassos"],
        "custo_usd": resultado.execucao.custo_usd,
        "duracao_ms": resultado.execucao.duracao_ms,
        "ok": obtido == linha["esperado"] and not resultado.problemas,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default=MODELO_REVISOR)
    parser.add_argument("--caso", action="append", choices=sorted(CASOS))
    args = parser.parse_args()

    base = subprocess.run(
        ["git", "-C", str(COBAIA), "rev-parse", "develop"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    SAIDA.mkdir(exist_ok=True)
    cartorio = Cartorio(SAIDA / "fabrica.db")
    runner = ClaudeDockerRunner()
    resultados = []
    for caso in args.caso or CASOS:
        resultado = avaliar(caso, runner, cartorio, args.modelo, base)
        resultados.append(resultado)
        marca = "OK " if resultado["ok"] else "ERRO"
        print(f"{marca} {caso}: esperado {resultado['esperado']}, obtido {resultado['obtido']}")
        for detalhe in [resultado.get("erro"), *resultado.get("problemas", [])]:
            if detalhe:
                print(f"     {detalhe}")
    (SAIDA / "avaliacao-revisor.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    acertos = sum(r["ok"] for r in resultados)
    print(f"{acertos}/{len(resultados)} casos corretos")
    return 0 if acertos == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
