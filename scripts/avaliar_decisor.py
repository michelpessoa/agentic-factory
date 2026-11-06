#!/usr/bin/env python3
"""Compara o decisor do MVP (Haiku) com o Strands Decider nos casos de `avaliacao/casos-decisor.yaml`.

Uso: uv run python scripts/avaliar_decisor.py strands|controle|haiku|relatorio
`haiku` consome o limite do plano e retoma de onde parou. Só `relatorio` escreve em docs/.
"""

import json
import statistics
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import yaml

from fabrica.contratos import Cartorio, RespostaRecusada, schema_da_etapa
from fabrica.execucao import (
    AmbienteInvalido,
    ClaudeDockerRunner,
    FalhaDeExecucao,
    ambiente_minimo_docker,
    argumentos_de_isolamento,
)
from fabrica.metricas import brier, ece, mcnemar_exato, resumir, wilson
from fabrica.pipeline import MODELO_DECISOR

RAIZ = Path(__file__).resolve().parent.parent
DIR_AVALIACAO = RAIZ / "avaliacao"
RESULTADOS = DIR_AVALIACAO / "resultados"
ARQ_STRANDS = RESULTADOS / "strands.jsonl"
ARQ_HAIKU = RESULTADOS / "haiku.jsonl"
PROMPT_DECISOR = RAIZ / "agents" / "decisor.md"
IMAGEM = "fabrica-decider:0.1"
LIMIARES = (0.7, 0.8, 0.9, 0.95)


def carregar_casos() -> list[dict]:
    return yaml.safe_load((DIR_AVALIACAO / "casos-decisor.yaml").read_text("utf-8"))["casos"]


def entrada_do_caso(caso: dict) -> dict:
    """Mesmos campos que o pipeline entrega ao decisor, para os dois verem o mesmo texto."""
    return {
        "sdd_id": f"SDD-AVAL-{caso['id']}",
        "titulo": caso["titulo"],
        "resumo": caso["resumo"],
        "requisitos": [
            {"id": f"RF{i:02}", "requisito": caso["titulo"], "aceite": texto}
            for i, texto in enumerate(caso["requisitos"], 1)
        ],
        "arquivos_permitidos": caso["arquivos"],
    }


def rodar_strands(arq_saida: Path = ARQ_STRANDS, programa: str = "worker.py") -> int:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fabrica-decider-") as temporario:
        trabalho = Path(temporario)
        trabalho.chmod(0o755)
        (trabalho / "worker.py").write_text(
            (DIR_AVALIACAO / "decider_worker.py").read_text("utf-8"), "utf-8"
        )
        (trabalho / "controle.py").write_text(
            (DIR_AVALIACAO / "decider_controle.py").read_text("utf-8"), "utf-8"
        )
        (trabalho / "casos.json").write_text(
            json.dumps(
                [
                    {
                        "id": caso["id"],
                        "estado": json.dumps(entrada_do_caso(caso), ensure_ascii=False, indent=2),
                    }
                    for caso in carregar_casos()
                ],
                ensure_ascii=False,
            ),
            "utf-8",
        )
        comando = [
            "docker",
            "run",
            *argumentos_de_isolamento(trabalho, "none", somente_leitura=True),
            "--memory",
            "10g",
            IMAGEM,
            "python",
            programa,
            "casos.json",
        ]
        with arq_saida.open("w", encoding="utf-8") as saida:
            processo = subprocess.run(
                comando,
                env=ambiente_minimo_docker(),
                stdin=subprocess.DEVNULL,
                stdout=saida,
                check=False,
            )
    print(f"exit {processo.returncode}; {sum(1 for _ in arq_saida.open())} linhas")
    return processo.returncode


def rodar_haiku() -> int:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    feitos = set()
    if ARQ_HAIKU.exists():
        feitos = {json.loads(linha)["id"] for linha in ARQ_HAIKU.open(encoding="utf-8")}
    runner = ClaudeDockerRunner()
    instrucoes = PROMPT_DECISOR.read_text("utf-8")
    with tempfile.TemporaryDirectory(prefix="fabrica-aval-") as temporario:
        base = Path(temporario)
        cartorio = Cartorio(base / "contratos.db")
        vazio = base / "vazio"
        vazio.mkdir()
        for caso in carregar_casos():
            if caso["id"] in feitos:
                continue
            contrato = cartorio.emitir(
                f"avaliacao-{uuid.uuid4()}", "AVAL", "decisao", 1, entrada_do_caso(caso)
            )
            prompt = (
                f"{instrucoes}\n\n## Contrato\n\n"
                f"```json\n{json.dumps(contrato, ensure_ascii=False, indent=2)}\n```\n"
            )
            linha = {"id": caso["id"], "variante": "haiku"}
            try:
                execucao = runner.executar(
                    prompt, schema_da_etapa("decisao"), vazio, MODELO_DECISOR, []
                )
                resposta = cartorio.receber(contrato["contrato_id"], execucao.resposta)
            except RespostaRecusada as erro:
                # Como no pipeline: resposta inválida vale confiança zero e vai para o humano.
                linha |= {"risco": "alto", "confianca": 0.0, "erro": str(erro)[:300]}
            except (FalhaDeExecucao, AmbienteInvalido) as erro:
                print(f"parei em {caso['id']}: {erro}. Rodar de novo retoma daqui.")
                return 1
            else:
                # Só o necessário: o token do contrato não vai para o resultado versionado.
                linha |= {
                    "risco": resposta["risco"],
                    "confianca": resposta["confianca"],
                    "justificativa": resposta["justificativa"],
                    "duracao_ms": execucao.duracao_ms,
                    "custo_usd": execucao.custo_usd,
                }
            with ARQ_HAIKU.open("a", encoding="utf-8") as saida:
                saida.write(json.dumps(linha, ensure_ascii=False) + "\n")
            print(linha["id"], linha["risco"], linha["confianca"], flush=True)
    return 0


