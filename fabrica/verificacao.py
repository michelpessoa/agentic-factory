"""Gate de verificação independente: revisor em contexto novo, resposta em JSON."""

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fabrica.contratos import (
    Cartorio,
    problemas_de_coerencia,
    problemas_de_evidencia,
    schema_da_etapa,
)
from fabrica.execucao import AgentRunner, ResultadoAgente, preparar_copia

PROMPT_REVISOR = Path(__file__).resolve().parent.parent / "agents" / "revisor.md"
FERRAMENTAS_REVISOR = ["Read", "Grep", "Glob", "Bash", "Edit"]
MODELO_REVISOR = "claude-opus-5-5"


@dataclass(frozen=True)
class Verificacao:
    validacao: dict
    problemas: list[str]
    execucao: ResultadoAgente


def montar_prompt(contrato: dict, base: str, caminho_sdd: str) -> str:
    instrucoes = PROMPT_REVISOR.read_text(encoding="utf-8")
    return (
        f"{instrucoes}\n\n## Contrato\n\n```json\n{json.dumps(contrato, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## Diff a verificar\n\n`git diff {base}..HEAD` no diretório atual.\n\n"
        f"## SDD\n\nArquivo `{caminho_sdd}` no diretório atual.\n"
    )


def verificar(
    runner: AgentRunner,
    cartorio: Cartorio,
    repo: Path | str,
    run_id: str,
    projeto: str,
    entrada: dict,
    caminho_sdd: str,
    base: str,
    head: str,
    tentativa: int = 1,
    modelo: str = MODELO_REVISOR,
    ocultar: tuple[str, ...] = (),
) -> Verificacao:
    """Roda o revisor. Sem o histórico do desenvolvedor: só SDD, código e diff."""
    contrato = cartorio.emitir(run_id, projeto, "verificacao", tentativa, entrada)
    temporario = Path(tempfile.mkdtemp(prefix="fabrica-verificacao-"))
    try:
        copia = preparar_copia(repo, head, temporario / "trabalho", ocultar)
        execucao = runner.executar(
            montar_prompt(contrato, base, caminho_sdd),
            schema_da_etapa("verificacao"),
            copia,
            modelo,
            FERRAMENTAS_REVISOR,
        )
        validacao = cartorio.receber(contrato["contrato_id"], execucao.resposta)
        problemas = problemas_de_coerencia(validacao) + problemas_de_evidencia(
            copia, validacao["evidencias"]
        )
        return Verificacao(validacao, problemas, execucao)
    finally:
        shutil.rmtree(temporario, ignore_errors=True)
