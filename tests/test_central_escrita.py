"""Escrita no central (SDD-FAB-0003): rascunho por PR e aprovação pela review.

O central é montado em `tmp_path`: um repositório nu como `origin` e um clone. O GitHub é um
falso que registra as chamadas; os scripts são os do kit fixado.
"""

import datetime
import subprocess
import types
from pathlib import Path

import pytest
import yaml

from adapters.doc_traceability import EscritaNoCentral, EscritaRecusada, repositorio_do_central
from adapters.doc_traceability import central as modulo_central
from adapters.doc_traceability.central import ESPERA_DO_HEAD_SEGUNDOS, LIMITE_DO_HEAD_SEGUNDOS
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework
from fabrica.publicacao import FalhaDePublicacao, PublicacaoRecusada

pytestmark = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")

APROVADOR = "dono"
EXECUTOR = "executor"
REGISTRY = """project: "ZERO"
framework_version: "2.7.0"
approvers: [dono]
repository: "https://github.com/dono/zero"
documents: []
"""

CORPO_SPEC = """# Avisos por e-mail

## Objetivo
Avisar o responsável por e-mail quando o cadastro muda.

# Parte 1 — Requisito (o QUÊ)

## Requisitos funcionais
| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Aviso de mudança | Quando o cadastro mudar, o sistema deve enviar um e-mail ao responsável. | `app/avisos.py` |

## Requisitos transversais (sweep)
| Categoria | Destino (RF-ID ou n/a) | Motivo (obrigatório se n/a) |
|---|---|---|
| Autorização / permissão | n/a | sem tela nova |
| Concorrência | n/a | um envio por mudança |
| Idempotência | RF01 | |
| Observabilidade | n/a | log já existente |
| Falha de dependência externa | RF01 | |
| Validação de entrada | n/a | sem entrada nova |
| Limite de volume / rate | n/a | volume baixo |

## Fora de escopo
SMS.

# Parte 2 — Desenho (o COMO e o ONDE)

## Contratos técnicos
`app/avisos.py`: `enviar_aviso(cadastro) -> None`.

## Estratégia de teste
Teste unitário com SMTP falso.
"""


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    return subprocess.run(
        comando, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class GithubFalso:
    def __init__(self, nu: Path, login: str = EXECUTOR):
        self.nu = nu
        self._login = login
        self.chamadas: list[tuple] = []
        self.prs: dict[str, dict] = {}
        self.lista_de_reviews: list[dict] = []
        self.situacao = ("passou", "")
        self.head_atrasado: str | None = None
        self.leituras_atrasadas = 0

    def login(self):
        self.chamadas.append(("login",))
        return self._login

    def abrir_pr_documento(self, ramo, titulo, corpo):
        self.chamadas.append(("abrir_pr_documento", ramo, titulo, corpo))
        numero = 40 + len(self.prs)
        self.prs[ramo] = {"number": numero, "ramo": ramo}
        return numero

    def pr_aberta_do_ramo(self, ramo):
        self.chamadas.append(("pr_aberta_do_ramo", ramo))
        pr = self.prs.get(ramo)
        if pr is None:
            return None
        head = git("rev-parse", ramo, cwd=self.nu)
        if self.head_atrasado is not None and self.leituras_atrasadas > 0:
            self.leituras_atrasadas -= 1
            head = self.head_atrasado
        self.chamadas.append(("head_da_pr", head))
        return {
            "number": pr["number"],
            "head": {"sha": head, "ref": ramo},
            "html_url": f"https://github.com/dono/central/pull/{pr['number']}",
        }

    def reviews(self, numero):
        self.chamadas.append(("reviews", numero))
        return self.lista_de_reviews

    def esperar_checks(self, numero):
        self.chamadas.append(("esperar_checks", numero))
        return self.situacao

    def fazer_merge_de_documento(self, numero):
        self.chamadas.append(("fazer_merge_de_documento", numero))
        ramo = next(r for r, pr in self.prs.items() if pr["number"] == numero)
        return git("rev-parse", ramo, cwd=self.nu)

    def nomes(self):
        return [c[0] for c in self.chamadas]


@pytest.fixture
def central(tmp_path):
    nu = tmp_path / "central.git"
    git("init", "-q", "--bare", "-b", "main", str(nu), cwd=tmp_path)
    clone = tmp_path / "central"
    git("clone", "-q", str(nu), str(clone), cwd=tmp_path)
    git("switch", "-q", "-c", "main", cwd=clone)
    docs = clone / "docs" / "ZERO"
    docs.mkdir(parents=True)
    (docs / "registry.yaml").write_text(REGISTRY, encoding="utf-8")
    Framework().gerar_registry_md(docs)
    git("add", "-A", cwd=clone)
    git("commit", "-qm", "chore: central", cwd=clone)
    git("push", "-q", "origin", "main", cwd=clone)
    return clone, nu


def escrita(central, login=EXECUTOR):
    clone, nu = central
    github = GithubFalso(nu, login)
    return EscritaNoCentral(clone, "ZERO", Framework(), github), github


def documento(tipo="SPEC", sizing="medium", corpo=CORPO_SPEC):
    return {"tipo": tipo, "titulo": "Avisos por e-mail", "sizing": sizing, "corpo": corpo}


def abrir(escritor, doc=None):
    doc_id, texto = escritor.montar(doc or documento(), "Owner", "2026-11-01")
    numero = escritor.abrir_pr(doc_id, (doc or documento())["tipo"], texto, "Avisos por e-mail")
    return doc_id, numero


def review(id_, login, estado, commit, corpo="", quando="2026-11-18T12:00:00Z"):
    return {
        "id": id_,
        "user": {"login": login},
        "state": estado,
        "body": corpo,
        "commit_id": commit,
        "submitted_at": quando,
    }


# --- repositorio_do_central ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("git@github.com:dono/central.git", "dono/central"),
        ("https://github.com/dono/central.git", "dono/central"),
        ("https://github.com/dono/central", "dono/central"),
    ],
)
def test_repositorio_do_central_pelo_remote(url, esperado, tmp_path):
    git("init", "-q", cwd=tmp_path)
    git("remote", "add", "origin", url, cwd=tmp_path)
    assert repositorio_do_central(tmp_path) == esperado