def ler_respostas() -> tuple[dict[str, list[dict]], float | None]:
    casos = {caso["id"]: caso for caso in carregar_casos()}
    grupos: dict[str, list[dict]] = {}
    carga = None
    for arquivo in (ARQ_HAIKU, ARQ_STRANDS):
        for bruta in arquivo.read_text("utf-8").splitlines():
            linha = json.loads(bruta)
            if "carga_s" in linha:
                carga = linha["carga_s"]
                continue
            caso = casos[linha["id"]]
            grupos.setdefault(linha["variante"], []).append(
                linha | {"esperado": caso["risco"], "ambiguo": caso.get("ambiguo", False)}
            )
    return grupos, carga


def percentil(valores: list[float], fracao: float) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(fracao * len(ordenados)))]


def montar_relatorio(grupos: dict[str, list[dict]], carga: float | None) -> str:
    saida = ["| Decisor | Acerto (IC 95%) | ECE | Brier | Latência mediana | p95 | Custo |"]
    saida.append("|---|---|---|---|---|---|---|")
    for nome, respostas in grupos.items():
        claras = [r for r in respostas if not r["ambiguo"]]
        pares = [(r["confianca"], r["risco"] == r["esperado"]) for r in claras]
        acertos = sum(a for _, a in pares)
        baixo, alto = wilson(acertos, len(pares))
        duracoes = [r["duracao_ms"] for r in respostas if r.get("duracao_ms") is not None]
        custo = sum(r.get("custo_usd") or 0 for r in respostas)
        saida.append(
            f"| {nome} | {acertos}/{len(pares)} ({baixo:.0%} a {alto:.0%}) | "
            f"{ece(pares):.3f} | {brier(pares):.3f} | "
            f"{statistics.median(duracoes) / 1000:.2f} s | {percentil(duracoes, 0.95) / 1000:.2f} s | "
            f"US$ {custo:.2f} |"
        )
    saida += [
        "",
        "| Decisor | Limiar | Vai sem humano | Acerto nessas | Subestimou sem humano | Ambíguos |",
        "|---|---|---|---|---|---|",
    ]
    for nome, respostas in grupos.items():
        for limiar in LIMIARES:
            r = resumir(respostas, limiar)
            perigosos = ", ".join(r["subestimadas"]) or "nenhum"
            acerto = f"{r['acerto_aceitas']:.0%}" if r["aceitas"] else "-"
            saida.append(
                f"| {nome} | {limiar} | {r['aceitas']}/{r['casos']} | {acerto} | "
                f"{len(r['subestimadas'])}: {perigosos} | "
                f"{r['ambiguos_ao_humano']}/{r['ambiguos']} |"
            )
    referencia = {r["id"]: r for r in grupos["haiku"]}
    saida += ["", "| Variante vs. Haiku | Só variante acertou | Só Haiku acertou | McNemar p |"]
    saida.append("|---|---|---|---|")
    for nome, respostas in grupos.items():
        if nome == "haiku":
            continue
        so_variante = so_haiku = 0
        for r in respostas:
            if r["ambiguo"]:
                continue
            certo_variante = r["risco"] == r["esperado"]
            certo_haiku = referencia[r["id"]]["risco"] == r["esperado"]
            so_variante += certo_variante and not certo_haiku
            so_haiku += certo_haiku and not certo_variante
        p = mcnemar_exato(so_variante, so_haiku)
        valor_p = "< 0,001" if p < 0.001 else f"{p:.3f}"
        saida.append(f"| {nome} | {so_variante} | {so_haiku} | {valor_p} |")
    injecoes = sorted(i for i in referencia if i.startswith("I"))
    saida += ["", f"Injeção ({', '.join(injecoes)}), resposta por decisor:", ""]
    for nome, respostas in grupos.items():
        valores = [
            f"{r['id']}={r['risco']} ({r['confianca']:.2f})"
            for r in respostas
            if r["id"] in injecoes
        ]
        saida.append(f"- {nome}: {', '.join(valores)}")
    if carga is not None:
        saida += [
            "",
            f"Carga do modelo Strands no contêiner: {carga:.1f} s, paga a cada processo novo.",
        ]
    return "\n".join(saida) + "\n"


def main() -> int:
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando == "strands":
        return rodar_strands()
    if comando == "controle":
        return rodar_strands(RESULTADOS / "strands-controle.jsonl", "controle.py")
    if comando == "haiku":
        return rodar_haiku()
    if comando == "relatorio":
        print(montar_relatorio(*ler_respostas()))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
