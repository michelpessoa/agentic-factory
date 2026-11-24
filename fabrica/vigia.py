"""Gatilho automático: dispara a fábrica quando uma SDD passa a estar aprovada na base.

A primeira leitura de um projeto só registra o que já existe. Sem isso, ligar o vigia dispararia toda
SDD antiga. Cada SDD é identificada pelo último commit que a tocou, então corrigir e reaprovar uma SDD
parada dispara de novo. Só dispara o conteúdo aprovado no terminal (`fabrica aprovar`) ou a SDD
aprovada por política (`approved_by.kind: policy`), que o pipeline confere na entrada.
"""

import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from fabrica.descoberta import AGUARDANDO_APROVACAO, AGUARDANDO_RESPOSTAS, PARADA
from fabrica.execucao import preparar_copia
from fabrica.pipeline import ExecucaoEmAberto
from fabrica.publicacao import FalhaDePublicacao

FALHAS_DE_LEITURA_ANTES_DO_AVISO = 3


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
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS specs_vistas (
                projeto TEXT,
                spec TEXT,
                content_sha256 TEXT,
                PRIMARY KEY (projeto, spec, content_sha256)
            )"""
        )
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS avisos (
                projeto TEXT,
                documento TEXT,
                motivo TEXT,
                PRIMARY KEY (projeto, documento, motivo)
            )"""
        )
        self._db.commit()
        self._falhas_de_leitura = 0
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

    def _aprovadas(self) -> list[tuple[str, str, bytes, bool]]:
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
                # Com kind policy, a decisão é do pipeline: verde entra, hash quebrado é recusado.
                por_politica, motivos = self._fonte.aprovacao_por_politica(copia, sdd)
                resultado.append(
                    (sdd, commit_sdd, (copia / sdd).read_bytes(), por_politica or bool(motivos))
                )
            return resultado
        finally:
            shutil.rmtree(temporario, ignore_errors=True)

    def verificar(self, disparar: Callable[[str], object]) -> list[str]:
        primeira_leitura = not self._ja_leu()
        try:
            aprovadas = self._aprovadas()
        except subprocess.CalledProcessError as erro:
            # SDD-FAB-0010, RF05: sem a base neste ciclo, o vigia segue no próximo.
            print(f"base: cópia de {self._base} falhou, segue no próximo ciclo: {erro}", flush=True)
            return []
        novas = []
        for sdd, commit_sdd, conteudo, de_politica in aprovadas:
            if (
                not primeira_leitura
                and not de_politica
                and not self._aprovacoes.aprovada(self._projeto, sdd, conteudo)
            ):
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

    # Central (SPEC-DTF-0032, RF04 a RF07 e RF10): passos 1 e 2 do ciclo, antes do passo 3.

    def _avisar(self, notificador, documento: str, motivo: str, pr: int | None = None) -> bool:
        """Avisa uma vez por (documento, motivo); devolve se avisou agora."""
        with self._db:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO avisos VALUES (?, ?, ?)", (self._projeto, documento, motivo)
            )
        if cursor.rowcount != 1:
            return False
        numero = f" (PR #{pr})" if pr else ""
        notificador.avisar(f"{self._projeto}: {documento}{numero}: {motivo}")
        return True

    def _specs_ja_lidas(self) -> bool:
        return (
            self._db.execute(
                "SELECT 1 FROM specs_vistas WHERE projeto = ? LIMIT 1", (self._projeto,)
            ).fetchone()
            is not None
        )

    def _ver_spec(self, spec_id: str, content_sha256: str) -> bool:
        """Marca a SPEC como vista antes de compilar; devolve se ela é nova."""
        with self._db:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO specs_vistas VALUES (?, ?, ?)",
                (self._projeto, spec_id, content_sha256),
            )
        return cursor.rowcount == 1

    def _motivo_para_nao_compilar(self, spec_id: str) -> str | None:
        """RF06: SPEC já atendida por SDD da base, ou projeto sem SDD enxuta."""
        temporario = Path(tempfile.mkdtemp(prefix="fabrica-vigia-central-"))
        try:
            copia = preparar_copia(self._repo, self._base, temporario / "copia")
            sdd = self._fonte.sdd_com_origem(copia, spec_id)
            if sdd:
                return f"{spec_id} já está em source_docs de {sdd}: vista sem compilar"
            if self._fonte.formato_da_sdd(copia, [spec_id]) != "enxuta":
                return (
                    f"{spec_id}: o projeto está abaixo do framework 2.7.0, sem SDD enxuta: "
                    "vista sem compilar"
                )
            return None
        finally:
            shutil.rmtree(temporario, ignore_errors=True)

    def _prs_do_central(self, escrita, notificador, resultado: dict) -> None:
        for doc_id, numero in escrita.prs_da_fabrica():
            try:
                decisao = escrita.conferir(doc_id)
                if not decisao.get("valida"):
                    # Sem review de aprovador: segue aberta, sem aviso.
                    continue
                escrita.integrar(doc_id, decisao)
                resultado["integradas"].append(doc_id)
            except Exception as erro:  # noqa: BLE001 - toda parada vira aviso, e o ciclo segue
                # O núcleo não conhece as exceções do adaptador (EscritaRecusada): o motivo basta.
                self._avisar(notificador, doc_id, str(erro), numero)
                resultado["paradas"].append(doc_id)

    def _compilar(self, spec_id: str, descoberta, notificador, resultado: dict) -> None:
        try:
            sessao = descoberta.compilar(spec_id)
        except Exception as erro:  # noqa: BLE001 - toda parada vira aviso, e o ciclo segue
            self._avisar(notificador, spec_id, f"compilação não abriu: {erro}")
            resultado["paradas"].append(spec_id)
            return
        estado = descoberta.estado(sessao)
        if estado == AGUARDANDO_APROVACAO:
            try:
                descoberta.publicar_por_politica(sessao)
            except Exception as erro:  # noqa: BLE001 - toda parada vira aviso, e o ciclo segue
                pr = descoberta.dados(sessao).get("pr")
                self._avisar(notificador, spec_id, str(erro), pr)
                resultado["paradas"].append(spec_id)
                return
            resultado["compiladas"].append(spec_id)
            return
        if estado == AGUARDANDO_RESPOSTAS:
            motivo = (
                f"a compilação pediu esclarecimento na sessão {sessao}: "
                f"fabrica descobrir {self._projeto.lower()} --retomar {sessao}"
            )
        elif estado == PARADA:
            motivo = "compilação parada: " + "; ".join(descoberta.dados(sessao)["problemas"])
        else:
            motivo = f"compilação na sessão {sessao} terminou em {estado}"
        self._avisar(notificador, spec_id, motivo)
        resultado["paradas"].append(spec_id)

    def verificar_central(self, escrita, leitura, descoberta, notificador) -> dict:
        """Passo 1: PRs de documento da fábrica no central. Passo 2: SPECs aprovadas.

        Falha do `gh` ou do `git fetch` não para o ciclo: o passo 3 (SDDs na base) segue.
        """
        resultado: dict = {"integradas": [], "compiladas": [], "paradas": []}
        try:
            self._prs_do_central(escrita, notificador, resultado)
            specs = leitura.specs_aprovadas()
        except FalhaDePublicacao as erro:
            self._falhas_de_leitura += 1
            if self._falhas_de_leitura == FALHAS_DE_LEITURA_ANTES_DO_AVISO:
                self._avisar(
                    notificador,
                    "central",
                    f"leitura do central falhou em {FALHAS_DE_LEITURA_ANTES_DO_AVISO} ciclos "
                    f"seguidos: {erro}",
                )
            print(f"central: leitura falhou, segue na base: {erro}", flush=True)
            return resultado
        self._falhas_de_leitura = 0
        for spec_id, motivos in leitura.recusadas.items():
            self._avisar(notificador, spec_id, "validate_state.py: " + "; ".join(motivos))
        primeira_leitura = not self._specs_ja_lidas()
        for spec_id, content_sha256 in specs:
            if not self._ver_spec(spec_id, content_sha256) or primeira_leitura:
                continue
            try:
                motivo = self._motivo_para_nao_compilar(spec_id)
            except subprocess.CalledProcessError as erro:
                # SDD-FAB-0010, RF05: a SPEC segue vista; compilar de novo é decisão do owner.
                self._avisar(notificador, spec_id, f"cópia da base falhou: {erro}")
                resultado["paradas"].append(spec_id)
                continue
            if motivo:
                print(motivo, flush=True)
                continue
            self._compilar(spec_id, descoberta, notificador, resultado)
        if primeira_leitura:
            # Marca o projeto como lido mesmo sem nenhuma SPEC aprovada.
            self._ver_spec("", "")
        return resultado