def test_repositorio_do_central_fora_do_github(tmp_path):
    git("init", "-q", cwd=tmp_path)
    git("remote", "add", "origin", "https://gitlab.com/dono/central.git", cwd=tmp_path)
    with pytest.raises(EscritaRecusada, match="não é do GitHub"):
        repositorio_do_central(tmp_path)


# --- montar (RF03) ------------------------------------------------------------------------


def test_montar_da_o_front_matter_da_spec(central):
    escritor, _ = escrita(central)
    doc_id, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    assert doc_id == "SPEC-ZERO-0001"
    frente = texto.split("---\n", 2)[1]
    assert frente.splitlines() == [
        "id: SPEC-ZERO-0001",
        "type: SPEC",
        'title: "Avisos por e-mail"',
        "status: in_review",
        'project: "ZERO"',
        'owner: "Owner"',
        'created: "2026-11-18"',
        'updated: "2026-11-18"',
        "relates_to: []",
        "parent_rfc: null",
        "parent_adr: null",
        'sizing: "medium"',
        "supersedes: null",
        "superseded_by: null",
        "tags: [fabrica-descoberta]",
    ]
    assert texto.endswith(CORPO_SPEC)


def test_montar_rfc_sem_parent(central):
    escritor, _ = escrita(central)
    doc_id, texto = escritor.montar(documento("RFC", "large", "# X\n"), "Owner", "2026-11-18")
    assert doc_id == "RFC-ZERO-0001"
    assert "parent_rfc" not in texto and "parent_adr" not in texto
    assert texto.endswith("\n\n# X\n")


def test_montar_pula_o_maior_id_do_registry_e_das_branches(central):
    clone, _nu = central
    registry = clone / "docs" / "ZERO" / "registry.yaml"
    registry.write_text(
        REGISTRY.replace(
            "documents: []",
            "documents:\n"
            '  - id: SPEC-ZERO-0003\n    type: SPEC\n    title: "a"\n    status: approved\n'
            '    owner: "o"\n    created: "2026-11-01"\n    updated: "2026-11-01"\n'
            '    path: "docs/ZERO/03-spec/SPEC-ZERO-0003.md"\n',
        ),
        encoding="utf-8",
    )
    git("commit", "-qam", "docs: registry", cwd=clone)
    git("push", "-q", "origin", "main", cwd=clone)
    escritor, _ = escrita(central)
    assert escritor.montar(documento(), "Owner", "2026-11-18")[0] == "SPEC-ZERO-0004"
    git("push", "-q", "origin", "main:refs/heads/docs/spec-zero-0007", cwd=clone)
    assert escritor.montar(documento(), "Owner", "2026-11-18")[0] == "SPEC-ZERO-0008"
    assert escritor.proximo_id("RFC") == "RFC-ZERO-0001"


