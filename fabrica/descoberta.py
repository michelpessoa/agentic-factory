"""Descoberta: da ideia do owner até uma SDD aprovada por ele no terminal.

O agente só pergunta e devolve campos. Quem escreve a SDD é o adaptador do framework, quem confere são
os validadores, e quem aprova é o humano. Depois da aprovação, a SDD vai para a base por PR, e o vigia
dispara o pipeline como para qualquer outra SDD.
"""

import json
import shutil
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio, RespostaRecusada, schema_da_etapa
from fabrica.execucao import AgentRunner, preparar_copia
from fabrica.publicacao import commit, enviar_ramo

DIR_AGENTES = Path(__file__).resolve().parent.parent / "agents"
MODELO_DESCOBRIDOR = "claude-opus-5-5"
RODADAS_DE_PERGUNTAS = 4
TENTATIVAS_DE_RASCUNHO = 3
PREFIXOS_PROIBIDOS = ("docs/", ".github/")

PERGUNTANDO = "PERGUNTANDO"
AGUARDANDO_RESPOSTAS = "AGUARDANDO_RESPOSTAS"
AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
PUBLICANDO = "PUBLICANDO"
APROVADA = "APROVADA"
PARADA = "PARADA"


class DescobertaInvalida(Exception):
    pass


class Redator(Protocol):
    """O que a descoberta precisa do adaptador do framework."""

    def escrever_sdd(
        self, repo: Path, rascunho: dict, codigo: str, owner: str, hoje: str, status: str,
        sdd_id: str | None = None,
    ) -> str: ...  # fmt: skip
    def problemas_de_entrada(self, repo: Path, caminho_sdd: str) -> list[str]: ...


def problemas_do_rascunho(rascunho: dict) -> list[str]:
    """Regras que o schema não expressa. Vão ao agente na tentativa seguinte."""
    problemas = []
    ids = [r["id"] for r in rascunho["requisitos"]]
    if len(set(ids)) != len(ids):
        problemas.append("RF-ID repetido")
    caminhos = {a for r in rascunho["requisitos"] for a in r["arquivos"]}
    caminhos |= {a for t in rascunho["tarefas"] for a in t["arquivos"]}
    for caminho in sorted(caminhos):
        if ".." in caminho.split("/") or caminho.startswith(PREFIXOS_PROIBIDOS):
            problemas.append(f"arquivo fora do código do projeto: {caminho}")
    if rascunho["sizing"] == "medium" and len(ids) > 1 and not rascunho["tarefas"]:
        problemas.append("sizing medium com mais de um requisito precisa de tarefas")
    if rascunho["sizing"] == "small" and (len(ids) > 3 or len(caminhos) > 4):
        problemas.append("small vai até 3 requisitos e 4 arquivos: use medium com tarefas")
    citados = {c["criterio"].split(":")[0].strip() for c in rascunho["criterios"]}
    for rf in ids:
        if rf not in citados:
            problemas.append(f"{rf} sem critério de aceite que comece por '{rf}:'")
    for tarefa in rascunho["tarefas"]:
        for rf in tarefa["requisitos"]:
            if rf not in ids:
                problemas.append(f"tarefa cita {rf}, que não existe")
    return problemas


