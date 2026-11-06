"""Emissão de contratos e recebimento das respostas dos agentes.

O token protege contra replay e contra resposta atrasada de uma tentativa anterior.
Não é autenticação: o agente enxerga o token. A garantia contra agente mal-comportado
vem do isolamento e dos gates.
"""

import hashlib
import json
import re
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

DIR_SCHEMAS = Path(__file__).resolve().parent.parent / "contracts"
SCHEMA_POR_ETAPA = {
    "decisao": "resposta-decisor",
    "planejamento": "resposta-planejador",
    "desenvolvimento": "resposta-desenvolvedor",
    "testes": "resposta-testador",
    "seguranca": "resposta-seguranca",
    "verificacao": "validacao",
    "descoberta": "resposta-descoberta",
}
EVIDENCIA_RE = re.compile(r"^(?P<caminho>.+):(?P<linha>[0-9]+) — .+$")


class RespostaRecusada(Exception):
    """Resposta fora do contrato. O motivo vai para o histórico da execução."""


def carregar_schema(nome: str) -> dict:
    return json.loads((DIR_SCHEMAS / f"{nome}.schema.json").read_text(encoding="utf-8"))


def schema_da_etapa(etapa: str) -> dict:
    return carregar_schema(SCHEMA_POR_ETAPA[etapa])


def erros_de_schema(documento: dict, schema: dict) -> list[str]:
    validador = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(raiz)'}: {e.message}"
        for e in sorted(validador.iter_errors(documento), key=lambda e: list(e.absolute_path))
    ]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Cartorio:
    """Guarda os contratos emitidos e consome cada token uma única vez."""

    def __init__(self, caminho_db: Path | str):
        self._db = sqlite3.connect(caminho_db)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS contratos (
                contrato_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                etapa TEXT NOT NULL,
                tentativa INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                emitido_em TEXT NOT NULL,
                usado_em TEXT
            )"""
        )
        self._db.commit()

    def emitir(self, run_id: str, projeto: str, etapa: str, tentativa: int, entrada: dict) -> dict:
        contrato = {
            "versao": "1",
            "contrato_id": str(uuid.uuid4()),
            "run_id": run_id,
            "projeto": projeto,
            "etapa": etapa,
            "tentativa": tentativa,
            "token": secrets.token_urlsafe(32),
            "emitido_em": datetime.now(UTC).isoformat(),
            "entrada": entrada,
        }
        erros = erros_de_schema(contrato, carregar_schema("contrato"))
        if erros:
            raise ValueError(f"contrato inválido: {erros}")
        self._db.execute(
            "INSERT INTO contratos VALUES (?, ?, ?, ?, ?, ?, NULL)",
            (
                contrato["contrato_id"],
                run_id,
                etapa,
                tentativa,
                _hash(contrato["token"]),
                contrato["emitido_em"],
            ),
        )
        self._db.commit()
        return contrato

    def receber(self, contrato_id: str, resposta: dict) -> dict:
        linha = self._db.execute(
            "SELECT etapa, tentativa, token_hash FROM contratos WHERE contrato_id = ?",
            (contrato_id,),
        ).fetchone()
        if linha is None:
            raise RespostaRecusada("contrato desconhecido")
        etapa, tentativa, token_hash = linha

        erros = erros_de_schema(resposta, schema_da_etapa(etapa))
        if erros:
            raise RespostaRecusada(f"fora do schema: {erros}")
        if resposta["contrato_id"] != contrato_id:
            raise RespostaRecusada("contrato_id da resposta não corresponde")
        if not secrets.compare_digest(_hash(resposta["token"]), token_hash):
            raise RespostaRecusada("token inválido")
        if "tentativa" in resposta and resposta["tentativa"] != tentativa:
            raise RespostaRecusada("tentativa da resposta não corresponde ao contrato")

        cursor = self._db.execute(
            "UPDATE contratos SET usado_em = ? WHERE contrato_id = ? AND usado_em IS NULL",
            (datetime.now(UTC).isoformat(), contrato_id),
        )
        self._db.commit()
        if cursor.rowcount != 1:
            raise RespostaRecusada("token reutilizado")
        return resposta


def problemas_de_evidencia(raiz: Path, evidencias: list[str]) -> list[str]:
    """Confere que cada evidência aponta para arquivo e linha que existem em `raiz`."""
    raiz = raiz.resolve()
    problemas = []
    for evidencia in evidencias:
        achado = EVIDENCIA_RE.match(evidencia)
        if not achado:
            problemas.append(f"evidência fora do formato: {evidencia}")
            continue
        alvo = (raiz / achado["caminho"]).resolve()
        if not alvo.is_relative_to(raiz) or not alvo.is_file():
            problemas.append(f"arquivo inexistente na evidência: {achado['caminho']}")
            continue
        total = len(alvo.read_text(encoding="utf-8", errors="replace").splitlines())
        if not 1 <= int(achado["linha"]) <= total:
            problemas.append(f"linha inexistente na evidência: {evidencia}")
    return problemas


def problemas_de_coerencia(validacao: dict) -> list[str]:
    """Contas feitas em código: o veredito precisa bater com os critérios informados."""
    problemas = []
    criterios = validacao["criterios"]
    falharam = sum(1 for c in criterios if not c["passou"])
    if validacao["status"] == "aprovado" and (falharam or not criterios):
        problemas.append("aprovado sem todos os critérios aprovados")
    if validacao["testes"]["falharam"] != falharam:
        problemas.append("testes.falharam não bate com os critérios")
    if validacao["testes"]["passaram"] != len(criterios) - falharam:
        problemas.append("testes.passaram não bate com os critérios")
    return problemas