def test_montar_corpo_sem_secao_obrigatoria_da_o_problema_do_kit(central):
    escritor, _ = escrita(central)
    corpo = CORPO_SPEC.replace("## Fora de escopo\nSMS.\n", "")
    _, texto = escritor.montar(documento(corpo=corpo), "Owner", "2026-11-18")
    problemas = escritor.problemas(texto)
    assert any("seção obrigatória ausente: 'Fora de escopo'" in p for p in problemas)


def test_montar_corpo_completo_nao_tem_problemas(central):
    escritor, _ = escrita(central)
    _, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    assert escritor.problemas(texto) == []


# --- partes da SPEC (SDD-FAB-0006) --------------------------------------------------------

LINHA_PARTE_1 = "# Parte 1 — Requisito (o QUÊ)\n"
LINHA_PARTE_2 = "# Parte 2 — Desenho (o COMO e o ONDE)\n"
SEM_PARTE_1 = "SPEC sem a linha '# Parte 1 — Requisito (o QUÊ)' do template"
SEM_PARTE_2 = (
    "SPEC sem a linha '# Parte 2 — Desenho (o COMO e o ONDE)' do template: "
    "a SDD enxuta lê o desenho a partir dela"
)
ORDEM_INVERTIDA = "SPEC com '# Parte 2' antes de '# Parte 1'"


def problemas_do_corpo(central, corpo, tipo="SPEC", sizing="medium"):
    escritor, _ = escrita(central)
    _, texto = escritor.montar(documento(tipo, sizing, corpo), "Owner", "2026-11-18")
    return escritor.problemas(texto)


def test_partes_spec_sem_parte_2_da_o_problema(central):
    problemas = problemas_do_corpo(central, CORPO_SPEC.replace(LINHA_PARTE_2, ""))
    assert SEM_PARTE_2 in problemas
    assert SEM_PARTE_1 not in problemas


def test_partes_spec_sem_parte_1_da_o_problema(central):
    problemas = problemas_do_corpo(central, CORPO_SPEC.replace(LINHA_PARTE_1, ""))
    assert SEM_PARTE_1 in problemas
    assert SEM_PARTE_2 not in problemas


def test_partes_spec_sem_as_duas_da_os_dois_problemas(central):
    corpo = CORPO_SPEC.replace(LINHA_PARTE_1, "").replace(LINHA_PARTE_2, "")
    problemas = problemas_do_corpo(central, corpo)
    assert problemas[-2:] == [SEM_PARTE_1, SEM_PARTE_2]


def test_partes_spec_com_ordem_invertida_da_o_problema(central):
    corpo = (
        CORPO_SPEC.replace(LINHA_PARTE_1, "@1\n")
        .replace(LINHA_PARTE_2, LINHA_PARTE_1)
        .replace("@1\n", LINHA_PARTE_2)
    )
    problemas = problemas_do_corpo(central, corpo)
    assert ORDEM_INVERTIDA in problemas
    assert SEM_PARTE_1 not in problemas and SEM_PARTE_2 not in problemas


def test_partes_parte_2_so_dentro_de_cerca_conta_como_ausente(central):
    corpo = CORPO_SPEC.replace(LINHA_PARTE_2, "```\n" + LINHA_PARTE_2 + "```\n")
    assert SEM_PARTE_2 in problemas_do_corpo(central, corpo)


def test_partes_parte_fora_do_inicio_da_linha_conta_como_ausente(central):
    corpo = CORPO_SPEC.replace(LINHA_PARTE_2, "Texto " + LINHA_PARTE_2)
    assert SEM_PARTE_2 in problemas_do_corpo(central, corpo)


def test_partes_rfc_sem_as_linhas_nao_e_conferida(central):
    problemas = problemas_do_corpo(central, "# Avisos por e-mail\n", "RFC", "large")
    assert not any("Parte" in p for p in problemas)


def test_partes_spec_montada_e_lida_pelo_compilador(central):
    from adapters.doc_traceability import compilador

    escritor, _ = escrita(central)
    _, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    assert escritor.problemas(texto) == []
    parte_2 = compilador._parte_2(texto)
    assert parte_2 is not None
    assert parte_2.startswith(modulo_central.PARTE_2)


def test_partes_descobridor_pede_as_duas_linhas_na_ordem():
    texto = (Path(__file__).parents[1] / "agents" / "descobridor.md").read_text(encoding="utf-8")
    assert modulo_central.PARTE_1 in texto and modulo_central.PARTE_2 in texto
    assert texto.index(modulo_central.PARTE_1) < texto.index(modulo_central.PARTE_2)


