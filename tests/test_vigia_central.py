"""Vigia do central (SDD-FAB-0009): PRs de documento, SPECs aprovadas e avisos.

O central é montado em `tmp_path`: um repositório nu como `origin` e um clone. O GitHub é um
falso; os scripts são os do kit fixado.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from adapters.doc_traceability.central import EscritaNoCentral, LeituraDoCentral
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework
from fabrica.descoberta import (
    AGUARDANDO_APROVACAO,
    AGUARDANDO_RESPOSTAS,
    APROVADA,
    PARADA,
    DescobertaInvalida,
)
from fabrica.publicacao import ETIQUETA_PR, FalhaDePublicacao
from fabrica.vigia import Vigia

pytestmark = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")

EXECUTOR = "executor"
REGISTRY = """project: "{codigo}"
framework_version: "2.7.0"
approvers: [dono]
repository: "https://github.com/dono/{repo}"
documents:
"""

CORPO_SPEC = """# {titulo}

# Parte 1 — Requisito (o QUÊ)

## Requisitos funcionais
| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |{coluna}
|---|---|---|---|{traco}
| RF01 | Aviso de mudança | Quando o cadastro mudar, o sistema deve enviar um e-mail. | `app/avisos.py` |{projetos}

# Parte 2 — Desenho (o COMO e o ONDE)

