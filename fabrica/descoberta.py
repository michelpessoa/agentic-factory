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
from collections.abc import Callable
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
LIMITE_DO_RESUMO = 200

PERGUNTANDO = "PERGUNTANDO"
AGUARDANDO_RESPOSTAS = "AGUARDANDO_RESPOSTAS"
AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
PUBLICANDO = "PUBLICANDO"
APROVADA = "APROVADA"
PARADA = "PARADA"
NO_CENTRAL = "NO_CENTRAL"
PEDIDO_DE_COMPILACAO = "Compilar a SDD enxuta de {spec_id}"


class DescobertaInvalida(Exception):
    pass


class Redator(Protocol):
    """O que a descoberta precisa do adaptador do framework."""

    def escrever_sdd(
        self, repo: Path, rascunho: dict, codigo: str, owner: str, hoje: str, status: str,
        sdd_id: str | None = None, origens: list = (),
    ) -> str: ...  # fmt: skip
    def problemas_de_entrada(self, repo: Path, caminho_sdd: str) -> list[str]: ...
    def formato_da_sdd(self, repo: Path, origens: list) -> str: ...
    def problemas_de_redacao(self, repo: Path, caminho_sdd: str) -> list[str]: ...
    def origem(self, doc_id: str) -> dict: ...
    def aprovar_por_politica(self, repo: Path, caminho_sdd: str, agora: str) -> dict: ...
    def aprovacao_por_politica(self, repo: Path, caminho_sdd: str) -> tuple[bool, list[str]]: ...


class Escritor(Protocol):
    """O que a descoberta precisa do adaptador para abrir documento no central."""

    def tipo_do_central(self, sizing: str) -> str | None: ...
    def montar(self, documento: dict, owner: str, hoje: str) -> tuple[str, str]: ...
    def problemas(self, texto: str) -> list[str]: ...
    def abrir_pr(self, doc_id: str, tipo: str, texto: str, titulo: str) -> int: ...


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