# --- cabeçalho da tabela de Requisitos funcionais (SDD-FAB-0007) ---------------------------

CABECALHO_DO_CORPO = "| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |"


def fora_do_template():
    return (
        "SPEC com a tabela de Requisitos funcionais fora do template: o cabeçalho deve ser "
        f"'{modulo_central.CABECALHO_RF}', com o critério EARS na 3ª coluna"
    )


def test_cabecalho_sem_a_coluna_requisito_da_o_problema(central):
    corpo = CORPO_SPEC.replace(
        CABECALHO_DO_CORPO, "| RF-ID | Critério de aceite (EARS) | Arquivos |"
    )
    assert fora_do_template() in problemas_do_corpo(central, corpo)


def test_cabecalho_com_colunas_trocadas_da_o_problema(central):
    corpo = CORPO_SPEC.replace(
        CABECALHO_DO_CORPO, "| RF-ID | Critério de aceite (EARS) | Requisito | Arquivos |"
    )
    assert fora_do_template() in problemas_do_corpo(central, corpo)


def test_cabecalho_do_template_nao_da_o_problema(central):
    assert fora_do_template() not in problemas_do_corpo(central, CORPO_SPEC)


def test_cabecalho_rfc_nao_e_conferida(central):
    corpo = CORPO_SPEC.replace(
        CABECALHO_DO_CORPO, "| RF-ID | Critério de aceite (EARS) | Arquivos |"
    )
    problemas = problemas_do_corpo(central, corpo, "RFC", "large")
    assert not any("Requisitos funcionais fora do template" in p for p in problemas)


def test_cabecalho_descobridor_da_o_cabecalho_exato():
    texto = (Path(__file__).parents[1] / "agents" / "descobridor.md").read_text(encoding="utf-8")
    assert modulo_central.CABECALHO_RF in texto


# --- abrir_pr (RF04) ----------------------------------------------------------------------


def test_abrir_pr_leva_o_documento_ao_remoto_por_branch(central):
    clone, nu = central
    escritor, github = escrita(central)
    doc_id, numero = abrir(escritor)
    assert numero == 40
    ramo = "docs/spec-zero-0001"
    arquivos = git("ls-tree", "-r", "--name-only", ramo, cwd=nu).splitlines()
    assert "docs/ZERO/03-spec/SPEC-ZERO-0001.md" in arquivos
    registry = yaml.safe_load(git("show", f"{ramo}:docs/ZERO/registry.yaml", cwd=nu))
    (entrada,) = registry["documents"]
    assert entrada["id"] == doc_id and entrada["status"] == "in_review"
    assert entrada["path"] == "docs/ZERO/03-spec/SPEC-ZERO-0001.md"
    assert entrada["tags"] == ["fabrica-descoberta"]
    assert "SPEC-ZERO-0001" in git("show", f"{ramo}:docs/ZERO/registry.md", cwd=nu)
    (pr,) = [c for c in github.chamadas if c[0] == "abrir_pr_documento"]
    assert pr[1] == ramo and pr[2] == "docs(ZERO): SPEC-ZERO-0001 — Avisos por e-mail"
    assert "central conferir <projeto> SPEC-ZERO-0001" in pr[3]
    assert "`Aprovado`" in pr[3]
    assert git("branch", "--show-current", cwd=clone) == "main"
    assert git("rev-parse", "main", cwd=nu) == git("rev-parse", "HEAD", cwd=clone)


def test_abrir_pr_com_clone_sujo_recusa_sem_push(central):
    clone, nu = central
    escritor, github = escrita(central)
    (clone / "solto.txt").write_text("x")
    with pytest.raises(EscritaRecusada, match="tem mudança local"):
        abrir(escritor)
    assert "abrir_pr_documento" not in github.nomes()
    assert git("branch", "--list", "docs/*", cwd=nu) == ""


def test_abrir_pr_fora_de_main_recusa_sem_push(central):
    clone, nu = central
    git("switch", "-q", "-c", "outro", cwd=clone)
    escritor, _github = escrita(central)
    with pytest.raises(EscritaRecusada, match="está em outro, não em main"):
        abrir(escritor)
    assert git("branch", "--list", "docs/*", cwd=nu) == ""