## Contratos técnicos
`app/avisos.py`: `enviar_aviso(cadastro) -> None`.
"""


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    return subprocess.run(
        comando, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def hash_do_kit(arquivo: Path) -> str:
    script = FRAMEWORK_PADRAO / "_framework" / "scripts" / "approval_hash.py"
    saida = subprocess.run(
        [sys.executable, str(script), str(arquivo), "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(saida)["content_sha256"]


class Central:
    """Clone de trabalho de um central com remoto nu; quem escreve aqui é o owner."""

    def __init__(self, tmp_path: Path):
        self.nu = tmp_path / "central.git"
        git("init", "-q", "--bare", "-b", "main", str(self.nu), cwd=tmp_path)
        self.clone = tmp_path / "central"
        git("clone", "-q", str(self.nu), str(self.clone), cwd=tmp_path)
        git("switch", "-q", "-c", "main", cwd=self.clone)
        self.projeto("ZERO")
        self.publicar("chore: central")

    def projeto(self, codigo: str) -> None:
        docs = self.clone / "docs" / codigo
        (docs / "03-spec").mkdir(parents=True, exist_ok=True)
        registry = docs / "registry.yaml"
        if not registry.is_file():
            registry.write_text(
                REGISTRY.format(codigo=codigo, repo=codigo.lower()), encoding="utf-8"
            )

    def spec(
        self,
        seq: int,
        codigo: str = "ZERO",
        projetos: str | None = None,
        kind: str = "human",
        hash_errado: bool = False,
        titulo: str = "Avisos por e-mail",
    ) -> str:
        self.projeto(codigo)
        doc_id = f"SPEC-{codigo}-{seq:04}"
        caminho = f"docs/{codigo}/03-spec/{doc_id}.md"
        coluna, traco, celula = ("", "", "") if projetos is None else (" Projeto |", "---|", "")
        if projetos is not None:
            celula = f" {projetos} |"
        corpo = CORPO_SPEC.format(titulo=titulo, coluna=coluna, traco=traco, projetos=celula)
        arquivo = self.clone / caminho
        cabecalho = (
            f'id: {doc_id}\ntype: SPEC\ntitle: "{titulo}"\nstatus: approved\n'
            f'project: "{codigo}"\nowner: "Dono"\ncreated: "2026-11-21"\n'
            'updated: "2026-11-21"\nrelates_to: []\nparent_rfc: null\nparent_adr: null\n'
            'sizing: "medium"\n'
        )
        arquivo.write_text(f"---\n{cabecalho}---\n\n{corpo}", encoding="utf-8")
        sha = "0" * 64 if hash_errado else hash_do_kit(arquivo)
        aprovacao = (
            f'approved_by:\n  kind: {kind}\n  actor: dono\n  at: "2026-11-21T12:00:00Z"\n'
            f'  content_sha256: "{sha}"\n'
            f'  evidence: "https://github.com/dono/central/pull/{seq}#pullrequestreview-{seq}"\n'
        )
        frente = cabecalho + aprovacao + "supersedes: null\nsuperseded_by: null\ntags: []\n"
        arquivo.write_text(f"---\n{frente}---\n\n{corpo}", encoding="utf-8")
        registry = self.clone / "docs" / codigo / "registry.yaml"
        with registry.open("a", encoding="utf-8") as saida:
            saida.write(
                f'  - id: {doc_id}\n    type: SPEC\n    title: "{titulo}"\n'
                f'    status: approved\n    owner: "Dono"\n    created: "2026-11-21"\n'
                f'    updated: "2026-11-21"\n    relates_to: []\n    path: "{caminho}"\n'
                "    tags: []\n"
            )
        return doc_id

    def publicar(self, mensagem: str = "docs: spec") -> None:
        git("add", "-A", cwd=self.clone)
        git("commit", "-qm", mensagem, cwd=self.clone)
        git("push", "-q", "origin", "main", cwd=self.clone)


@pytest.fixture
def central(tmp_path):
    return Central(tmp_path)


def leitura(central: Central, codigo: str = "ZERO") -> LeituraDoCentral:
    clone = central.clone.parent / f"leitor-{codigo}"
    if not clone.is_dir():
        git("clone", "-q", str(central.nu), str(clone), cwd=central.clone.parent)
    return LeituraDoCentral(clone, codigo, Framework())


# --- RF05: SPECs aprovadas em origin/main --------------------------------------------------


def test_specs_aprovada_por_humano_no_projeto_aparece_com_o_hash(central):
    doc_id = central.spec(1)
    central.publicar()
    leitor = leitura(central)
    arquivo = central.clone / "docs" / "ZERO" / "03-spec" / f"{doc_id}.md"
    assert leitor.specs_aprovadas() == [(doc_id, hash_do_kit(arquivo))]
    assert leitor.recusadas == {}


def test_specs_le_origin_main_depois_do_fetch(central):
    leitor = leitura(central)
    assert leitor.specs_aprovadas() == []
    doc_id = central.spec(1)
    central.publicar()
    assert [spec for spec, _ in leitor.specs_aprovadas()] == [doc_id]


def test_specs_de_outro_projeto_com_o_codigo_na_coluna_projeto(central):
    dividida = central.spec(1, codigo="KIT", projetos="KIT, ZERO")
    central.spec(2, codigo="KIT", projetos="KIT")
    sem_coluna = central.spec(3, codigo="KIT")
    central.publicar()
    ids = [spec for spec, _ in leitura(central).specs_aprovadas()]
    assert ids == [dividida]
    assert sem_coluna not in ids


def test_specs_com_kind_policy_nao_conta(central):
    central.spec(1, kind="policy")
    central.publicar()
    leitor = leitura(central)
    assert leitor.specs_aprovadas() == []
    # Fica fora antes do validate_state: não é recusa, só não é aprovação humana.
    assert leitor.recusadas == {}


def test_specs_com_validate_state_vermelho_fica_fora_com_o_motivo(central):
    doc_id = central.spec(1, hash_errado=True)
    central.publicar()
    leitor = leitura(central)
    assert leitor.specs_aprovadas() == []
    assert list(leitor.recusadas) == [doc_id]
    assert leitor.recusadas[doc_id]


def test_specs_url_e_a_de_source_docs(central):
    doc_id = central.spec(1)
    central.publicar()
    leitor = leitura(central)
    leitor.specs_aprovadas()
    # Mesma regra de FonteDocTraceability.origem: remote sem `.git`, `/blob/main/` e o path.
    base = str(central.nu).removesuffix(".git")
    assert leitor.url(doc_id) == f"{base}/blob/main/docs/ZERO/03-spec/{doc_id}.md"


# --- RF04: PRs da fábrica no central -------------------------------------------------------


class GithubDasPrs:
    def __init__(self, prs: list[dict], login: str = EXECUTOR):
        self.repo = "dono/central"
        self._prs = prs
        self._login = login
        self.chamadas: list[tuple] = []

    def login(self):
        return self._login

    def _gh(self, *args):
        self.chamadas.append(args)
        return json.dumps(self._prs)


def pr(ramo, login=EXECUTOR, etiquetas=(ETIQUETA_PR,), numero=1):
    return {
        "number": numero,
        "head": {"ref": ramo},
        "user": {"login": login},
        "labels": [{"name": e} for e in etiquetas],
    }


def test_prs_da_fabrica_filtra_por_ramo_conta_e_etiqueta(tmp_path):
    github = GithubDasPrs(
        [
            pr("docs/spec-zero-0001", numero=11),
            pr("docs/rfc-zero-0002", login="outra", numero=12),
            pr("docs/spec-zero-0003", etiquetas=(), numero=13),
            pr("feature/sdd-zero-0004", numero=14),
            pr("docs/spec-zero-0005", numero=15),
        ]
    )
    escrita = EscritaNoCentral(tmp_path, "ZERO", Framework(), github)
    # SDD-FAB-0010, RF02: o número vem da mesma listagem, para o aviso.
    assert escrita.prs_da_fabrica() == [("SPEC-ZERO-0001", 11), ("SPEC-ZERO-0005", 15)]


def test_prs_da_fabrica_uma_listagem_rest_por_chamada(tmp_path):
    github = GithubDasPrs([])
    EscritaNoCentral(tmp_path, "ZERO", Framework(), github).prs_da_fabrica()
    assert github.chamadas == [("api", "repos/dono/central/pulls?state=open&per_page=100")]


# --- Vigia.verificar_central: o ciclo com escrita, leitura e descoberta falsas -------------


class EscritaFalsa:
    def __init__(self, prs=(), decisoes=None, erros_integrar=None, erros_conferir=None):
        self.prs = list(prs)
        self.decisoes = decisoes or {}
        self.erros_integrar = erros_integrar or {}
        self.erros_conferir = erros_conferir or {}
        self.integradas = []
        self.conferidas = []

    def prs_da_fabrica(self):
        # A PR do i-ésimo documento tem o número 41 + i.
        return [(doc_id, 41 + i) for i, doc_id in enumerate(self.prs)]

    def conferir(self, doc_id):
        self.conferidas.append(doc_id)
        if doc_id in self.erros_conferir:
            raise self.erros_conferir[doc_id]
        return self.decisoes.get(doc_id, {"valida": False, "motivos": ["sem review"]})

    def integrar(self, doc_id, decisao):
        if doc_id in self.erros_integrar:
            raise self.erros_integrar[doc_id]
        self.integradas.append(doc_id)
        return "sha"


class LeituraFalsa:
    def __init__(self, specs=(), recusadas=None):
        self.specs = list(specs)
        self.recusadas = recusadas or {}
        self.falhar = 0
        self.leituras = 0

    def specs_aprovadas(self):
        self.leituras += 1
        if self.falhar:
            self.falhar -= 1
            raise FalhaDePublicacao("git fetch: rede")
        return list(self.specs)


class DescobertaFalsa:
    def __init__(self, fim=AGUARDANDO_APROVACAO, erro_publicar=None):
        self.fim = fim
        self.erro_publicar = erro_publicar
        self.compiladas = []
        self.publicadas = []
        self._estados = {}

    def compilar(self, spec_id):
        sessao = f"s-{spec_id}"
        self.compiladas.append(spec_id)
        self._estados[sessao] = self.fim
        return sessao

    def estado(self, sessao):
        return self._estados[sessao]

    def dados(self, sessao):
        return {"problemas": ["RF02 fora da SDD"], "pr": 9 if self.erro_publicar else None}

    def publicar_por_politica(self, sessao):
        if self.erro_publicar:
            raise self.erro_publicar
        self.publicadas.append(sessao)
        self._estados[sessao] = APROVADA
        return 7


class NotificadorFalso:
    def __init__(self):
        self.mensagens = []

    def avisar(self, mensagem):
        self.mensagens.append(mensagem)


class FonteDaBase:
    def __init__(self, formato="enxuta", atendidas=()):
        self.formato = formato
        self.atendidas = set(atendidas)

    def formato_da_sdd(self, repo, origens):
        return self.formato

    def sdd_com_origem(self, repo, spec_id):
        return "docs/sdd/SDD-ZERO-0001.md" if spec_id in self.atendidas else None

    def sdds_aprovadas(self, repo):
        return []

    def aprovacao_por_politica(self, repo, caminho_sdd):
        return False, []


@pytest.fixture
def base(tmp_path):
    origem = tmp_path / "base"
    origem.mkdir()
    git("init", "-q", "-b", "develop", cwd=origem)
    (origem / "README.md").write_text("# base\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "inicio", cwd=origem)
    return origem


def vigia_com(base, tmp_path, fonte=None):
    return Vigia(tmp_path / "f.db", "ZERO", str(base), "develop", fonte or FonteDaBase(), None)


def ciclo(vigia, escrita=None, leitura=None, descoberta=None, notificador=None):
    return vigia.verificar_central(
        escrita or EscritaFalsa(),
        leitura or LeituraFalsa(),
        descoberta or DescobertaFalsa(),
        notificador or NotificadorFalso(),
    )


def test_prs_sem_review_seguem_abertas_sem_aviso(base, tmp_path):
    escrita = EscritaFalsa(prs=["SPEC-ZERO-0001"])
    notificador = NotificadorFalso()
    resultado = ciclo(vigia_com(base, tmp_path), escrita, notificador=notificador)
    assert escrita.conferidas == ["SPEC-ZERO-0001"]
    assert escrita.integradas == []
    assert resultado["integradas"] == []
    assert notificador.mensagens == []


def test_prs_aprovada_e_integrada(base, tmp_path):
    escrita = EscritaFalsa(
        prs=["SPEC-ZERO-0001", "SPEC-ZERO-0002"], decisoes={"SPEC-ZERO-0002": {"valida": True}}
    )
    resultado = ciclo(vigia_com(base, tmp_path), escrita)
    assert escrita.integradas == ["SPEC-ZERO-0002"]
    assert resultado["integradas"] == ["SPEC-ZERO-0002"]


def test_specs_primeira_leitura_so_registra(base, tmp_path):
    descoberta = DescobertaFalsa()
    resultado = ciclo(
        vigia_com(base, tmp_path), leitura=LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)]),
        descoberta=descoberta,
    )  # fmt: skip
    assert descoberta.compiladas == []
    assert resultado["compiladas"] == []


def test_specs_nova_e_compilada_e_publicada_uma_vez(base, tmp_path):
    vigia = vigia_com(base, tmp_path)
    ciclo(vigia, leitura=LeituraFalsa([]))
    leitura = LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)])
    descoberta = DescobertaFalsa()
    assert ciclo(vigia, leitura=leitura, descoberta=descoberta)["compiladas"] == ["SPEC-ZERO-0001"]
    assert descoberta.publicadas == ["s-SPEC-ZERO-0001"]
    assert ciclo(vigia, leitura=leitura, descoberta=descoberta)["compiladas"] == []
    assert descoberta.compiladas == ["SPEC-ZERO-0001"]


def test_specs_hash_novo_da_mesma_spec_e_visto_de_novo(base, tmp_path):
    vigia = vigia_com(base, tmp_path)
    ciclo(vigia, leitura=LeituraFalsa([]))
    descoberta = DescobertaFalsa()
    ciclo(vigia, leitura=LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)]), descoberta=descoberta)
    ciclo(vigia, leitura=LeituraFalsa([("SPEC-ZERO-0001", "b" * 64)]), descoberta=descoberta)
    assert descoberta.compiladas == ["SPEC-ZERO-0001", "SPEC-ZERO-0001"]


def test_specs_recusada_pelo_validate_state_vira_aviso(base, tmp_path):
    notificador = NotificadorFalso()
    leitura = LeituraFalsa(recusadas={"SPEC-ZERO-0003": ["hash não bate"]})
    ciclo(vigia_com(base, tmp_path), leitura=leitura, notificador=notificador)
    assert len(notificador.mensagens) == 1
    assert "SPEC-ZERO-0003" in notificador.mensagens[0]
    assert "hash não bate" in notificador.mensagens[0]


# --- RF06 ---------------------------------------------------------------------------------


def test_atendida_spec_ja_em_source_docs_vista_sem_compilar(base, tmp_path, capsys):
    vigia = vigia_com(base, tmp_path, FonteDaBase(atendidas={"SPEC-ZERO-0001"}))
    ciclo(vigia, leitura=LeituraFalsa([]))
    descoberta = DescobertaFalsa()
    leitura = LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)])
    assert ciclo(vigia, leitura=leitura, descoberta=descoberta)["compiladas"] == []
    assert descoberta.compiladas == []
    assert "SPEC-ZERO-0001" in capsys.readouterr().out
    assert ciclo(vigia, leitura=leitura, descoberta=descoberta)["compiladas"] == []


def test_atendida_projeto_abaixo_de_2_7_0_vista_sem_compilar(base, tmp_path, capsys):
    vigia = vigia_com(base, tmp_path, FonteDaBase(formato="completa"))
    ciclo(vigia, leitura=LeituraFalsa([]))
    descoberta = DescobertaFalsa()
    ciclo(vigia, leitura=LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)]), descoberta=descoberta)
    assert descoberta.compiladas == []
    saida = capsys.readouterr().out
    assert "SPEC-ZERO-0001" in saida and "2.7.0" in saida


def test_atendida_adaptador_real_acha_a_sdd_pelo_source_docs(tmp_path):
    from adapters.doc_traceability import FonteDocTraceability

    repo = tmp_path / "repo"
    (repo / "docs/sdd").mkdir(parents=True)
    (repo / "docs/sdd/SDD-ZERO-0001.md").write_text(
        '---\nid: SDD-ZERO-0001\nsource_docs:\n  - id: "SPEC-ZERO-0001"\n    url: "u"\n---\n',
        encoding="utf-8",
    )
    fonte = FonteDocTraceability()
    assert fonte.sdd_com_origem(repo, "SPEC-ZERO-0001") == "docs/sdd/SDD-ZERO-0001.md"
    assert fonte.sdd_com_origem(repo, "SPEC-ZERO-0002") is None


# --- RF07 e RF10 --------------------------------------------------------------------------


def preparada(base, tmp_path):
    vigia = vigia_com(base, tmp_path)
    ciclo(vigia, leitura=LeituraFalsa([]))
    return vigia, LeituraFalsa([("SPEC-ZERO-0001", "a" * 64)])


def test_compilar_agente_que_pergunta_avisa_com_spec_e_sessao(base, tmp_path):
    vigia, leitura = preparada(base, tmp_path)
    notificador = NotificadorFalso()
    resultado = ciclo(
        vigia, leitura=leitura, descoberta=DescobertaFalsa(fim=AGUARDANDO_RESPOSTAS),
        notificador=notificador,
    )  # fmt: skip
    assert resultado["paradas"] == ["SPEC-ZERO-0001"]
    assert len(notificador.mensagens) == 1
    assert "SPEC-ZERO-0001" in notificador.mensagens[0]
    assert "--retomar s-SPEC-ZERO-0001" in notificador.mensagens[0]


def test_avisos_rascunho_parado_avisa_com_os_motivos(base, tmp_path):
    vigia, leitura = preparada(base, tmp_path)
    notificador = NotificadorFalso()
    ciclo(vigia, leitura=leitura, descoberta=DescobertaFalsa(fim=PARADA), notificador=notificador)
    assert "RF02 fora da SDD" in notificador.mensagens[0]


def test_avisos_publicacao_recusada_avisa_com_a_pr(base, tmp_path):
    vigia, leitura = preparada(base, tmp_path)
    notificador = NotificadorFalso()
    descoberta = DescobertaFalsa(erro_publicar=DescobertaInvalida("CI da PR #9: falhou"))
    ciclo(vigia, leitura=leitura, descoberta=descoberta, notificador=notificador)
    assert "SPEC-ZERO-0001" in notificador.mensagens[0]
    assert "#9" in notificador.mensagens[0]
    assert "CI da PR #9: falhou" in notificador.mensagens[0]


def test_avisos_publicacao_recusada_sem_numero_no_motivo_avisa_com_a_pr(base, tmp_path):
    vigia, leitura = preparada(base, tmp_path)
    notificador = NotificadorFalso()
    descoberta = DescobertaFalsa(erro_publicar=DescobertaInvalida("checks vermelhos"))
    ciclo(vigia, leitura=leitura, descoberta=descoberta, notificador=notificador)
    assert "SPEC-ZERO-0001 (PR #9): checks vermelhos" in notificador.mensagens[0]


def test_avisos_mesmo_motivo_em_dois_ciclos_avisa_uma_vez(base, tmp_path):
    from adapters.doc_traceability import EscritaRecusada

    vigia = vigia_com(base, tmp_path)
    notificador = NotificadorFalso()
    escrita = EscritaFalsa(
        prs=["SPEC-ZERO-0001", "SPEC-ZERO-0002"],
        decisoes={"SPEC-ZERO-0001": {"valida": True}, "SPEC-ZERO-0002": {"valida": True}},
        erros_integrar={"SPEC-ZERO-0001": EscritaRecusada("checks da PR #41: falhou")},
    )
    ciclo(vigia, escrita, notificador=notificador)
    ciclo(vigia, escrita, notificador=notificador)
    assert len(notificador.mensagens) == 1
    assert "checks da PR #41: falhou" in notificador.mensagens[0]
    # O ciclo segue nos outros documentos.
    assert escrita.integradas == ["SPEC-ZERO-0002", "SPEC-ZERO-0002"]


def test_avisos_pr_do_central_sem_numero_no_motivo_avisa_com_a_pr(base, tmp_path):
    from adapters.doc_traceability import EscritaRecusada

    notificador = NotificadorFalso()
    escrita = EscritaFalsa(
        prs=["SPEC-ZERO-0001", "SPEC-ZERO-0002"],
        decisoes={"SPEC-ZERO-0002": {"valida": True}},
        erros_conferir={"SPEC-ZERO-0001": EscritaRecusada("aprovação inválida")},
        erros_integrar={"SPEC-ZERO-0002": EscritaRecusada("merge recusado: x → y")},
    )
    ciclo(vigia_com(base, tmp_path), escrita, notificador=notificador)
    assert len(notificador.mensagens) == 2
    assert "SPEC-ZERO-0001 (PR #41): aprovação inválida" in notificador.mensagens[0]
    assert "SPEC-ZERO-0002 (PR #42): merge recusado" in notificador.mensagens[1]


def test_avisos_falha_de_fetch_tres_vezes_avisa_uma_vez(base, tmp_path):
    vigia = vigia_com(base, tmp_path)
    notificador = NotificadorFalso()
    leitura = LeituraFalsa()
    leitura.falhar = 4
    for _ in range(4):
        ciclo(vigia, leitura=leitura, notificador=notificador)
    assert len(notificador.mensagens) == 1
    assert "3" in notificador.mensagens[0]


def test_avisos_falha_de_fetch_de_novo_depois_de_recuperar_volta_a_contar(base, tmp_path):
    vigia = vigia_com(base, tmp_path)
    notificador = NotificadorFalso()
    leitura = LeituraFalsa()
    leitura.falhar = 2
    for _ in range(3):
        ciclo(vigia, leitura=leitura, notificador=notificador)
    leitura.falhar = 2
    for _ in range(2):
        ciclo(vigia, leitura=leitura, notificador=notificador)
    assert notificador.mensagens == []


# --- SDD-FAB-0010, RF05: o clone da base falha no RF06 --------------------------------------


def test_clone_da_base_falha_no_rf06_avisa_e_segue(tmp_path):
    vigia = Vigia(
        tmp_path / "f.db", "ZERO", str(tmp_path / "sem-base"), "develop", FonteDaBase(), None
    )
    ciclo(vigia, leitura=LeituraFalsa([]))
    notificador = NotificadorFalso()
    descoberta = DescobertaFalsa()
    leitura = LeituraFalsa([("SPEC-ZERO-0001", "a" * 64), ("SPEC-ZERO-0002", "b" * 64)])
    resultado = ciclo(vigia, leitura=leitura, descoberta=descoberta, notificador=notificador)
    assert resultado["paradas"] == ["SPEC-ZERO-0001", "SPEC-ZERO-0002"]
    assert descoberta.compiladas == []
    assert len(notificador.mensagens) == 2
    assert "SPEC-ZERO-0001: cópia da base falhou" in notificador.mensagens[0]