def problemas_do_formato(rascunho: dict, formato: str, origens: list[str]) -> list[str]:
    """Campos que cada formato de SDD pede. O formato vem do adaptador, como texto opaco."""
    problemas = []
    if formato == "enxuta":
        specs = [o for o in origens if o.startswith("SPEC-")]
        for campo in ("arquitetura", "especificacao"):
            if rascunho[campo] is not None:
                problemas.append(f"SDD enxuta: {campo} vem null, o desenho fica na SPEC de origem")
        for r in rascunho["requisitos"]:
            rf = r["id"]
            if r["aceite"] is not None:
                problemas.append(
                    f"SDD enxuta: {rf} traz aceite, que vem null: o critério EARS fica na SPEC de origem"
                )
            if r["origem"] not in specs:
                problemas.append(
                    f"{rf} com origem {r['origem']!r} fora das SPECs da sessão: {', '.join(specs)}"
                )
            if len(r["requisito"]) > LIMITE_DO_RESUMO:
                problemas.append(
                    f"{rf} com requisito de {len(r['requisito'])} caracteres: "
                    f"o limite da SDD enxuta é {LIMITE_DO_RESUMO}"
                )
        return problemas
    for campo in ("arquitetura", "especificacao"):
        if rascunho[campo] is None:
            problemas.append(f"SDD completa: {campo} é obrigatório")
    for r in rascunho["requisitos"]:
        if r["aceite"] is None:
            problemas.append(f"SDD completa: {r['id']} sem aceite")
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
        escritor: Escritor | None = None,
        progresso: Callable[[str, dict], None] | None = None,
    ):
        self.projeto = projeto
        self.escritor = escritor
        self._progresso = progresso
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

    def criar(self, ideia: str, origens: list | tuple = ()) -> str:
        sessao = str(uuid.uuid4())
        dados = {"ideia": ideia, "conversa": [], "tentativa": 1, "problemas": [], "custo_usd": 0}
        dados["origens"] = list(origens)
        with self._db:
            self._db.execute(
                "INSERT INTO descobertas VALUES (?, ?, ?, ?, ?)",
                (sessao, self.projeto.codigo, PERGUNTANDO, json.dumps(dados),
                 datetime.now(UTC).isoformat()),
            )  # fmt: skip
        return sessao

    def compilar(self, spec_id: str) -> str:
        """Sessão disparada pelo vigia: a SPEC aprovada vira SDD sem humano (SPEC-DTF-0032, RF07).

        O agente roda até ter rascunho, perguntas ou parada; ninguém responde dentro do ciclo.
        """
        sessao = self.criar(
            PEDIDO_DE_COMPILACAO.format(spec_id=spec_id), [self.redator.origem(spec_id)]
        )
        dados = self.dados(sessao)
        dados["automatica"] = True
        self._salvar(sessao, self.estado(sessao), dados)
        self.avancar(sessao)
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

    def _avisar(self, evento: str, **detalhes) -> None:
        if self._progresso:
            self._progresso(evento, detalhes)

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
        if "sdd" not in dados:
            copia = self._copia_da_base(sessao, "formato")
            try:
                dados["sdd"] = self.redator.formato_da_sdd(copia, dados.get("origens", []))
            finally:
                shutil.rmtree(copia, ignore_errors=True)
        entrada = {
            "ideia": dados["ideia"],
            "conversa": dados["conversa"],
            "rodadas_restantes": rodadas_restantes,
            "problemas": dados["problemas"],
            "sdd": dados["sdd"],
            "origens": [
                {k: o[k] for k in ("id", "tipo", "titulo", "sizing", "texto")}
                for o in dados.get("origens", [])
            ],
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
        self._avisar(
            "agente",
            tentativa=dados["tentativa"],
            tentativas=TENTATIVAS_DE_RASCUNHO,
            respostas=any(r["respostas"] for r in dados["conversa"]),
        )
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
            self._avisar(
                "perguntas",
                quantidade=len(resposta["perguntas"]),
                rodada=len(dados["conversa"]),
                rodadas=RODADAS_DE_PERGUNTAS,
            )
            self._salvar(sessao, AGUARDANDO_RESPOSTAS, dados)
            return
        if resposta["status"] == "documento":
            self._receber_documento(sessao, dados, resposta["documento"])
            return
        if resposta["rascunho"] is None:
            self._recusar(sessao, dados, ["status rascunho sem rascunho"])
            return
        sizing = resposta["rascunho"]["sizing"]
        if not dados.get("origens") and self.escritor:
            esperado = self.escritor.tipo_do_central(sizing)
            if esperado:
                self._recusar(
                    sessao,
                    dados,
                    [
                        f"sizing {sizing} sem --origem pede rascunho de {esperado} no central, não de SDD"
                    ],
                )
                return
        self._receber_rascunho(sessao, dados, resposta["rascunho"])

    def _receber_documento(self, sessao: str, dados: dict, documento: dict | None) -> None:
        """Sem origem, acima de `small`: o documento é do central e entra lá por PR."""
        if documento is None:
            self._recusar(sessao, dados, ["status documento sem documento"])
            return
        if dados.get("origens"):
            self._recusar(
                sessao,
                dados,
                ["com --origem a descoberta entrega rascunho de SDD, não documento do central"],
            )
            return
        if self.escritor is None:
            self._recusar(
                sessao, dados, ["documento do central sem escrita no central configurada"]
            )
            return
        sizing, tipo = documento["sizing"], documento["tipo"]
        esperado = self.escritor.tipo_do_central(sizing)
        if esperado is None:
            self._recusar(
                sessao, dados, [f"sizing {sizing} gera rascunho de SDD, não documento do central"]
            )
            return
        if tipo != esperado:
            self._recusar(sessao, dados, [f"sizing {sizing} pede {esperado}, não {tipo}"])
            return
        self._validando(dados, tipo, sizing)
        doc_id, texto = self.escritor.montar(documento, self.projeto.owner, _hoje())
        problemas = self.escritor.problemas(texto)
        if problemas:
            self._recusar(sessao, dados, problemas)
            return
        self._avisar(
            "pr_central",
            doc_id=doc_id,
            tipo=tipo,
            tentativa=dados["tentativa"],
            tentativas=TENTATIVAS_DE_RASCUNHO,
        )
        pr = self.escritor.abrir_pr(doc_id, tipo, texto, documento["titulo"])
        dados |= {"documento": documento, "doc_id": doc_id, "pr": pr, "problemas": []}
        self._salvar(sessao, NO_CENTRAL, dados)

    def _validando(self, dados: dict, tipo: str, sizing: str) -> None:
        self._avisar(
            "validando",
            tipo=tipo,
            sizing=sizing,
            origens=[o["id"] for o in dados.get("origens", [])],
            tentativa=dados["tentativa"],
            tentativas=TENTATIVAS_DE_RASCUNHO,
        )

    def _receber_rascunho(self, sessao: str, dados: dict, rascunho: dict) -> None:
        self._validando(dados, "SDD", rascunho["sizing"])
        problemas = problemas_do_rascunho(rascunho)
        problemas += problemas_do_formato(
            rascunho, dados["sdd"], [o["id"] for o in dados.get("origens", [])]
        )
        if not problemas:
            # Os validadores do framework olham a SDD como ela vai entrar na base: aprovada.
            copia = self._copia_da_base(sessao, "validacao")
            try:
                caminho = self.redator.escrever_sdd(
                    copia, rascunho, self.projeto.codigo, self.projeto.owner, _hoje(), "approved",
                    origens=dados.get("origens", []),
                )  # fmt: skip
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
                sdd_id, origens=dados.get("origens", []),
            )  # fmt: skip
            if dados["sdd"] == "enxuta":
                problemas = self.redator.problemas_de_redacao(copia, caminho)
            if not problemas:
                arquivo = rascunho_dir / f"{sdd_id}.md"
                shutil.copy(copia / caminho, arquivo)
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        if problemas:
            self._recusar(sessao, dados, problemas)
            return
        dados |= {"rascunho": rascunho, "sdd_id": sdd_id, "arquivo": str(arquivo), "problemas": []}
        self._avisar(
            "pronto",
            sdd_id=sdd_id,
            tentativa=dados["tentativa"],
            tentativas=TENTATIVAS_DE_RASCUNHO,
            automatica=bool(dados.get("automatica")),
        )
        self._salvar(sessao, AGUARDANDO_APROVACAO, dados)

    def _recusar(self, sessao: str, dados: dict, problemas: list[str]) -> None:
        dados.setdefault("recusas", []).append(
            {"tentativa": dados["tentativa"], "problemas": problemas}
        )
        self._avisar(
            "recusa",
            tentativa=dados["tentativa"],
            tentativas=TENTATIVAS_DE_RASCUNHO,
            problemas=len(problemas),
            parando=dados["tentativa"] >= TENTATIVAS_DE_RASCUNHO,
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
        return self._publicar(sessao, politica=False)

    def publicar_por_politica(self, sessao: str) -> int:
        """SDD da compilação do vigia, approved por política e sem `fabrica aprovar` (RF08)."""
        if not self.dados(sessao).get("automatica"):
            raise DescobertaInvalida("sessão interativa termina em fabrica aprovar")
        return self._publicar(sessao, politica=True)

    def _publicar(self, sessao: str, politica: bool) -> int:
        estado = self.estado(sessao)
        if estado not in {AGUARDANDO_APROVACAO, PUBLICANDO}:
            raise DescobertaInvalida(f"sessão em {estado}: nada para aprovar")
        dados = self.dados(sessao)
        if estado == AGUARDANDO_APROVACAO:
            try:
                dados["pr"] = self._abrir_pr(sessao, dados, politica)
            except DescobertaInvalida as erro:
                if politica:
                    dados["problemas"] = [str(erro)]
                    self._salvar(sessao, PARADA, dados)
                raise
            self._salvar(sessao, PUBLICANDO, dados)
        situacao, detalhe = self.github.esperar_checks(dados["pr"])
        if situacao not in {"passou", "sem_checks"}:
            raise DescobertaInvalida(f"CI da PR #{dados['pr']}: {situacao} {detalhe}")
        self.github.fazer_merge_em_develop(dados["pr"])
        self._salvar(sessao, APROVADA, dados)
        return dados["pr"]

    def _abrir_pr(self, sessao: str, dados: dict, politica: bool = False) -> int:
        sdd_id = dados["sdd_id"]
        copia = self._copia_da_base(sessao, "publicacao")
        try:
            caminho = self.redator.escrever_sdd(
                copia, dados["rascunho"], self.projeto.codigo, self.projeto.owner, _hoje(),
                "approved", sdd_id, origens=dados.get("origens", []),
            )  # fmt: skip
            problemas = self.redator.problemas_de_entrada(copia, caminho)
            if problemas:
                raise DescobertaInvalida(f"a base mudou e a SDD não passa mais: {problemas}")
            if politica:
                agora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                self.redator.aprovar_por_politica(copia, caminho, agora)
                aprovada, motivos = self.redator.aprovacao_por_politica(copia, caminho)
                if not aprovada:
                    raise DescobertaInvalida(f"aprovação por política reprovada: {motivos}")
            else:
                # Registrada antes do push: o vigia pode ver a SDD na base a qualquer momento.
                self.aprovacoes.registrar(
                    self.projeto.codigo, caminho, (copia / caminho).read_bytes(),
                    f"descoberta {sessao}",
                )  # fmt: skip
            ramo = f"feature/{sdd_id.lower()}-{sessao[:8]}"
            subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", "-C", str(copia), "switch", "-q", "-c",
                 ramo],
                check=True,
            )  # fmt: skip
            como = "aprovada por política" if politica else "aprovada no terminal"
            commit(copia, f"docs(sdd): {sdd_id} {como}")
            enviar_ramo(copia, self.projeto.repo, ramo)
            return self.github.abrir_pr(
                ramo,
                self.projeto.base,
                f"docs(sdd): {sdd_id}",
                (
                    f"{sdd_id}, compilada pelo vigia e aprovada por política.\n\n"
                    if politica
                    else f"{sdd_id}, nascida da descoberta e aprovada pelo owner no terminal.\n\n"
                )
                + "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n",
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