def test_abrir_pr_com_branch_existente_recusa(central):
    clone, _nu = central
    escritor, github = escrita(central)
    doc_id, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    git("push", "-q", "origin", "main:refs/heads/docs/spec-zero-0001", cwd=clone)
    with pytest.raises(EscritaRecusada, match="já existe no central"):
        escritor.abrir_pr(doc_id, "SPEC", texto, "Avisos por e-mail")
    assert "abrir_pr_documento" not in github.nomes()
    assert git("branch", "--show-current", cwd=clone) == "main"


# --- executor fora de approvers (RF07) ----------------------------------------------------


def test_executor_em_approvers_nao_abre_pr_nem_confere(central):
    _clone, nu = central
    escritor, github = escrita(central, login=APROVADOR)
    doc_id, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    mensagem = "a conta do executor dono está em approvers de docs/ZERO"
    with pytest.raises(EscritaRecusada, match=mensagem):
        escritor.abrir_pr(doc_id, "SPEC", texto, "t")
    with pytest.raises(EscritaRecusada, match=mensagem):
        escritor.conferir(doc_id)
    assert git("branch", "--list", "docs/*", cwd=nu) == ""
    assert "pr_aberta_do_ramo" not in github.nomes()


def test_executor_sem_approvers_no_registry_recusa_os_dois(central):
    clone, nu = central
    registry = clone / "docs" / "ZERO" / "registry.yaml"
    registry.write_text(REGISTRY.replace("approvers: [dono]\n", ""), encoding="utf-8")
    git("commit", "-qam", "docs: sem approvers", cwd=clone)
    git("push", "-q", "origin", "main", cwd=clone)
    escritor, _github = escrita(central)
    doc_id, texto = escritor.montar(documento(), "Owner", "2026-11-18")
    mensagem = "approvers não declarado no registry de docs/ZERO"
    with pytest.raises(EscritaRecusada, match=mensagem):
        escritor.abrir_pr(doc_id, "SPEC", texto, "t")
    with pytest.raises(EscritaRecusada, match=mensagem):
        escritor.conferir(doc_id)
    assert git("branch", "--list", "docs/*", cwd=nu) == ""


# --- conferir (RF05) ----------------------------------------------------------------------


def test_conferir_review_aprovada_sobre_o_head(central):
    clone, nu = central
    escritor, github = escrita(central)
    doc_id, numero = abrir(escritor)
    head = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    github.lista_de_reviews = [review(77, APROVADOR, "APPROVED", head)]
    decisao = escritor.conferir(doc_id)
    assert decisao["valida"] is True
    assert decisao["head"] == head
    assert decisao["approved_by"]["actor"] == APROVADOR
    assert decisao["approved_by"]["evidence"].endswith(f"/pull/{numero}#pullrequestreview-77")
    assert git("rev-parse", "docs/spec-zero-0001", cwd=nu) == head
    assert git("worktree", "list", cwd=clone).count("\n") == 0


def test_conferir_review_sobre_commit_anterior_nao_vale(central):
    _, nu = central
    escritor, github = escrita(central)
    doc_id, _ = abrir(escritor)
    anterior = git("rev-parse", "main", cwd=nu)
    github.lista_de_reviews = [review(1, APROVADOR, "APPROVED", anterior)]
    decisao = escritor.conferir(doc_id)
    assert decisao["valida"] is False and decisao["motivos"]


def test_conferir_changes_requested_posterior_derruba(central):
    _, nu = central
    escritor, github = escrita(central)
    doc_id, _ = abrir(escritor)
    head = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    github.lista_de_reviews = [
        review(1, APROVADOR, "APPROVED", head, quando="2026-11-18T12:00:00Z"),
        review(2, APROVADOR, "CHANGES_REQUESTED", head, quando="2026-11-18T13:00:00Z"),
    ]
    decisao = escritor.conferir(doc_id)
    assert decisao["valida"] is False and decisao["motivos"]


def test_conferir_sem_pr_aberta(central):
    escritor, _ = escrita(central)
    with pytest.raises(EscritaRecusada, match="nenhuma PR aberta para docs/spec-zero-0009"):
        escritor.conferir("SPEC-ZERO-0009")


@pytest.mark.parametrize(
    "saida",
    [
        "print('saida qualquer')",
        """print('{"valida": true, "motivos": [], "approved_by": {}}')""",
    ],
)
def test_conferir_com_saida_fora_do_contrato_nao_aprova(saida, tmp_path):
    scripts = tmp_path / "kit" / "_framework" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "review_approval.py").write_text(saida + "\n")
    decisao = Framework(tmp_path / "kit").decidir_review(
        tmp_path / "d.md", tmp_path / "r.json", "abc", "https://github.com/d/c/pull/1"
    )
    assert decisao["valida"] is False and decisao["approved_by"] is None
    (motivo,) = decisao["motivos"]
    assert motivo.startswith("saída fora do contrato dtf.review-approval/1: ")


