"""Máquina de estados de uma execução, com histórico gravado na mesma transação."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

TRANSICOES = {
    "DETECTADO": {"ENTRADA_OK", "RECUSADA_ENTRADA", "PARADA_ESPECIFICACAO", "PAUSADA_AMBIENTE"},
    "ENTRADA_OK": {"ROTEADO", "PAUSADA_DECISAO", "PAUSADA_AMBIENTE", "PAUSADA_LIMITE_USO"},
    "ROTEADO": {"PLANEJANDO", "CONTRATO_EMITIDO"},
    "PLANEJANDO": {
        "CONTRATO_EMITIDO",
        "PARADA_ESPECIFICACAO",
        "PAUSADA_AMBIENTE",
        "PAUSADA_LIMITE_USO",
    },
    "CONTRATO_EMITIDO": {"AGENTE_RODANDO", "PAUSADA_AMBIENTE"},
    "AGENTE_RODANDO": {
        "RESPOSTA_VALIDA",
        "RESPOSTA_RECUSADA",
        "PARADA_ESPECIFICACAO",
        "PAUSADA_AMBIENTE",
        "PAUSADA_LIMITE_USO",
        "CONTRATO_EMITIDO",
    },
    "RESPOSTA_VALIDA": {"GATES_LOCAIS", "TESTADOR_RODANDO"},
    "TESTADOR_RODANDO": {
        "GATES_LOCAIS",
        "RESPOSTA_RECUSADA",
        "PARADA_ESPECIFICACAO",
        "PAUSADA_AMBIENTE",
        "PAUSADA_LIMITE_USO",
    },
    "GATES_LOCAIS": {
        "SEGURANCA",
        "CORRECAO",
        "PARADA_LIMITE",
        "PARADA_ESPECIFICACAO",
        "PAUSADA_AMBIENTE",
    },
    "SEGURANCA": {
        "VERIFY_SDD",
        "CORRECAO",
        "PARADA_LIMITE",
        "RESPOSTA_RECUSADA",
        "PAUSADA_AMBIENTE",
        "PAUSADA_LIMITE_USO",
    },
    "VERIFY_SDD": {
        "PR_PARA_DEVELOP",
        "CORRECAO",
        "PARADA_LIMITE",
        "PARADA_ESPECIFICACAO",
        "PAUSADA_AMBIENTE",
        "PAUSADA_LIMITE_USO",
        "RESPOSTA_RECUSADA",
    },
    "PR_PARA_DEVELOP": {"CI_E2E", "PAUSADA_AMBIENTE"},
    "CI_E2E": {"MERGE_EM_DEVELOP", "CORRECAO", "PARADA_LIMITE", "PAUSADA_AMBIENTE"},
    "MERGE_EM_DEVELOP": {"ARQUIVAMENTO", "PAUSADA_AMBIENTE"},
    "ARQUIVAMENTO": {"MEDIDA", "PAUSADA_AMBIENTE"},
    "RESPOSTA_RECUSADA": {"CORRECAO", "PARADA_LIMITE"},
    "CORRECAO": {"CONTRATO_EMITIDO"},
    "PAUSADA_AMBIENTE": {
        "DETECTADO",
        "ENTRADA_OK",
        "PLANEJANDO",
        "CONTRATO_EMITIDO",
        "TESTADOR_RODANDO",
        "GATES_LOCAIS",
        "SEGURANCA",
        "VERIFY_SDD",
        "PR_PARA_DEVELOP",
        "CI_E2E",
        "MERGE_EM_DEVELOP",
        "ARQUIVAMENTO",
    },
    "PAUSADA_LIMITE_USO": {
        "ENTRADA_OK",
        "PLANEJANDO",
        "CONTRATO_EMITIDO",
        "TESTADOR_RODANDO",
        "SEGURANCA",
        "VERIFY_SDD",
    },
    "PAUSADA_DECISAO": {"ROTEADO"},
    "RECUSADA_ENTRADA": set(),
    "PARADA_ESPECIFICACAO": set(),
    "PARADA_LIMITE": set(),
    "MEDIDA": set(),
}
TERMINAIS = {estado for estado, destinos in TRANSICOES.items() if not destinos}
PAUSAS = {"PAUSADA_AMBIENTE", "PAUSADA_LIMITE_USO", "PAUSADA_DECISAO"}


class TransicaoInvalida(Exception):
    pass


class Historico:
    def __init__(self, caminho_db: Path | str):
        self._db = sqlite3.connect(caminho_db)
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS execucoes (
                run_id TEXT PRIMARY KEY,
                projeto TEXT NOT NULL,
                sdd TEXT NOT NULL,
                estado TEXT NOT NULL,
                dados TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                origem TEXT,
                destino TEXT NOT NULL,
                motivo TEXT NOT NULL,
                em TEXT NOT NULL
            );
            """
        )
        self._db.commit()

    def criar(self, projeto: str, sdd: str, dados: dict | None = None) -> str:
        run_id = str(uuid.uuid4())
        with self._db:
            self._db.execute(
                "INSERT INTO execucoes VALUES (?, ?, ?, 'DETECTADO', ?)",
                (run_id, projeto, sdd, json.dumps(dados or {})),
            )
            self._registrar(run_id, None, "DETECTADO", "execução criada")
        return run_id

    def _registrar(self, run_id: str, origem: str | None, destino: str, motivo: str) -> None:
        self._db.execute(
            "INSERT INTO transicoes (run_id, origem, destino, motivo, em) VALUES (?, ?, ?, ?, ?)",
            (run_id, origem, destino, motivo, datetime.now(UTC).isoformat()),
        )

    def _linha(self, run_id: str) -> tuple:
        linha = self._db.execute(
            "SELECT projeto, sdd, estado, dados FROM execucoes WHERE run_id = ?", (run_id,)
        ).fetchone()
        if linha is None:
            raise KeyError(run_id)
        return linha

    def estado(self, run_id: str) -> str:
        return self._linha(run_id)[2]

    def dados(self, run_id: str) -> dict:
        return json.loads(self._linha(run_id)[3])

    def projeto_e_sdd(self, run_id: str) -> tuple[str, str]:
        linha = self._linha(run_id)
        return linha[0], linha[1]

    def avancar(self, run_id: str, destino: str, motivo: str, dados: dict | None = None) -> None:
        origem = self.estado(run_id)
        if destino not in TRANSICOES[origem]:
            raise TransicaoInvalida(f"{origem} -> {destino}")
        novos = self.dados(run_id) | (dados or {})
        with self._db:
            cursor = self._db.execute(
                "UPDATE execucoes SET estado = ?, dados = ? WHERE run_id = ? AND estado = ?",
                (destino, json.dumps(novos), run_id, origem),
            )
            if cursor.rowcount != 1:
                raise TransicaoInvalida(f"estado de {run_id} mudou durante a transição")
            self._registrar(run_id, origem, destino, motivo)

    def atualizar_dados(self, run_id: str, dados: dict) -> None:
        with self._db:
            self._db.execute(
                "UPDATE execucoes SET dados = ? WHERE run_id = ?",
                (json.dumps(self.dados(run_id) | dados), run_id),
            )

    def transicoes(self, run_id: str) -> list[tuple[str | None, str, str]]:
        return self._db.execute(
            "SELECT origem, destino, motivo FROM transicoes WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()

    def listar(self) -> list[tuple[str, str, str, str]]:
        return self._db.execute("SELECT run_id, projeto, sdd, estado FROM execucoes").fetchall()
