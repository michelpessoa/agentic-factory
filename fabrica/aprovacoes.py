"""Aprovação humana de SDD, feita no terminal e presa ao conteúdo aprovado.

A fábrica faz merge em `develop` com o login do owner, então quem mergeou não distingue os dois. O
que distingue é o hash: a SDD só entra no pipeline se o conteúdo for exatamente o que o humano aprovou.
Mudar uma vírgula depois exige aprovar de novo.
"""

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def resumo(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


class Aprovacoes:
    def __init__(self, caminho_db: Path | str):
        self._db = sqlite3.connect(caminho_db)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS aprovacoes (
                projeto TEXT NOT NULL,
                sdd TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                origem TEXT NOT NULL,
                em TEXT NOT NULL,
                PRIMARY KEY (projeto, sdd, sha256)
            )"""
        )
        self._db.commit()

    def registrar(self, projeto: str, sdd: str, conteudo: bytes, origem: str) -> str:
        sha = resumo(conteudo)
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO aprovacoes VALUES (?, ?, ?, ?, ?)",
                (projeto, sdd, sha, origem, datetime.now(UTC).isoformat()),
            )
        return sha

    def aprovada(self, projeto: str, sdd: str, conteudo: bytes) -> bool:
        return (
            self._db.execute(
                "SELECT 1 FROM aprovacoes WHERE projeto = ? AND sdd = ? AND sha256 = ?",
                (projeto, sdd, resumo(conteudo)),
            ).fetchone()
            is not None
        )