# --- integrar (RF06) ----------------------------------------------------------------------


def aprovado(central):
    _clone, nu = central
    escritor, github = escrita(central)
    doc_id, _numero = abrir(escritor)
    head = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    github.lista_de_reviews = [review(77, APROVADOR, "COMMENTED", head, corpo="Aprovado")]
    return escritor, github, doc_id, head


def test_integrar_grava_a_aprovacao_na_mesma_pr_e_faz_o_merge(central):
    clone, nu = central
    escritor, github, doc_id, head = aprovado(central)
    decisao = escritor.conferir(doc_id)
    assert decisao["valida"] is True
    sha = escritor.integrar(doc_id, decisao)
    ramo = "docs/spec-zero-0001"
    assert sha == git("rev-parse", ramo, cwd=nu)
    assert git("rev-parse", f"{ramo}~1", cwd=nu) == head
    diff = git("diff", head, ramo, "--", "docs/ZERO/03-spec/SPEC-ZERO-0001.md", cwd=nu)
    mudou = [
        linha
        for linha in diff.splitlines()
        if linha[:1] in "+-" and not linha.startswith(("+++", "---"))
    ]
    assert "-status: in_review" in mudou and "+status: approved" in mudou
    assert any(linha.startswith("+updated:") for linha in mudou)
    assert "+approved_by:" in mudou
    assert all(
        linha.startswith(("-status", "+status", "-updated", "+updated", "+approved_by", "+  "))
        for linha in mudou
    )
    registry = yaml.safe_load(git("show", f"{ramo}:docs/ZERO/registry.yaml", cwd=nu))
    assert registry["documents"][0]["status"] == "approved"
    texto = git("show", f"{ramo}:docs/ZERO/03-spec/SPEC-ZERO-0001.md", cwd=nu)
    frente = yaml.safe_load(texto.split("---\n", 2)[1])
    assert frente["approved_by"]["actor"] == APROVADOR
    assert frente["approved_by"]["kind"] == "human"
    assert github.nomes().index("esperar_checks") < github.nomes().index("fazer_merge_de_documento")
    assert git("branch", "--show-current", cwd=clone) == "main"


def test_integrar_com_check_falho_nao_faz_merge(central):
    escritor, github, doc_id, _ = aprovado(central)
    github.situacao = ("falhou", "validate")
    with pytest.raises(EscritaRecusada, match="checks da PR #40: falhou validate"):
        escritor.integrar(doc_id, escritor.conferir(doc_id))
    assert "fazer_merge_de_documento" not in github.nomes()
    assert git("branch", "--show-current", cwd=central[0]) == "main"


def test_integrar_repetido_nao_cria_outro_commit(central):
    _, nu = central
    escritor, github, doc_id, _ = aprovado(central)
    github.situacao = ("pendente", "tempo máximo de espera do CI")
    with pytest.raises(EscritaRecusada, match="pendente"):
        escritor.integrar(doc_id, escritor.conferir(doc_id))
    depois_da_aprovacao = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    github.situacao = ("passou", "")
    github.chamadas.clear()
    decisao = escritor.conferir(doc_id)
    assert decisao["valida"] is True and "reviews" not in github.nomes()
    assert escritor.integrar(doc_id, decisao) == depois_da_aprovacao
    assert git("rev-parse", "docs/spec-zero-0001", cwd=nu) == depois_da_aprovacao
    assert "fazer_merge_de_documento" in github.nomes()


def test_integrar_com_head_mudado_depois_da_decisao(central):
    clone, nu = central
    escritor, github, doc_id, _ = aprovado(central)
    decisao = escritor.conferir(doc_id)
    outro = clone.parent / "outro"
    git("clone", "-q", "-b", "docs/spec-zero-0001", str(nu), str(outro), cwd=clone.parent)
    (outro / "docs" / "ZERO" / "nota.md").write_text("x\n")
    git("add", "-A", cwd=outro)
    git("commit", "-qm", "docs: nota", cwd=outro)
    git("push", "-q", "origin", "docs/spec-zero-0001", cwd=outro)
    novo = git("rev-parse", "HEAD", cwd=outro)
    with pytest.raises(EscritaRecusada, match=f"head de docs/spec-zero-0001 mudou para {novo}"):
        escritor.integrar(doc_id, decisao)
    assert git("rev-parse", "docs/spec-zero-0001", cwd=nu) == novo
    assert "fazer_merge_de_documento" not in github.nomes()


