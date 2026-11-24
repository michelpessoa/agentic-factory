"""Operação da fábrica: `uv run python -m fabrica <comando>`."""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from adapters.doc_traceability import (
    EscritaNoCentral,
    EscritaRecusada,
    FonteDocTraceability,
    OrigemInvalida,
    VersaoDivergente,
    repositorio_do_central,
)
from adapters.doc_traceability.central import LeituraDoCentral
from adapters.doc_traceability.validadores import Framework
from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio
from fabrica.descoberta import (
    AGUARDANDO_APROVACAO,
    AGUARDANDO_RESPOSTAS,
    NO_CENTRAL,
    PARADA,
    TENTATIVAS_DE_RASCUNHO,
    Descoberta,
    DescobertaInvalida,
)
from fabrica.estados import Historico
from fabrica.execucao import AmbienteDocker, ClaudeDockerRunner
from fabrica.notificacao import ConfiguracaoInvalida, Notificador, carregar_canais
from fabrica.painel import ENDERECO, criar_servidor
from fabrica.pipeline import Pipeline, Projeto
from fabrica.publicacao import (
    FalhaDePublicacao,
    Github,
    PublicacaoRecusada,
    concluir_release,
    preparar_release,
)
from fabrica.vigia import Vigia

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / ".fabrica"


def carregar_projeto(nome: str) -> Projeto:
    dados = yaml.safe_load((RAIZ / "projetos" / f"{nome}.yaml").read_text(encoding="utf-8"))
    dados["permitidos"] = tuple(dados.get("permitidos") or ())
    return Projeto(**dados)


def sem_tokens(valor):
    """Tira o token dos contratos da saída: mesmo de uso único, token não aparece em terminal nem log."""
    if isinstance(valor, dict):
        return {k: sem_tokens(v) for k, v in valor.items() if k != "token"}
    if isinstance(valor, list):
        return [sem_tokens(v) for v in valor]
    return valor


def montar_fonte(projeto: Projeto) -> FonteDocTraceability:
    fonte = FonteDocTraceability(
        central=Path(projeto.central).expanduser() if projeto.central else None,
        codigo=projeto.codigo,
    )
    fonte.exigir_versao(projeto.framework)
    return fonte


def montar_pipeline(projeto: Projeto) -> Pipeline:
    fonte = montar_fonte(projeto)
    DIR_DADOS.mkdir(exist_ok=True)
    banco = DIR_DADOS / "fabrica.db"
    return Pipeline(
        projeto,
        Historico(banco),
        Cartorio(banco),
        fonte,
        ClaudeDockerRunner(),
        AmbienteDocker(),
        Github(projeto.github),
        Notificador(DIR_DADOS / "status.log", canais=carregar_canais()),
        DIR_DADOS / "runs",
        aprovacoes=Aprovacoes(banco),
    )


def montar_escrita(projeto: Projeto) -> EscritaNoCentral:
    central = Path(projeto.central).expanduser()
    return EscritaNoCentral(
        central, projeto.codigo, Framework(), Github(repositorio_do_central(central))
    )


def montar_descoberta(projeto: Projeto) -> Descoberta:
    fonte = montar_fonte(projeto)
    DIR_DADOS.mkdir(exist_ok=True)
    banco = DIR_DADOS / "fabrica.db"
    return Descoberta(
        projeto,
        banco,
        Cartorio(banco),
        ClaudeDockerRunner(),
        fonte,
        Aprovacoes(banco),
        Github(projeto.github),
        DIR_DADOS / "descobertas",
        escritor=montar_escrita(projeto),
        progresso=mostrar_progresso,
    )


