"""Gatilho automático: dispara a fábrica quando uma SDD passa a estar aprovada na base.

A primeira leitura de um projeto só registra o que já existe. Sem isso, ligar o vigia dispararia toda
SDD antiga. Cada SDD é identificada pelo último commit que a tocou, então corrigir e reaprovar uma SDD
parada dispara de novo. Só dispara o conteúdo aprovado no terminal (`fabrica aprovar`).
"""

import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from fabrica.execucao import preparar_copia
from fabrica.pipeline import ExecucaoEmAberto


class Vigia:
    def __init__(
        self, caminho_db: Path | str, projeto: str, repo: str, base: str, fonte, aprovacoes
    ):
        self._db = sqlite3.connect(caminho_db)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS sdds_vistas (
                projeto TEXT NOT NULL,
                sdd TEXT NOT NULL,
                commit_sdd TEXT NOT NULL,
                PRIMARY KEY (projeto, sdd, commit_sdd)
            )"""
        )
        self._db.commit()
        self._projeto = projeto
        self._repo = repo
        self._base = base
        self._fonte = fonte
        self._aprovacoes = aprovacoes

    def _ja_leu(self) -> bool:
        return (
            self._db.execute(
                "SELECT 1 FROM sdds_vistas WHERE projeto = ? LIMIT 1", (self._projeto,)
            ).fetchone()
            is not None
        )

    def _aprovadas(self) -> list[tuple[str, str, bytes]]:
        temporario = Path(tempfile.mkdtemp(prefix="fabrica-vigia-"))
        try:
            copia = preparar_copia(self._repo, self._base, temporario / "copia")
            resultado = []
            for sdd in self._fonte.sdds_aprovadas(copia):
                commit_sdd = subprocess.run(
                    ["git", "-C", str(copia), "log", "-1", "--format=%H", "--", sdd],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
                resultado.append((sdd, commit_sdd, (copia / sdd).read_bytes()))
            return resultado
        finally:
            shutil.rmtree(temporario, ignore_errors=True)

    def verificar(self, disparar: Callable[[str], object]) -> list[str]:
        primeira_leitura = not self._ja_leu()
        novas = []
        for sdd, commit_sdd, conteudo in self._aprovadas():
            if not primeira_leitura and not self._aprovacoes.aprovada(self._projeto, sdd, conteudo):
                # Sem marcar como vista: quando o humano aprovar no terminal, ela dispara.
                continue
            with self._db:
                cursor = self._db.execute(
                    "INSERT OR IGNORE INTO sdds_vistas VALUES (?, ?, ?)",
                    (self._projeto, sdd, commit_sdd),
                )
            if cursor.rowcount == 1 and not primeira_leitura:
                novas.append(sdd)
        if primeira_leitura:
            # Marca o projeto como lido mesmo sem nenhuma SDD aprovada.
            with self._db:
                self._db.execute(
                    "INSERT OR IGNORE INTO sdds_vistas VALUES (?, '', '')", (self._projeto,)
                )
        disparadas = []
        for sdd in novas:
            try:
                disparar(sdd)
                disparadas.append(sdd)
            except ExecucaoEmAberto as erro:
                print(erro, flush=True)
        return disparadas