def test_integrar_com_head_atrasado_espera_o_commit_enviado_antes_dos_checks(central):
    _, nu = central
    escritor, github, doc_id, head = aprovado(central)
    decisao = escritor.conferir(doc_id)
    github.head_atrasado = head
    github.leituras_atrasadas = 3
    github.chamadas.clear()
    dormidas: list[int] = []
    escritor.integrar(doc_id, decisao, dormir=dormidas.append)
    enviado = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    heads = [c[1] for c in github.chamadas if c[0] == "head_da_pr"]
    assert heads == [head, head, head, enviado]
    assert dormidas == [ESPERA_DO_HEAD_SEGUNDOS] * 3
    nomes = github.nomes()
    ultimo_head = len(nomes) - 1 - nomes[::-1].index("head_da_pr")
    assert ultimo_head < nomes.index("esperar_checks") < nomes.index("fazer_merge_de_documento")


def test_integrar_com_head_que_nao_chega_recusa_sem_checks_nem_merge(central):
    _, nu = central
    escritor, github, doc_id, head = aprovado(central)
    decisao = escritor.conferir(doc_id)
    github.head_atrasado = head
    github.leituras_atrasadas = 10_000
    dormidas: list[int] = []
    with pytest.raises(EscritaRecusada) as erro:
        escritor.integrar(doc_id, decisao, dormir=dormidas.append)
    enviado = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    assert str(erro.value) == (
        f"head da PR #40 segue em {head}, não em {enviado}, "
        f"depois de {LIMITE_DO_HEAD_SEGUNDOS}s: rode conferir de novo"
    )
    assert "depois de 120s" in str(erro.value)
    assert sum(dormidas) == LIMITE_DO_HEAD_SEGUNDOS
    assert "esperar_checks" not in github.nomes()
    assert "fazer_merge_de_documento" not in github.nomes()
    assert git("branch", "--show-current", cwd=central[0]) == "main"


def test_integrar_na_retomada_tambem_espera_o_head(central):
    _, nu = central
    escritor, github, doc_id, head = aprovado(central)
    github.situacao = ("pendente", "tempo máximo de espera do CI")
    with pytest.raises(EscritaRecusada, match="pendente"):
        escritor.integrar(doc_id, escritor.conferir(doc_id), dormir=lambda _s: None)
    enviado = git("rev-parse", "docs/spec-zero-0001", cwd=nu)
    github.situacao = ("passou", "")
    decisao = escritor.conferir(doc_id)
    github.head_atrasado = head
    github.leituras_atrasadas = 2
    github.chamadas.clear()
    dormidas: list[int] = []
    assert escritor.integrar(doc_id, decisao, dormir=dormidas.append) == enviado
    heads = [c[1] for c in github.chamadas if c[0] == "head_da_pr"]
    assert heads == [head, head, enviado]
    assert dormidas == [ESPERA_DO_HEAD_SEGUNDOS] * 2
    assert github.nomes().index("esperar_checks") > max(
        i for i, n in enumerate(github.nomes()) if n == "head_da_pr"
    )