MAPA = """
Descoberta: da sua ideia até um documento aprovado, antes de qualquer código.
  1. Entender a ideia      o agente pergunta o que faltar
  2. Escrever o documento  o tamanho da mudança decide qual
  3. Validar               os validadores do framework conferem
  4. Aprovar               só você aprova; nada entra sem isso
  5. Implementar           a fábrica implementa e integra em develop
  6. Liberar               release para main, com merge seu
Esta sessão cuida das etapas 1 a 3. Da 4 em diante, cada etapa começa por um comando seu."""


def _texto_do_progresso(evento: str, d: dict) -> str | None:
    """Texto de cada evento da descoberta: em que etapa a sessão está e por quê."""
    if evento == "agente" and d["tentativa"] == 1:
        if d["respostas"]:
            return (
                "Respostas enviadas. O agente decide se ainda falta algo ou se já escreve. Aguarde."
            )
        return (
            "── 1/6 Entender a ideia ──\n"
            "O agente lê a sua ideia e decide se já dá para escrever ou se falta informação.\n"
            "A chamada ao agente demora, e o terminal fica parado enquanto ela roda. Aguarde."
        )
    if evento == "perguntas":
        return (
            f"O agente tem {d['quantidade']} pergunta(s) (rodada {d['rodada']} de até "
            f"{d['rodadas']}).\n"
            "Por que perguntar: as respostas fecham o escopo, os critérios de aceite e o tamanho\n"
            "da mudança. O tamanho decide quais documentos o framework exige antes do código."
        )
    if evento == "validando":
        tipo, sizing = d["tipo"], d["sizing"]
        if d["tentativa"] > 1:
            return (
                f"Tentativa {d['tentativa']} de {d['tentativas']}: o agente entregou um novo "
                f"rascunho de {tipo} ({sizing}), e os validadores o conferem."
            )
        if tipo != "SDD":
            porque = f"{sizing} sem --origem: o framework pede uma {tipo} aprovada no central antes da SDD."
            destino = "no central"
        elif d["origens"]:
            porque = f"A SDD nasce de {', '.join(d['origens'])}, já aprovada(s) no central."
            destino = "na base"
        else:
            porque = f"{sizing} sem --origem: basta a SDD, sem SPEC nem RFC antes."
            destino = "na base"
        return (
            "── 2/6 Escrever o documento ──\n"
            f"O agente entregou um rascunho de {tipo}, tamanho {sizing}.\n"
            f"{porque}\n\n"
            "── 3/6 Validar ──\n"
            f"Os validadores do framework conferem o rascunho como ele entraria {destino}, "
            "antes de você ler."
        )
    if evento == "recusa" and not d["parando"]:
        return (
            f"Tentativa {d['tentativa']} de {d['tentativas']} recusada: {d['problemas']} "
            "problema(s). O agente recebe os motivos e refaz. Aguarde."
        )
    if evento in {"pr_central", "pronto"}:
        documento = d.get("doc_id") or d.get("sdd_id")
        if evento == "pr_central":
            depois = "Abrindo a PR no central, onde o documento fica em in_review."
        elif d.get("automatica"):
            # SDD-FAB-0010, RF06: a política dispensa a aprovação no terminal.
            depois = (
                "Compilação do vigia: a SDD sai aprovada por política e entra na base por PR, "
                "sem fabrica aprovar."
            )
        else:
            depois = "Agora é com você: nada entra na base sem a sua aprovação."
        return (
            "── 4/6 Aprovar ──\n"
            f"{documento} passou nos validadores na tentativa {d['tentativa']} de "
            f"{d['tentativas']}.\n{depois}"
        )
    return None


def mostrar_progresso(evento: str, detalhes: dict) -> None:
    """Imprime na hora o aviso de cada etapa da descoberta. Só informa: não lê entrada."""
    texto = _texto_do_progresso(evento, detalhes)
    if texto is not None:
        print(f"\n{texto}", flush=True)