class Descoberta:
    def __init__(
        self,
        projeto,
        caminho_db: Path | str,
        cartorio: Cartorio,
        runner: AgentRunner,
        redator: Redator,
        aprovacoes: Aprovacoes,
        github,
        dir_trabalho: Path,
    ):
        self.projeto = projeto
        self.cartorio = cartorio
        self.runner = runner
        self.redator = redator
        self.aprovacoes = aprovacoes
        self.github = github
        self.dir_trabalho = dir_trabalho
        self._db = sqlite3.connect(caminho_db)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS descobertas (
                id TEXT PRIMARY KEY,
                projeto TEXT NOT NULL,
                estado TEXT NOT NULL,
                dados TEXT NOT NULL,
                criada TEXT NOT NULL
            )"""
        )
        self._db.commit()

    # Sessão

    def criar(self, ideia: str) -> str:
        sessao = str(uuid.uuid4())
        dados = {"ideia": ideia, "conversa": [], "tentativa": 1, "problemas": [], "custo_usd": 0}
        with self._db:
            self._db.execute(
                "INSERT INTO descobertas VALUES (?, ?, ?, ?, ?)",
                (sessao, self.projeto.codigo, PERGUNTANDO, json.dumps(dados),
                 datetime.now(UTC).isoformat()),
            )  # fmt: skip
        return sessao

    def estado(self, sessao: str) -> str:
        return self._linha(sessao)[0]

    def dados(self, sessao: str) -> dict:
        return json.loads(self._linha(sessao)[1])

    def _linha(self, sessao: str) -> tuple[str, str]:
        linha = self._db.execute(
            "SELECT estado, dados FROM descobertas WHERE id = ? AND projeto = ?",
            (sessao, self.projeto.codigo),
        ).fetchone()
        if linha is None:
            raise KeyError(sessao)
        return linha

    def _salvar(self, sessao: str, estado: str, dados: dict) -> None:
        with self._db:
            self._db.execute(
                "UPDATE descobertas SET estado = ?, dados = ? WHERE id = ?",
                (estado, json.dumps(dados, ensure_ascii=False), sessao),
            )

    # Conversa

    def avancar(self, sessao: str) -> str:
        """Chama o agente até ter perguntas para o humano, um rascunho válido ou uma parada."""
        while self.estado(sessao) == PERGUNTANDO:
            self._rodada(sessao)
        return self.estado(sessao)

    def responder(self, sessao: str, respostas: list[str]) -> None:
        if self.estado(sessao) != AGUARDANDO_RESPOSTAS:
            raise DescobertaInvalida(f"sessão em {self.estado(sessao)}, sem perguntas abertas")
        dados = self.dados(sessao)
        perguntas = dados["conversa"][-1]["perguntas"]
        if len(respostas) != len(perguntas):
            raise DescobertaInvalida(f"{len(perguntas)} perguntas, {len(respostas)} respostas")
        dados["conversa"][-1]["respostas"] = respostas
        self._salvar(sessao, PERGUNTANDO, dados)

    def _rodada(self, sessao: str) -> None:
        dados = self.dados(sessao)
        rodadas_restantes = RODADAS_DE_PERGUNTAS - len(dados["conversa"])
        entrada = {
            "ideia": dados["ideia"],
            "conversa": dados["conversa"],
            "rodadas_restantes": rodadas_restantes,
            "problemas": dados["problemas"],
        }
        contrato = self.cartorio.emitir(
            sessao, self.projeto.codigo, "descoberta", dados["tentativa"], entrada
        )
        prompt = (
            f"{(DIR_AGENTES / 'descobridor.md').read_text(encoding='utf-8')}\n\n## Contrato\n\n"
            f"```json\n{json.dumps(contrato, ensure_ascii=False, indent=2)}\n```\n"
        )
        vazio = self.dir_trabalho / sessao / "vazio"
        vazio.mkdir(parents=True, exist_ok=True)
        execucao = self.runner.executar(
            prompt, schema_da_etapa("descoberta"), vazio, MODELO_DESCOBRIDOR, []
        )
        dados["custo_usd"] += execucao.custo_usd or 0
        try:
            resposta = self.cartorio.receber(contrato["contrato_id"], execucao.resposta)
        except RespostaRecusada as erro:
            self._recusar(sessao, dados, [f"resposta recusada: {erro}"])
            return
        if resposta["status"] == "perguntas":
            if rodadas_restantes <= 0 or not resposta["perguntas"]:
                self._recusar(sessao, dados, ["sem rodadas de perguntas: entregue o rascunho"])
                return
            dados["conversa"].append({"perguntas": resposta["perguntas"], "respostas": []})
            self._salvar(sessao, AGUARDANDO_RESPOSTAS, dados)
            return
        if resposta["rascunho"] is None:
            self._recusar(sessao, dados, ["status rascunho sem rascunho"])
            return
        self._receber_rascunho(sessao, dados, resposta["rascunho"])

    def _receber_rascunho(self, sessao: str, dados: dict, rascunho: dict) -> None:
        problemas = problemas_do_rascunho(rascunho)
        if not problemas:
            # Os validadores do framework olham a SDD como ela vai entrar na base: aprovada.
            copia = self._copia_da_base(sessao, "validacao")
            try:
                caminho = self.redator.escrever_sdd(
                    copia, rascunho, self.projeto.codigo, self.projeto.owner, _hoje(), "approved"
                )
                problemas = self.redator.problemas_de_entrada(copia, caminho)
            finally:
                shutil.rmtree(copia, ignore_errors=True)
        if problemas:
            self._recusar(sessao, dados, problemas)
            return
        sdd_id = Path(caminho).stem
        rascunho_dir = self.dir_trabalho / sessao
        copia = self._copia_da_base(sessao, "leitura")
        try:
            self.redator.escrever_sdd(
                copia, rascunho, self.projeto.codigo, self.projeto.owner, _hoje(), "draft",
                sdd_id,
            )  # fmt: skip
            arquivo = rascunho_dir / f"{sdd_id}.md"
            shutil.copy(copia / caminho, arquivo)
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        dados |= {"rascunho": rascunho, "sdd_id": sdd_id, "arquivo": str(arquivo), "problemas": []}
        self._salvar(sessao, AGUARDANDO_APROVACAO, dados)

    def _recusar(self, sessao: str, dados: dict, problemas: list[str]) -> None:
        dados.setdefault("recusas", []).append(
            {"tentativa": dados["tentativa"], "problemas": problemas}
        )
        if dados["tentativa"] >= TENTATIVAS_DE_RASCUNHO:
            dados["problemas"] = problemas
            self._salvar(sessao, PARADA, dados)
            return
        dados["tentativa"] += 1
        dados["problemas"] = problemas
        self._salvar(sessao, PERGUNTANDO, dados)

    def _copia_da_base(self, sessao: str, nome: str) -> Path:
        destino = self.dir_trabalho / sessao / nome
        shutil.rmtree(destino, ignore_errors=True)
        return preparar_copia(self.projeto.repo, self.projeto.base, destino)

    # Aprovação: só pelo comando humano

    def aprovar(self, sessao: str) -> int:
        """Grava a SDD aprovada na base por PR. Retoma do ponto em que parou."""
        estado = self.estado(sessao)
        if estado not in {AGUARDANDO_APROVACAO, PUBLICANDO}:
            raise DescobertaInvalida(f"sessão em {estado}: nada para aprovar")
        dados = self.dados(sessao)
        if estado == AGUARDANDO_APROVACAO:
            dados["pr"] = self._abrir_pr(sessao, dados)
            self._salvar(sessao, PUBLICANDO, dados)
        situacao, detalhe = self.github.esperar_checks(dados["pr"])
        if situacao not in {"passou", "sem_checks"}:
            raise DescobertaInvalida(f"CI da PR #{dados['pr']}: {situacao} {detalhe}")
        self.github.fazer_merge_em_develop(dados["pr"])
        self._salvar(sessao, APROVADA, dados)
        return dados["pr"]

    def _abrir_pr(self, sessao: str, dados: dict) -> int:
        sdd_id = dados["sdd_id"]
        copia = self._copia_da_base(sessao, "publicacao")
        try:
            caminho = self.redator.escrever_sdd(
                copia, dados["rascunho"], self.projeto.codigo, self.projeto.owner, _hoje(),
                "approved", sdd_id,
            )  # fmt: skip
            problemas = self.redator.problemas_de_entrada(copia, caminho)
            if problemas:
                raise DescobertaInvalida(f"a base mudou e a SDD não passa mais: {problemas}")
            # Registrada antes do push: o vigia pode ver a SDD na base a qualquer momento.
            self.aprovacoes.registrar(
                self.projeto.codigo, caminho, (copia / caminho).read_bytes(), f"descoberta {sessao}"
            )
            ramo = f"feature/sdd-{sdd_id.lower()}-{sessao[:8]}"
            subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", "-C", str(copia), "switch", "-q", "-c",
                 ramo],
                check=True,
            )  # fmt: skip
            commit(copia, f"docs(sdd): {sdd_id} aprovada no terminal")
            enviar_ramo(copia, self.projeto.repo, ramo)
            return self.github.abrir_pr(
                ramo,
                self.projeto.base,
                f"docs(sdd): {sdd_id}",
                f"{sdd_id}, nascida da descoberta e aprovada pelo owner no terminal.\n\n"
                "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n",
            )
        finally:
            shutil.rmtree(copia, ignore_errors=True)

    def aprovar_existente(self, caminho_sdd: str) -> str:
        """SDD escrita à mão, já na base com status approved: registra o conteúdo aprovado."""
        copia = self._copia_da_base("existente", str(uuid.uuid4()))
        try:
            arquivo = copia / caminho_sdd
            if not arquivo.is_file():
                raise DescobertaInvalida(f"{caminho_sdd} não existe em {self.projeto.base}")
            problemas = self.redator.problemas_de_entrada(copia, caminho_sdd)
            if problemas:
                raise DescobertaInvalida(f"SDD não passa na entrada: {problemas}")
            return self.aprovacoes.registrar(
                self.projeto.codigo, caminho_sdd, arquivo.read_bytes(), "terminal"
            )
        finally:
            shutil.rmtree(copia, ignore_errors=True)


def _hoje() -> str:
    return datetime.now(UTC).date().isoformat()