def test_integrar_grava_updated_na_data_utc_como_a_descoberta(central, monkeypatch):
    _, nu = central
    escritor, _github, doc_id, _ = aprovado(central)
    decisao = escritor.conferir(doc_id)

    class DataLocal(datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 18)

    class Agora(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is datetime.UTC
            return cls(2026, 11, 19, 0, 18, tzinfo=datetime.UTC)

    falso = types.SimpleNamespace(UTC=datetime.UTC, date=DataLocal, datetime=Agora)
    monkeypatch.setattr(modulo_central, "datetime", falso)
    escritor.integrar(doc_id, decisao)
    ramo = "docs/spec-zero-0001"
    texto = git("show", f"{ramo}:docs/ZERO/03-spec/SPEC-ZERO-0001.md", cwd=nu)
    frente = yaml.safe_load(texto.split("---\n", 2)[1])
    assert str(frente["updated"]) == "2026-11-19"
    registry = yaml.safe_load(git("show", f"{ramo}:docs/ZERO/registry.yaml", cwd=nu))
    assert str(registry["documents"][0]["updated"]) == "2026-11-19"


def test_integrar_com_validate_state_reprovado_nao_envia(central):
    clone, nu = central
    escritor, github, doc_id, head = aprovado(central)
    decisao = escritor.conferir(doc_id)
    decisao["approved_by"] = decisao["approved_by"] | {"content_sha256": "0" * 64}
    with pytest.raises(
        EscritaRecusada, match="validação antes do push: .*mudou depois da aprovação"
    ):
        escritor.integrar(doc_id, decisao)
    assert git("rev-parse", "docs/spec-zero-0001", cwd=nu) == head
    assert git("status", "--porcelain", cwd=clone) == ""
    assert "fazer_merge_de_documento" not in github.nomes()


def test_cli_erro_ao_montar_a_escrita_sai_com_1(tmp_path, monkeypatch, capsys):
    from fabrica import __main__ as cli
    from fabrica.pipeline import Projeto

    git("init", "-q", cwd=tmp_path)
    git("remote", "add", "origin", "https://gitlab.com/dono/central.git", cwd=tmp_path)
    projeto = Projeto("ZERO", "repo", "o/r", central=str(tmp_path))
    monkeypatch.setattr(cli, "carregar_projeto", lambda nome: projeto)
    monkeypatch.setattr(cli, "montar_fonte", lambda projeto: None)
    monkeypatch.setattr(cli, "ClaudeDockerRunner", lambda: None)
    monkeypatch.setattr(cli, "DIR_DADOS", tmp_path / "dados")
    for argv in (["central", "conferir", "zero", "SPEC-ZERO-0001"], ["descobrir", "zero", "x"]):
        monkeypatch.setattr("sys.argv", ["fabrica", *argv])
        assert cli.main() == 1
        assert "erro: remote origin de" in capsys.readouterr().out


def test_integrar_recusa_aprovacao_invalida(central):
    escritor, github = escrita(central)
    with pytest.raises(EscritaRecusada, match="aprovação inválida"):
        escritor.integrar("SPEC-ZERO-0001", {"valida": False})
    assert github.chamadas == []


# --- CLI (RF02, RF05) ---------------------------------------------------------------------


class EscritaDeCli:
    def __init__(self, decisao=None, erro=None):
        self.decisao = decisao
        self.erro = erro
        self.integrados = []

    def conferir(self, doc_id):
        if self.erro:
            raise self.erro
        return self.decisao

    def integrar(self, doc_id, decisao):
        self.integrados.append(doc_id)
        return "abc123"


def test_cli_central_conferir_com_aprovacao_invalida_sai_com_1(capsys):
    from fabrica import __main__ as cli

    escrita_cli = EscritaDeCli({"valida": False, "motivos": ["review sobre commit anterior"]})
    assert cli.central_conferir(escrita_cli, "SPEC-ZERO-0001") == 1
    assert "- review sobre commit anterior" in capsys.readouterr().out
    assert escrita_cli.integrados == []


@pytest.mark.parametrize(
    "erro",
    [
        EscritaRecusada("nenhuma PR aberta para docs/spec-zero-0001"),
        FalhaDePublicacao("gh api: 502"),
        PublicacaoRecusada("merge recusado"),
    ],
)
def test_cli_central_conferir_com_recusa_sai_com_1(erro, capsys):
    from fabrica import __main__ as cli

    assert cli.central_conferir(EscritaDeCli(erro=erro), "SPEC-ZERO-0001") == 1
    assert f"erro: {erro}" in capsys.readouterr().out


def test_cli_central_conferir_valido_integra_e_sai_com_0(capsys):
    from fabrica import __main__ as cli

    escrita_cli = EscritaDeCli({"valida": True, "motivos": [], "approved_by": {}})
    assert cli.central_conferir(escrita_cli, "SPEC-ZERO-0001") == 0
    assert "SPEC-ZERO-0001 approved e em main do central pelo merge abc123" in (
        capsys.readouterr().out
    )
    assert escrita_cli.integrados == ["SPEC-ZERO-0001"]


def test_cli_conversar_no_central_mostra_a_pr_e_o_conferir(capsys):
    from fabrica import __main__ as cli
    from fabrica.descoberta import NO_CENTRAL

    class DescobertaNoCentral:
        def avancar(self, sessao):
            return NO_CENTRAL

        def dados(self, sessao):
            return {"doc_id": "SPEC-ZERO-0001", "pr": 31}

    assert cli.conversar(DescobertaNoCentral(), "s1") == 0
    saida = capsys.readouterr().out
    assert "Rascunho SPEC-ZERO-0001 na PR #31 do central, em in_review." in saida
    assert "uv run python -m fabrica central conferir <projeto> SPEC-ZERO-0001" in saida