def mostrar_parada(sessao: str, dados: dict) -> None:
    """Os motivos da última tentativa primeiro, depois os das anteriores."""
    *anteriores, ultima = dados["recusas"]
    print("\n── Parada na etapa 3/6 Validar ──")
    print(
        f"O rascunho foi recusado nas {TENTATIVAS_DE_RASCUNHO} tentativas. "
        "Nada foi gravado na base nem no central."
    )
    print(
        f"\nMotivos da última tentativa ({ultima['tentativa']} de {TENTATIVAS_DE_RASCUNHO}), "
        f"{len(ultima['problemas'])} problema(s):"
    )
    for numero, problema in enumerate(ultima["problemas"], 1):
        print(f"  {numero}. {problema}")
    if anteriores:
        print("\nTentativas anteriores:")
        for recusa in anteriores:
            if recusa["problemas"] == ultima["problemas"]:
                print(
                    f"  tentativa {recusa['tentativa']}: os mesmos motivos da tentativa "
                    f"{ultima['tentativa']}"
                )
                continue
            print(f"  tentativa {recusa['tentativa']}: {len(recusa['problemas'])} problema(s)")
            for numero, problema in enumerate(recusa["problemas"], 1):
                print(f"    {numero}. {problema}")
    print("\nO que fazer: ajuste a ideia com base nesses motivos e rode descobrir de novo.")


def conversar(descoberta: Descoberta, sessao: str) -> int:
    """Pergunta no terminal até haver rascunho. Ctrl-D sai, e `--retomar` continua de onde parou."""
    print(f"sessão {sessao}", flush=True)
    print(MAPA, flush=True)
    while True:
        estado = descoberta.avancar(sessao)
        dados = descoberta.dados(sessao)
        if estado == AGUARDANDO_RESPOSTAS:
            respostas = []
            for numero, pergunta in enumerate(dados["conversa"][-1]["perguntas"], 1):
                print(f"\n{numero}. {pergunta}")
                try:
                    respostas.append(input("> ").strip() or "sem resposta")
                except EOFError:
                    print(f"\nsalvo. Continue com: descobrir {descoberta.projeto.codigo.lower()} "
                          f"--retomar {sessao}")  # fmt: skip
                    return 0
            descoberta.responder(sessao, respostas)
            continue
        if estado == AGUARDANDO_APROVACAO:
            print(f"\nRascunho {dados['sdd_id']} em {dados['arquivo']}")
            print(f"Leia e, se estiver certo: uv run python -m fabrica aprovar <projeto> {sessao}")
            print(
                "Depois de aprovada, a SDD vai para develop por PR e o vigia dispara a "
                "implementação (etapa 5)."
            )
            return 0
        if estado == NO_CENTRAL:
            print(f"\nRascunho {dados['doc_id']} na PR #{dados['pr']} do central, em in_review.")
            print(
                "Aprove por review na PR e depois: "
                f"uv run python -m fabrica central conferir <projeto> {dados['doc_id']}"
            )
            tipo = dados["doc_id"].split("-")[0]
            if tipo == "SPEC":
                print(
                    "Com a SPEC aprovada, a SDD sai de outra descoberta com "
                    f"--origem {dados['doc_id']}."
                )
            else:
                print(
                    f"Com a {tipo} aprovada, o fluxo segue no central até uma SPEC aprovada, "
                    "que é a --origem da SDD."
                )
            return 0
        if estado == PARADA:
            mostrar_parada(sessao, dados)
            return 1
        print(f"estado inesperado: {estado}")
        return 1


