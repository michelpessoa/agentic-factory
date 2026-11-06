"""Operação da fábrica: `uv run python -m fabrica <comando>`."""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from adapters.doc_traceability import FonteDocTraceability
from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio
from fabrica.descoberta import (
    AGUARDANDO_APROVACAO,
    AGUARDANDO_RESPOSTAS,
    PARADA,
    Descoberta,
    DescobertaInvalida,
)
from fabrica.estados import Historico
from fabrica.execucao import AmbienteDocker, ClaudeDockerRunner
from fabrica.notificacao import Notificador
from fabrica.painel import ENDERECO, criar_servidor
from fabrica.pipeline import Pipeline, Projeto
from fabrica.publicacao import Github, concluir_release, preparar_release
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


def montar_pipeline(projeto: Projeto) -> Pipeline:
    DIR_DADOS.mkdir(exist_ok=True)
    banco = DIR_DADOS / "fabrica.db"
    return Pipeline(
        projeto,
        Historico(banco),
        Cartorio(banco),
        FonteDocTraceability(),
        ClaudeDockerRunner(),
        AmbienteDocker(),
        Github(projeto.github),
        Notificador(DIR_DADOS / "status.log"),
        DIR_DADOS / "runs",
        aprovacoes=Aprovacoes(banco),
    )


def montar_descoberta(projeto: Projeto) -> Descoberta:
    DIR_DADOS.mkdir(exist_ok=True)
    banco = DIR_DADOS / "fabrica.db"
    return Descoberta(
        projeto,
        banco,
        Cartorio(banco),
        ClaudeDockerRunner(),
        FonteDocTraceability(),
        Aprovacoes(banco),
        Github(projeto.github),
        DIR_DADOS / "descobertas",
    )


def conversar(descoberta: Descoberta, sessao: str) -> int:
    """Pergunta no terminal até haver rascunho. Ctrl-D sai, e `--retomar` continua de onde parou."""
    print(f"sessão {sessao}", flush=True)
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
            return 0
        if estado == PARADA:
            print("\nParada: o rascunho não passou nos validadores em 3 tentativas.")
            for problema in dados["problemas"]:
                print(f"- {problema}")
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
    descobrir = comandos.add_parser("descobrir", help="da ideia até o rascunho de SDD")
    descobrir.add_argument("projeto")
    descobrir.add_argument("ideia", nargs="?")
    descobrir.add_argument("--retomar", metavar="SESSAO")
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
    if args.comando in {"descobrir", "aprovar"}:
        descoberta = montar_descoberta(projeto)
        try:
            if args.comando == "aprovar":
                return aprovar(descoberta, args.alvo)
            if not (args.ideia or args.retomar):
                parser.error("descobrir precisa da ideia ou de --retomar")
            return conversar(descoberta, args.retomar or descoberta.criar(args.ideia))
        except (DescobertaInvalida, KeyError) as erro:
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
        while True:
            print(f"disparadas: {vigia.verificar(pipeline.iniciar)}", flush=True)
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
    sys.exit(main())
