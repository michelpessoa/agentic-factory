"""Orquestrador: um método por estado, e o estado salvo decide o próximo passo.

O núcleo não conhece o framework de documentação nem decide nada com LLM. Agentes entram só em
`AGENTE_RODANDO` e `VERIFY_SDD`, e o que respondem é conferido antes de valer.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import (
    Cartorio,
    RespostaRecusada,
    problemas_de_evidencia,
    schema_da_etapa,
)
from fabrica.decisao import Decisao, decidir_risco
from fabrica.estados import PAUSAS, TERMINAIS, Historico
from fabrica.execucao import AgentRunner, FalhaDeExecucao, aplicar_patch, preparar_copia
from fabrica.gates import (
    PADROES_DE_TESTE,
    ResultadoGate,
    gate_caminhos_protegidos,
    gate_escopo,
    gate_patch,
    gate_sizing,
    gate_so_testes,
    relatorio_de_reprovacao,
)
from fabrica.publicacao import (
    FalhaDePublicacao,
    commit,
    enviar_ramo,
    montar_corpo_pr,
    preparar_release,
)
from fabrica.roteamento import MODELO_POR_RISCO
from fabrica.verificacao import verificar

DIR_AGENTES = Path(__file__).resolve().parent.parent / "agents"
FERRAMENTAS_DESENVOLVEDOR = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
FERRAMENTAS_LEITURA = ["Read", "Grep", "Glob"]
MODELO_DECISOR = "claude-haiku-5-5"
MODELO_SEGURANCA = "claude-opus-5-5"
MAXIMO_DE_TENTATIVAS = 3
CONTEXTO_VIVO = "docs/fabrica/contexto.md"
LIMITE_CONTEXTO_VIVO_BYTES = 8000
LIMITE_DIFF_NO_CONTRATO = 50000


@dataclass(frozen=True)
class Projeto:
    codigo: str
    repo: str
    github: str
    base: str = "develop"
    principal: str = "main"
    permitidos: tuple[str, ...] = ()
    comandos: dict[str, str] = field(default_factory=dict)
    padroes_de_teste: tuple[str, ...] = PADROES_DE_TESTE
    owner: str = ""


class ExecucaoEmAberto(Exception):
    """Mesma SDD não roda duas vezes ao mesmo tempo: use `retomar` na execução existente."""


class FonteDeContrato(Protocol):
    def identificador(self) -> str: ...
    def problemas_de_entrada(self, repo: Path, caminho_sdd: str) -> list[str]: ...
    def compilar(self, repo: Path, caminho_sdd: str) -> dict: ...
    def caminhos_historicos(self) -> tuple[str, ...]: ...
    def arquivar(self, repo: Path, caminho_sdd: str, pr: int, data: str) -> bool: ...
    def registrar_verificacao(
        self, repo: Path, caminho_sdd: str, validacao: dict, base: str, head: str
    ) -> list[str]: ...


def _git(repo: Path, *args: str) -> str:
    resultado = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout.strip()


class Pipeline:
    def __init__(
        self,
        projeto: Projeto,
        historico: Historico,
        cartorio: Cartorio,
        fonte: FonteDeContrato,
        runner: AgentRunner,
        ambiente,
        github,
        notificador,
        dir_runs: Path,
        revisor_modelo: str = "claude-opus-5-5",
        *,
        aprovacoes: Aprovacoes,
    ):
        self.projeto = projeto
        self.aprovacoes = aprovacoes
        self.historico = historico
        self.cartorio = cartorio
        self.fonte = fonte
        self.runner = runner
        self.ambiente = ambiente
        self.github = github
        self.notificador = notificador
        self.dir_runs = dir_runs
        self.revisor_modelo = revisor_modelo
        self._acoes = {
            "DETECTADO": self._entrada,
            "ENTRADA_OK": self._rotear,
            "ROTEADO": self._apos_roteamento,
            "PLANEJANDO": self._planejar,
            "CONTRATO_EMITIDO": self._desenvolver,
            "AGENTE_RODANDO": self._retomar_agente,
            "RESPOSTA_VALIDA": self._apos_desenvolvimento,
            "TESTADOR_RODANDO": self._testar,
            "GATES_LOCAIS": self._gates_locais,
            "SEGURANCA": self._seguranca,
            "VERIFY_SDD": self._verificar,
            "PR_PARA_DEVELOP": self._abrir_pr,
            "CI_E2E": self._esperar_ci,
            "MERGE_EM_DEVELOP": self._merge,
            "ARQUIVAMENTO": self._arquivar,
            "RESPOSTA_RECUSADA": self._apos_recusa,
            "CORRECAO": self._preparar_correcao,
        }

    # Fluxo

    def iniciar(self, caminho_sdd: str) -> str:
        em_aberto = [
            run_id
            for run_id, projeto, sdd, estado in self.historico.listar()
            if projeto == self.projeto.codigo and sdd == caminho_sdd and estado not in TERMINAIS
        ]
        if em_aberto:
            raise ExecucaoEmAberto(f"{caminho_sdd} já tem execução em aberto: {em_aberto[0]}")
        run_id = self.historico.criar(
            self.projeto.codigo, caminho_sdd, {"tentativa": 1, "fonte": self.fonte.identificador()}
        )
        self.executar(run_id)
        return run_id

    def executar(self, run_id: str) -> str:
        while True:
            estado = self.historico.estado(run_id)
            if estado in TERMINAIS or estado in PAUSAS:
                return estado
            try:
                self._acoes[estado](run_id)
            except FalhaDeExecucao as erro:
                self._tratar_falha(run_id, estado, erro.causa, erro.detalhe)
            except FalhaDePublicacao as erro:
                self._tratar_falha(run_id, estado, "ambiente", str(erro))

    def decidir(self, run_id: str, risco: str) -> str:
        """Resposta do humano quando a confiança ficou abaixo do limiar."""
        if risco not in MODELO_POR_RISCO:
            raise ValueError(f"risco inválido: {risco}")
        self.historico.avancar(
            run_id,
            "ROTEADO",
            f"risco {risco}, decidido pelo humano",
            {"risco": risco, "modelo": MODELO_POR_RISCO[risco]},
        )
        return self.executar(run_id)

    def retomar(self, run_id: str) -> str:
        estado = self.historico.estado(run_id)
        if estado == "PAUSADA_DECISAO":
            raise ValueError("esta execução espera uma decisão: use `decidir`")
        if estado in PAUSAS:
            destino = self.historico.dados(run_id)["retomar_em"]
            self.historico.avancar(run_id, destino, "retomada pelo operador")
        return self.executar(run_id)

    def _tratar_falha(self, run_id: str, estado: str, causa: str, detalhe: str) -> None:
        destino_retomada = "CONTRATO_EMITIDO" if estado == "AGENTE_RODANDO" else estado
        if causa == "limite_uso":
            self._parar(run_id, "PAUSADA_LIMITE_USO", detalhe, {"retomar_em": destino_retomada})
        elif causa == "fora_do_contrato":
            self._recusar(run_id, detalhe)
        else:
            self._parar(run_id, "PAUSADA_AMBIENTE", detalhe, {"retomar_em": destino_retomada})

    def _parar(self, run_id: str, estado: str, motivo: str, dados: dict | None = None) -> None:
        self.historico.avancar(run_id, estado, motivo[:2000], dados)
        _, sdd = self.historico.projeto_e_sdd(run_id)
        self.notificador.avisar(f"{Path(sdd).stem}: {estado}. {motivo[:300]}")

    def _recusar(self, run_id: str, motivo: str) -> None:
        self.historico.avancar(run_id, "RESPOSTA_RECUSADA", motivo[:2000])

    def _reprovar(self, run_id: str, relatorio: dict, motivo: str) -> None:
        dados = self.historico.dados(run_id)
        if dados["tentativa"] >= MAXIMO_DE_TENTATIVAS:
            self._parar(run_id, "PARADA_LIMITE", motivo, {"relatorio": relatorio})
        else:
            self.historico.avancar(run_id, "CORRECAO", motivo[:2000], {"relatorio": relatorio})

    def _dir(self, run_id: str) -> Path:
        caminho = self.dir_runs / run_id
        caminho.mkdir(parents=True, exist_ok=True)
        return caminho

    # Etapas 1 a 3

    def _entrada(self, run_id: str) -> None:
        _, caminho_sdd = self.historico.projeto_e_sdd(run_id)
        base = _ls_remote(self.projeto.repo, self.projeto.base)
        leitura = self._dir(run_id) / "leitura"
        shutil.rmtree(leitura, ignore_errors=True)
        preparar_copia(self.projeto.repo, base, leitura)

        if not (leitura / caminho_sdd).is_file():
            self._parar(
                run_id, "RECUSADA_ENTRADA", f"{caminho_sdd} não existe em {self.projeto.base}"
            )
            return
        sha_sdd = _ultimo_commit_do_arquivo(leitura, caminho_sdd)
        aprovador = self.github.quem_mergeou_o_commit(sha_sdd)
        if aprovador not in self.projeto.permitidos:
            self._parar(
                run_id,
                "RECUSADA_ENTRADA",
                f"SDD não chegou à base por PR de quem pode aprovar (merge por {aprovador!r})",
            )
            return
        conteudo = (leitura / caminho_sdd).read_bytes()
        if not self.aprovacoes.aprovada(self.projeto.codigo, caminho_sdd, conteudo):
            self._parar(
                run_id,
                "RECUSADA_ENTRADA",
                "este conteúdo da SDD não foi aprovado no terminal: rode `fabrica aprovar`",
            )
            return
        problemas = self.fonte.problemas_de_entrada(leitura, caminho_sdd)
        if problemas:
            self._parar(run_id, "PARADA_ESPECIFICACAO", "; ".join(problemas))
            return
        contexto = leitura / CONTEXTO_VIVO
        if contexto.is_file() and contexto.stat().st_size > LIMITE_CONTEXTO_VIVO_BYTES:
            self._parar(
                run_id,
                "PARADA_ESPECIFICACAO",
                f"{CONTEXTO_VIVO} passou de {LIMITE_CONTEXTO_VIVO_BYTES} bytes: reduza antes de seguir",
            )
            return
        entrada = self.fonte.compilar(leitura, caminho_sdd)
        if contexto.is_file():
            entrada["contexto_vivo"] = contexto.read_text(encoding="utf-8")
        self.historico.avancar(
            run_id, "ENTRADA_OK", f"aprovada por {aprovador}", {"base": base, "entrada": entrada}
        )
        shutil.rmtree(leitura, ignore_errors=True)

    def _rotear(self, run_id: str) -> None:
        entrada = self.historico.dados(run_id)["entrada"]
        try:
            decisao = decidir_risco(entrada, _DecisorDoRun(self, run_id))
        except RespostaRecusada as erro:
            decisao = Decisao("alto", 0.0, f"resposta recusada: {erro}", "decisor")
        motivo = f"risco {decisao.risco} ({decisao.origem}, confiança {decisao.confianca}): {decisao.justificativa}"
        if not decisao.segura:
            self._parar(run_id, "PAUSADA_DECISAO", f"decisão com baixa confiança. {motivo}")
            return
        self.historico.avancar(
            run_id,
            "ROTEADO",
            motivo[:2000],
            {"risco": decisao.risco, "modelo": MODELO_POR_RISCO[decisao.risco]},
        )

    def _apos_roteamento(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        if dados["risco"] != "baixo" and not dados["entrada"].get("tarefas"):
            self.historico.avancar(run_id, "PLANEJANDO", "SDD sem tarefas e risco não baixo")
        else:
            self.historico.avancar(run_id, "CONTRATO_EMITIDO", "pronto para o desenvolvedor")

    def _chamar_agente(
        self,
        run_id: str,
        etapa: str,
        arquivo_prompt: str,
        entrada: dict,
        trabalho: Path,
        modelo: str,
        ferramentas: list[str],
        antes=None,
    ) -> dict:
        """O token nasce e morre na memória desta chamada: a retomada sempre emite outro."""
        tentativa = self.historico.dados(run_id)["tentativa"]
        contrato = self.cartorio.emitir(run_id, self.projeto.codigo, etapa, tentativa, entrada)
        if antes:
            antes()
        prompt = (
            f"{(DIR_AGENTES / arquivo_prompt).read_text(encoding='utf-8')}\n\n## Contrato\n\n"
            f"```json\n{json.dumps(contrato, ensure_ascii=False, indent=2)}\n```\n"
        )
        execucao = self.runner.executar(
            prompt, schema_da_etapa(etapa), trabalho, modelo, ferramentas
        )
        resposta = self.cartorio.receber(contrato["contrato_id"], execucao.resposta)
        self._somar_custo(run_id, execucao.custo_usd)
        return resposta

    def _planejar(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        leitura = self._dir(run_id) / "planejamento"
        shutil.rmtree(leitura, ignore_errors=True)
        preparar_copia(self.projeto.repo, dados["base"], leitura, self._ocultos())
        try:
            resposta = self._chamar_agente(
                run_id,
                "planejamento",
                "planejador.md",
                dados["entrada"],
                leitura,
                dados["modelo"],
                FERRAMENTAS_LEITURA,
            )
        except RespostaRecusada as erro:
            # O plano é auxílio: sem ele, o desenvolvedor trabalha direto pela SDD.
            self.historico.avancar(run_id, "CONTRATO_EMITIDO", f"plano recusado: {erro}"[:2000])
            return
        finally:
            shutil.rmtree(leitura, ignore_errors=True)
        if resposta["status"] == "bloqueado":
            self._parar(
                run_id, "PARADA_ESPECIFICACAO", resposta.get("bloqueio") or "plano bloqueado"
            )
            return
        permitidos = dados["entrada"]["arquivos_permitidos"]
        fora = sorted(
            {
                arquivo
                for tarefa in resposta["tarefas"]
                for arquivo in tarefa["arquivos"]
                if not gate_escopo(f"diff --git a/{arquivo} b/{arquivo}\n", permitidos).aprovado
            }
        )
        if fora:
            motivo = f"plano recusado, fora de arquivos_permitidos: {', '.join(fora)}"
            self.historico.avancar(run_id, "CONTRATO_EMITIDO", motivo)
            return
        entrada = dados["entrada"] | {"tarefas": resposta["tarefas"]}
        self.historico.avancar(
            run_id, "CONTRATO_EMITIDO", f"{len(resposta['tarefas'])} tarefas", {"entrada": entrada}
        )

    def _ocultos(self) -> tuple[str, ...]:
        return self.fonte.caminhos_historicos()

    # Etapa 5

    def _desenvolver(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        tentativa = dados["tentativa"]
        entrada = dados["entrada"] | ({"correcao": dados["relatorio"]} if tentativa > 1 else {})
        trabalho = self._preparar_trabalho(run_id, dados)
        try:
            resposta = self._chamar_agente(
                run_id,
                "desenvolvimento",
                "desenvolvedor.md",
                entrada,
                trabalho,
                dados["modelo"],
                FERRAMENTAS_DESENVOLVEDOR,
                lambda: self.historico.avancar(run_id, "AGENTE_RODANDO", f"tentativa {tentativa}"),
            )
        except RespostaRecusada as erro:
            self._recusar(run_id, str(erro))
            return
        if resposta["status"] == "bloqueado":
            self._parar(
                run_id, "PARADA_ESPECIFICACAO", resposta.get("bloqueio") or resposta["resumo"]
            )
            return
        problemas = problemas_de_evidencia(trabalho, resposta["evidencias"])
        if problemas:
            self._recusar(run_id, "; ".join(problemas))
            return
        patch = self.ambiente.extrair_patch(trabalho, dados["base"], self._ocultos())
        (self._dir(run_id) / f"tentativa-{tentativa}.patch").write_text(patch, encoding="utf-8")
        shutil.rmtree(trabalho, ignore_errors=True)
        self.historico.avancar(run_id, "RESPOSTA_VALIDA", resposta["resumo"][:500])

    def _preparar_trabalho(self, run_id: str, dados: dict) -> Path:
        trabalho = self._dir(run_id) / "trabalho"
        shutil.rmtree(trabalho, ignore_errors=True)
        preparar_copia(self.projeto.repo, dados["base"], trabalho, self._ocultos())
        if dados["tentativa"] > 1:
            for conteudo in self._patches(run_id, dados["tentativa"] - 1):
                aplicar_patch(trabalho, conteudo)
            _git(trabalho, "reset", "-q")
        return trabalho

    def _patches(self, run_id: str, tentativa: int) -> list[str]:
        """O patch do desenvolvedor e, se houver, o do testador, na ordem de aplicação."""
        arquivos = [f"tentativa-{tentativa}.patch", f"tentativa-{tentativa}-testes.patch"]
        caminhos = [self._dir(run_id) / nome for nome in arquivos]
        conteudos = [c.read_text(encoding="utf-8") for c in caminhos if c.is_file()]
        return [c for c in conteudos if c.strip()]

    def _retomar_agente(self, run_id: str) -> None:
        """Queda com o agente rodando: o contrato anterior morreu, emite outro."""
        self.historico.avancar(run_id, "CONTRATO_EMITIDO", "retomada após queda")

    def _somar_custo(self, run_id: str, custo: float | None) -> None:
        total = self.historico.dados(run_id).get("custo_usd", 0) + (custo or 0)
        self.historico.atualizar_dados(run_id, {"custo_usd": total})

    # Etapa 6

    def _apos_desenvolvimento(self, run_id: str) -> None:
        if self.historico.dados(run_id)["risco"] == "baixo":
            self.historico.avancar(run_id, "GATES_LOCAIS", "resposta dentro do contrato")
        else:
            self.historico.avancar(run_id, "TESTADOR_RODANDO", "resposta dentro do contrato")

    def _testar(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        tentativa = dados["tentativa"]
        caminho_delta = self._dir(run_id) / f"tentativa-{tentativa}-testes.patch"
        caminho_delta.unlink(missing_ok=True)
        trabalho = self._dir(run_id) / "testes"
        shutil.rmtree(trabalho, ignore_errors=True)
        preparar_copia(self.projeto.repo, dados["base"], trabalho, self._ocultos())
        patch_dev = (self._dir(run_id) / f"tentativa-{tentativa}.patch").read_text(encoding="utf-8")
        if patch_dev.strip():
            aplicar_patch(trabalho, patch_dev)
            commit(trabalho, "implementação em teste")
        ponto_de_partida = _git(trabalho, "rev-parse", "HEAD")
        entrada = {
            chave: dados["entrada"].get(chave)
            for chave in ("sdd_id", "requisitos", "criterios", "especificacao")
        } | {"diff": patch_dev[:LIMITE_DIFF_NO_CONTRATO]}
        try:
            resposta = self._chamar_agente(
                run_id,
                "testes",
                "testador.md",
                entrada,
                trabalho,
                dados["modelo"],
                FERRAMENTAS_DESENVOLVEDOR,
            )
        except RespostaRecusada as erro:
            self._recusar(run_id, str(erro))
            return
        if resposta["status"] == "bloqueado":
            self._parar(
                run_id, "PARADA_ESPECIFICACAO", resposta.get("bloqueio") or resposta["resumo"]
            )
            return
        problemas = problemas_de_evidencia(trabalho, resposta["evidencias"])
        if problemas:
            self._recusar(run_id, "; ".join(problemas))
            return
        delta = self.ambiente.extrair_patch(trabalho, ponto_de_partida, self._ocultos())
        shutil.rmtree(trabalho, ignore_errors=True)
        gate = gate_so_testes(delta, self.projeto.padroes_de_teste)
        if not gate.aprovado:
            self._recusar(run_id, gate.detalhe)
            return
        caminho_delta.write_text(delta, encoding="utf-8")
        self.historico.avancar(run_id, "GATES_LOCAIS", "testador concluiu")

    def _patch(self, run_id: str) -> str:
        tentativa = self.historico.dados(run_id)["tentativa"]
        return "".join(self._patches(run_id, tentativa))

    def _ramo(self, run_id: str) -> str:
        dados = self.historico.dados(run_id)
        return f"feature/{dados['entrada']['sdd_id'].lower()}-{run_id[:8]}-t{dados['tentativa']}"

    def _candidato(self, run_id: str, recriar: bool = False) -> Path:
        """Clone limpo no host com o patch aplicado. Nunca a cópia que o agente tocou."""
        candidato = self._dir(run_id) / "candidato"
        if candidato.exists() and not recriar:
            return candidato
        shutil.rmtree(candidato, ignore_errors=True)
        dados = self.historico.dados(run_id)
        preparar_copia(self.projeto.repo, dados["base"], candidato)
        for conteudo in self._patches(run_id, dados["tentativa"]):
            aplicar_patch(candidato, conteudo)
        _git(candidato, "switch", "-q", "-c", self._ramo(run_id))
        entrada = dados["entrada"]
        commit(candidato, f"feat: {entrada['titulo']} ({entrada['sdd_id']})")
        return candidato

    def _copia_para_gate(self, run_id: str, nome: str) -> Path:
        copia = self._dir(run_id) / f"gate-{nome}"
        shutil.rmtree(copia, ignore_errors=True)
        candidato = self._candidato(run_id)
        preparar_copia(candidato, "HEAD", copia)
        return copia

    def _gates_locais(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        entrada = dados["entrada"]
        patch = self._patch(run_id)
        resultados = [gate_patch(patch)]
        if resultados[0].aprovado:
            sizing = gate_sizing(patch, entrada.get("sizing"))
            if not sizing.aprovado:
                self._parar(run_id, "PARADA_ESPECIFICACAO", sizing.detalhe)
                return
            resultados += [
                gate_escopo(patch, entrada["arquivos_permitidos"]),
                gate_caminhos_protegidos(patch, entrada["arquivos_permitidos"], dados["risco"]),
            ]
        if all(g.aprovado for g in resultados):
            self._candidato(run_id, recriar=True)
            for nome, comando in self.projeto.comandos.items():
                resultados.append(self._rodar_comando(run_id, nome, comando))
        self._concluir_gates(run_id, resultados, "SEGURANCA")

    def _rodar_comando(self, run_id: str, nome: str, comando: str) -> ResultadoGate:
        copia = self._copia_para_gate(run_id, nome)
        try:
            codigo, saida = self.ambiente.rodar(copia, comando)
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        if codigo in {124, 127}:
            raise FalhaDeExecucao("ambiente", f"{nome}: exit {codigo}: {saida[-500:]}")
        return ResultadoGate(nome, codigo == 0, "" if codigo == 0 else saida[-2000:])

    def _concluir_gates(self, run_id: str, resultados: list[ResultadoGate], proximo: str) -> None:
        dados = self.historico.dados(run_id)
        anteriores = dados.get("gates", []) if proximo != "SEGURANCA" else []
        registro = anteriores + [
            f"{g.nome}: {'ok' if g.aprovado else 'reprovado'}" for g in resultados
        ]
        self.historico.atualizar_dados(run_id, {"gates": registro})
        if all(g.aprovado for g in resultados):
            self.historico.avancar(run_id, proximo, "gates aprovados")
            return
        relatorio = relatorio_de_reprovacao(resultados, dados["tentativa"])
        self._reprovar(run_id, relatorio, "; ".join(relatorio["evidencias"]))

    def _seguranca(self, run_id: str) -> None:
        copia = self._copia_para_gate(run_id, "seguranca")
        try:
            resultados = []
            for nome, varredura in (
                ("segredos", self.ambiente.procurar_segredos),
                ("análise estática", self.ambiente.analisar_codigo),
            ):
                codigo, saida = varredura(copia)
                if codigo not in {0, 1}:
                    raise FalhaDeExecucao("ambiente", f"{nome}: exit {codigo}: {saida[-500:]}")
                resultados.append(
                    ResultadoGate(nome, codigo == 0, "" if codigo == 0 else saida[-2000:])
                )
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        dados = self.historico.dados(run_id)
        if all(g.aprovado for g in resultados) and dados["risco"] == "alto":
            try:
                resultados.append(self._revisar_seguranca(run_id, dados))
            except RespostaRecusada as erro:
                self._recusar(run_id, str(erro))
                return
        self._concluir_gates(run_id, resultados, "VERIFY_SDD")

    def _revisar_seguranca(self, run_id: str, dados: dict) -> ResultadoGate:
        """Risco alto ganha revisão humana-equivalente: o owner não lê o código."""
        copia = self._copia_para_gate(run_id, "revisao-seguranca")
        try:
            resposta = self._chamar_agente(
                run_id,
                "seguranca",
                "seguranca.md",
                {k: dados["entrada"].get(k) for k in ("sdd_id", "arquivos_permitidos")},
                copia,
                MODELO_SEGURANCA,
                FERRAMENTAS_LEITURA + ["Bash"],
            )
            problemas = problemas_de_evidencia(copia, resposta["achados"])
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        if problemas:
            raise RespostaRecusada("; ".join(problemas))
        if resposta["status"] == "aprovado" and not resposta["achados"]:
            return ResultadoGate("revisão de segurança", True)
        return ResultadoGate(
            "revisão de segurança", False, "; ".join(resposta["achados"]) or "reprovado"
        )

    def _verificar(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        _, caminho_sdd = self.historico.projeto_e_sdd(run_id)
        candidato = self._candidato(run_id)
        try:
            resultado = verificar(
                self.runner,
                self.cartorio,
                candidato,
                run_id,
                self.projeto.codigo,
                dados["entrada"],
                caminho_sdd,
                dados["base"],
                "HEAD",
                dados["tentativa"],
                self.revisor_modelo,
                self._ocultos(),
            )
        except RespostaRecusada as erro:
            self._recusar(run_id, str(erro))
            return
        self._somar_custo(run_id, resultado.execucao.custo_usd)
        if resultado.problemas:
            self._recusar(run_id, "; ".join(resultado.problemas))
            return
        validacao = resultado.validacao
        if validacao["status"] == "reprovado":
            motivo = "; ".join(validacao["descompassos"] or validacao["evidencias"]) or "reprovado"
            relatorio = {
                k: validacao[k] for k in ("status", "testes", "evidencias", "causa", "tentativa")
            }
            relatorio["descompassos"] = validacao["descompassos"]
            if validacao["causa"] == "especificacao":
                self._parar(run_id, "PARADA_ESPECIFICACAO", motivo, {"relatorio": relatorio})
            elif validacao["causa"] == "ambiente":
                self._parar(run_id, "PAUSADA_AMBIENTE", motivo, {"retomar_em": "VERIFY_SDD"})
            else:
                self._reprovar(run_id, relatorio, motivo)
            return
        head = _git(candidato, "rev-parse", "HEAD")
        problemas = self.fonte.registrar_verificacao(
            candidato, caminho_sdd, validacao, dados["base"], head
        )
        if problemas:
            self._parar(run_id, "PARADA_ESPECIFICACAO", "; ".join(problemas), {"relatorio": {}})
            return
        entrada = dados["entrada"]
        commit(candidato, f"docs(sdd): {entrada['sdd_id']} approved -> implemented")
        self.historico.avancar(
            run_id, "PR_PARA_DEVELOP", "verificação aprovada", {"validacao": validacao}
        )

    # Etapas 6 (CI), 7 e 8

    def _abrir_pr(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        _, caminho_sdd = self.historico.projeto_e_sdd(run_id)
        candidato = self._candidato(run_id)
        ramo = self._ramo(run_id)
        enviar_ramo(candidato, self.projeto.repo, ramo)
        entrada = dados["entrada"]
        resumo = "\n".join(
            [
                f"Implementa {entrada['sdd_id']}. Aberta pela fábrica.",
                f"\nRisco: {dados['risco']}. Tentativas: {dados['tentativa']}.",
                "\n## Gates\n",
                *[f"- {g}" for g in dados.get("gates", [])],
                "- Verify SDD: aprovado",
            ]
        )
        sdd_texto = (candidato / caminho_sdd).read_text(encoding="utf-8")
        corpo = montar_corpo_pr(
            resumo,
            sdd_texto,
            _git(candidato, "rev-parse", "HEAD"),
            caminho_sdd,
            self.projeto.github,
        )
        numero = self.github.abrir_pr(ramo, self.projeto.base, f"feat: {entrada['titulo']}", corpo)
        self.historico.avancar(run_id, "CI_E2E", f"PR #{numero}", {"pr": numero})

    def _esperar_ci(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        situacao, detalhe = self.github.esperar_checks(dados["pr"])
        if situacao == "passou":
            self.historico.avancar(run_id, "MERGE_EM_DEVELOP", "CI aprovado")
        elif situacao == "falhou":
            relatorio = relatorio_de_reprovacao(
                [ResultadoGate("CI", False, detalhe)], dados["tentativa"]
            )
            self.github.fechar_pr(dados["pr"], f"CI reprovado: {detalhe}. A fábrica vai corrigir.")
            self._reprovar(run_id, relatorio, f"CI reprovado: {detalhe}")
        else:
            self._parar(
                run_id,
                "PAUSADA_AMBIENTE",
                f"CI sem resultado: {situacao} {detalhe}",
                {"retomar_em": "CI_E2E"},
            )

    def _merge(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        self.github.fazer_merge_em_develop(dados["pr"])
        self.historico.avancar(run_id, "ARQUIVAMENTO", f"PR #{dados['pr']} em {self.projeto.base}")

    def _arquivar(self, run_id: str) -> None:
        """A SDD foi na PR. Agora sai do contexto vivo, por uma PR própria."""
        dados = self.historico.dados(run_id)
        _, caminho_sdd = self.historico.projeto_e_sdd(run_id)
        numero = dados.get("pr_arquivamento") or self._abrir_pr_de_arquivamento(
            run_id, dados, caminho_sdd
        )
        if numero:
            situacao, detalhe = self.github.esperar_checks(numero)
            if situacao not in {"passou", "sem_checks"}:
                self._parar(
                    run_id,
                    "PAUSADA_AMBIENTE",
                    f"CI do arquivamento: {situacao} {detalhe}",
                    {"retomar_em": "ARQUIVAMENTO"},
                )
                return
            self.github.fazer_merge_em_develop(numero)
        numero_release, versao = preparar_release(
            self.github, self.projeto.repo, self.projeto.base, self.projeto.principal
        )
        self._parar(
            run_id,
            "MEDIDA",
            f"PR #{dados['pr']} em {self.projeto.base}. Release {versao} aguarda aprovação: PR #{numero_release}",
            {"release": versao, "pr_release": numero_release},
        )
        shutil.rmtree(self._dir(run_id) / "candidato", ignore_errors=True)

    def _abrir_pr_de_arquivamento(self, run_id: str, dados: dict, caminho_sdd: str) -> int | None:
        """Devolve o número da PR, ou None se a SDD já estava arquivada."""
        copia = self._dir(run_id) / "arquivamento"
        shutil.rmtree(copia, ignore_errors=True)
        preparar_copia(self.projeto.repo, self.projeto.base, copia)
        try:
            hoje = datetime.now(UTC).date().isoformat()
            if not self.fonte.arquivar(copia, caminho_sdd, dados["pr"], hoje):
                return None
            sdd_id = dados["entrada"]["sdd_id"]
            ramo = f"feature/arquivar-{sdd_id.lower()}-{run_id[:8]}"
            _git(copia, "switch", "-q", "-c", ramo)
            commit(copia, f"docs(sdd): arquiva {sdd_id}, entregue na PR #{dados['pr']}")
            enviar_ramo(copia, self.projeto.repo, ramo)
            numero = self.github.abrir_pr(
                ramo,
                self.projeto.base,
                f"docs(sdd): arquiva {sdd_id}",
                f"Tira {sdd_id} do contexto vivo. Entregue na PR #{dados['pr']}.\n\n"
                "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n",
            )
        finally:
            shutil.rmtree(copia, ignore_errors=True)
        self.historico.atualizar_dados(run_id, {"pr_arquivamento": numero})
        return numero

    # Correção

    def _apos_recusa(self, run_id: str) -> None:
        dados = self.historico.dados(run_id)
        motivo = self.historico.transicoes(run_id)[-1][2]
        relatorio = {
            "status": "reprovado",
            "testes": {"passaram": 0, "falharam": 1},
            "evidencias": [f"resposta recusada: {motivo}"],
            "causa": "implementacao",
            "tentativa": dados["tentativa"],
        }
        self._reprovar(run_id, relatorio, f"resposta recusada: {motivo}")

    def _preparar_correcao(self, run_id: str) -> None:
        tentativa = self.historico.dados(run_id)["tentativa"] + 1
        self.historico.avancar(
            run_id, "CONTRATO_EMITIDO", f"correção, tentativa {tentativa}", {"tentativa": tentativa}
        )


class _DecisorDoRun:
    """Decisor do MVP: agente pequeno, sem ferramentas e sem código do projeto à vista."""

    def __init__(self, pipeline: Pipeline, run_id: str):
        self._pipeline = pipeline
        self._run_id = run_id

    def classificar_risco(self, entrada: dict) -> Decisao:
        vazio = self._pipeline._dir(self._run_id) / "decisao"
        vazio.mkdir(exist_ok=True)
        resumo = {
            k: entrada.get(k)
            for k in ("sdd_id", "titulo", "resumo", "requisitos", "arquivos_permitidos")
        }
        resposta = self._pipeline._chamar_agente(
            self._run_id, "decisao", "decisor.md", resumo, vazio, MODELO_DECISOR, []
        )
        return Decisao(
            resposta["risco"], resposta["confianca"], resposta["justificativa"], "decisor"
        )


def _ls_remote(repo: str, ramo: str) -> str:
    saida = subprocess.run(
        ["git", "ls-remote", repo, f"refs/heads/{ramo}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if not saida:
        raise FalhaDePublicacao(f"ramo {ramo} não encontrado em {repo}")
    return saida[0]


def _ultimo_commit_do_arquivo(repo: Path, caminho: str) -> str:
    return _git(repo, "log", "-1", "--format=%H", "--", caminho)