def aprovar(descoberta: Descoberta, alvo: str) -> int:
    """Só no terminal, com o id da SDD digitado. Não é segurança: é para não aprovar por engano."""
    if not sys.stdin.isatty():
        print("aprovar exige terminal interativo: a aprovação é do humano")
        return 2
    if alvo.endswith(".md"):
        resposta = input(f"Aprovar o conteúdo atual de {alvo} na base? Digite o caminho: ")
        if resposta.strip() != alvo:
            print("não aprovada")
            return 1
        print(f"aprovada, sha256 {descoberta.aprovar_existente(alvo)}")
        return 0
    dados = descoberta.dados(alvo)
    if descoberta.estado(alvo) == AGUARDANDO_APROVACAO:
        print(f"SDD {dados['sdd_id']}: {dados['rascunho']['titulo']}\nArquivo: {dados['arquivo']}")
        if input("Digite o id da SDD para aprovar: ").strip() != dados["sdd_id"]:
            print("não aprovada")
            return 1
    print(
        f"publicando em {descoberta.projeto.base}: abre a PR e espera o CI; sem CI, são 2 minutos",
        flush=True,
    )
    print(f"aprovada e em {descoberta.projeto.base} pela PR #{descoberta.aprovar(alvo)}")
    return 0


def central_conferir(escrita: EscritaNoCentral, doc_id: str) -> int:
    """Confere a review da PR do central e, se valer, grava a aprovação e faz o merge."""
    try:
        decisao = escrita.conferir(doc_id)
        if not decisao.get("valida"):
            for motivo in decisao.get("motivos", []):
                print(f"- {motivo}")
            return 1
        sha = escrita.integrar(doc_id, decisao)
    except (EscritaRecusada, FalhaDePublicacao, PublicacaoRecusada) as erro:
        print(f"erro: {erro}")
        return 1
    print(f"{doc_id} approved e em main do central pelo merge {sha}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="fabrica")
    comandos = parser.add_subparsers(dest="comando", required=True)
    iniciar = comandos.add_parser("iniciar", help="roda o pipeline para uma SDD aprovada")
    iniciar.add_argument("projeto")
    iniciar.add_argument("sdd")
    retomar = comandos.add_parser("retomar", help="retoma execução pausada ou interrompida")
    retomar.add_argument("projeto")
    retomar.add_argument("run_id")
    decidir = comandos.add_parser("decidir", help="responde a uma decisão de baixa confiança")
    decidir.add_argument("projeto")
    decidir.add_argument("run_id")
    decidir.add_argument("risco", choices=["baixo", "medio", "alto"])
    vigiar = comandos.add_parser("vigiar", help="dispara a fábrica quando uma SDD é aprovada")
    vigiar.add_argument("projeto")
    vigiar.add_argument("--intervalo", type=int, default=300)
    vigiar.add_argument("--uma-vez", action="store_true")
    vigiar.add_argument(
        "--sem-central",
        action="store_true",
        help="só as SDDs da base: não confere PRs nem SPECs aprovadas do central",
    )
    descobrir = comandos.add_parser("descobrir", help="da ideia até o rascunho de SDD")
    descobrir.add_argument("projeto")
    descobrir.add_argument("ideia", nargs="?")
    descobrir.add_argument("--retomar", metavar="SESSAO")
    descobrir.add_argument("--origem", action="append", default=[], metavar="ID")
    aprovar_cmd = comandos.add_parser("aprovar", help="aprova uma SDD; só no terminal")
    aprovar_cmd.add_argument("projeto")
    aprovar_cmd.add_argument("alvo", help="sessão da descoberta ou caminho de SDD já na base")
    comandos.add_parser("status", help="lista as execuções")
    painel = comandos.add_parser("painel", help="abre o painel local, só leitura")
    painel.add_argument("--porta", type=int, default=8765)
    historico = comandos.add_parser("historico", help="mostra as transições de uma execução")
    historico.add_argument("run_id")
    release = comandos.add_parser("release", help="abre ou atualiza a PR de release")
    release.add_argument("projeto")
    pos = comandos.add_parser("pos-release", help="tag e develop depois do merge humano")
    pos.add_argument("projeto")
    pos.add_argument("versao")
    central = comandos.add_parser("central", help="documento do central aberto pela descoberta")
    acoes_central = central.add_subparsers(dest="acao", required=True)
    conferir = acoes_central.add_parser(
        "conferir", help="confere a review e faz o merge da PR do central"
    )
    conferir.add_argument("projeto")
    conferir.add_argument("id")
    args = parser.parse_args()

    if args.comando == "status":
        for linha in Historico(DIR_DADOS / "fabrica.db").listar():
            print(*linha, sep="  ")
        return 0
    if args.comando == "historico":
        banco = Historico(DIR_DADOS / "fabrica.db")
        for origem, destino, motivo in banco.transicoes(args.run_id):
            print(f"{origem} -> {destino}: {motivo}")
        print(
            json.dumps(
                sem_tokens({k: v for k, v in banco.dados(args.run_id).items() if k != "entrada"}),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.comando == "painel":
        servidor = criar_servidor(DIR_DADOS / "fabrica.db", args.porta)
        print(f"http://{ENDERECO}:{servidor.server_address[1]}", flush=True)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    projeto = carregar_projeto(args.projeto)
    if args.comando == "central":
        montar_fonte(projeto)
        try:
            escrita = montar_escrita(projeto)
        except (EscritaRecusada, FalhaDePublicacao) as erro:
            print(f"erro: {erro}")
            return 1
        return central_conferir(escrita, args.id)
    if args.comando in {"descobrir", "aprovar"}:
        try:
            descoberta = montar_descoberta(projeto)
            if args.comando == "aprovar":
                return aprovar(descoberta, args.alvo)
            if not (args.ideia or args.retomar):
                parser.error("descobrir precisa da ideia ou de --retomar")
            if args.retomar:
                if args.origem:
                    print("--origem só vale ao iniciar uma descoberta")
                    return 2
                return conversar(descoberta, args.retomar)
            try:
                origens = [descoberta.redator.origem(i) for i in args.origem]
            except OrigemInvalida as erro:
                print(f"erro: {erro}")
                return 2
            return conversar(descoberta, descoberta.criar(args.ideia, origens))
        except (DescobertaInvalida, KeyError, EscritaRecusada, FalhaDePublicacao) as erro:
            print(f"erro: {erro}")
            return 1
    if args.comando == "iniciar":
        pipeline = montar_pipeline(projeto)
        run_id = pipeline.iniciar(args.sdd)
        print(run_id, pipeline.historico.estado(run_id))
    elif args.comando == "retomar":
        print(montar_pipeline(projeto).retomar(args.run_id))
    elif args.comando == "decidir":
        print(montar_pipeline(projeto).decidir(args.run_id, args.risco))
    elif args.comando == "vigiar":
        pipeline = montar_pipeline(projeto)
        vigia = Vigia(
            DIR_DADOS / "fabrica.db",
            projeto.codigo,
            projeto.repo,
            projeto.base,
            pipeline.fonte,
            pipeline.aprovacoes,
        )
        central = None
        if not args.sem_central and projeto.central:
            caminho_central = Path(projeto.central).expanduser()
            central = (
                montar_escrita(projeto),
                LeituraDoCentral(caminho_central, projeto.codigo, Framework()),
                montar_descoberta(projeto),
                pipeline.notificador,
            )
        while True:
            linha = ""
            if central:
                r = vigia.verificar_central(*central)
                linha = f"central: integradas {r['integradas']}, compiladas {r['compiladas']}; "
            print(f"{linha}disparadas: {vigia.verificar(pipeline.iniciar)}", flush=True)
            if args.uma_vez:
                break
            time.sleep(args.intervalo)
    elif args.comando == "release":
        print(
            preparar_release(Github(projeto.github), projeto.repo, projeto.base, projeto.principal)
        )
    elif args.comando == "pos-release":
        concluir_release(
            projeto.repo, projeto.base, projeto.principal, Github(projeto.github), args.versao
        )
        print(f"v{args.versao} criada e {projeto.base} atualizada")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ConfiguracaoInvalida, VersaoDivergente) as erro:
        print(f"erro: {erro}")
        sys.exit(1)
