import pytest

from fabrica.gates import (
    PatchInvalido,
    arquivos_do_patch,
    gate_caminhos_protegidos,
    gate_escopo,
    gate_patch,
    gate_sizing,
    gate_so_testes,
    relatorio_de_reprovacao,
)
from fabrica.roteamento import calcular_risco
from fabrica.versao import proxima_versao


def patch_de(*arquivos):
    return "".join(f"diff --git a/{a} b/{a}\n--- a/{a}\n+++ b/{a}\n" for a in arquivos)


def test_escopo_aprova_dentro_da_lista():
    assert gate_escopo(patch_de("a.py", "tests/t.py"), ["a.py", "tests/*.py"]).aprovado


def test_escopo_reprova_arquivo_fora_da_lista():
    resultado = gate_escopo(patch_de("a.py", "b.py"), ["a.py"])
    assert not resultado.aprovado and "b.py" in resultado.detalhe


def test_renomeio_conta_os_dois_lados():
    patch = "diff --git a/a.py b/z.py\nsimilarity index 100%\nrename from a.py\nrename to z.py\n"
    assert arquivos_do_patch(patch) == ["a.py", "z.py"]
    assert not gate_escopo(patch, ["z.py"]).aprovado


def test_caminho_com_aspas_e_recusado():
    with pytest.raises(PatchInvalido):
        arquivos_do_patch('diff --git "a/x\\ty" "b/x\\ty"\n')
    assert not gate_patch('diff --git "a/x\\ty" "b/x\\ty"\n').aprovado


def test_caminho_ambiguo_e_recusado():
    """Um arquivo chamado `z b/a.py` não pode se passar por `a.py`, que está na lista."""
    patch = "diff --git a/z b/a.py b/z b/a.py\n"
    assert "ambíguo" in gate_patch(patch).detalhe


def test_patch_vazio_e_recusado():
    assert not gate_patch("  \n").aprovado


def test_link_simbolico_e_recusado():
    patch = "diff --git a/l b/l\nnew file mode 120000\n--- /dev/null\n+++ b/l\n"
    assert "link simbólico" in gate_patch(patch).detalhe


@pytest.mark.parametrize(
    "arquivo",
    [
        ".github/workflows/x.yml",
        ".claude/settings.json",
        ".husky/pre-push",
        "_framework/a",
        "deploy/x",
    ],
)
def test_caminho_protegido_recusado_sem_risco_alto(arquivo):
    assert not gate_caminhos_protegidos(patch_de(arquivo), [arquivo], "baixo").aprovado


def test_caminho_protegido_recusado_fora_da_sdd_mesmo_com_risco_alto():
    assert not gate_caminhos_protegidos(patch_de("deploy/x"), ["a.py"], "alto").aprovado


def test_caminho_protegido_aceito_com_sdd_e_risco_alto():
    assert gate_caminhos_protegidos(patch_de("deploy/x"), ["deploy/x"], "alto").aprovado


def test_testador_so_toca_em_teste():
    assert gate_so_testes(patch_de("tests/a.py", "web/__tests__/b.ts", "c/d.test.ts")).aprovado
    resultado = gate_so_testes(patch_de("tests/a.py", "estoque/itens.py"))
    assert not resultado.aprovado and "estoque/itens.py" in resultado.detalhe


def test_testador_sem_mudanca_e_aceito():
    assert gate_so_testes("").aprovado


def test_small_com_diff_grande_contradiz_a_declaracao():
    grande = patch_de("a", "b", "c", "d", "e")
    assert not gate_sizing(grande, "small").aprovado
    assert gate_sizing(patch_de("a", "b", "c", "d"), "small").aprovado
    assert gate_sizing(grande, "medium").aprovado


def test_relatorio_tem_formato_padrao():
    relatorio = relatorio_de_reprovacao([gate_patch("")], 2)
    assert relatorio["status"] == "reprovado" and relatorio["causa"] == "implementacao"
    assert relatorio["tentativa"] == 2 and relatorio["testes"] == {"passaram": 0, "falharam": 1}


@pytest.mark.parametrize(
    ("entrada", "risco"),
    [
        ({"sizing": "small", "arquivos_permitidos": ["a.py"]}, None),
        ({"sizing": "medium", "arquivos_permitidos": ["a.py"]}, None),
        ({"sizing": "small", "titulo": "Corrigir autenticação", "arquivos_permitidos": []}, "alto"),
        ({"sizing": "small", "titulo": "Estorno de pagamento", "arquivos_permitidos": []}, "alto"),
        ({"sizing": "small", "resumo": "Guarda o CPF.", "arquivos_permitidos": []}, "alto"),
        (
            {
                "sizing": "small",
                "requisitos": [{"requisito": "Ficha", "aceite": "Mostrar o prontuário."}],
                "arquivos_permitidos": [],
            },
            "alto",
        ),
        ({"sizing": "small", "titulo": "Apagar rascunho", "arquivos_permitidos": []}, None),
        ({"sizing": "large", "arquivos_permitidos": ["a.py"]}, "alto"),
        ({"sizing": "small", "arquivos_permitidos": ["deploy/x.sh"]}, "alto"),
        ({"sizing": "small", "arquivos_permitidos": ["prisma/migrations/1.sql"]}, "alto"),
        ({"sizing": "small", "titulo": "Tela de login", "arquivos_permitidos": ["a.py"]}, "alto"),
        ({"arquivos_permitidos": ["a.py"]}, None),
        ({"sizing": "desconhecido", "arquivos_permitidos": ["a.py"]}, None),
    ],
)
def test_risco_por_regras(entrada, risco):
    assert calcular_risco(entrada) == risco


@pytest.mark.parametrize(
    ("atual", "mensagens", "esperada"),
    [
        ("v0.1.0", ["fix: a"], "0.1.1"),
        ("v0.1.0", ["fix: a", "feat: b"], "0.2.0"),
        ("v0.1.0", ["feat(x): b"], "0.2.0"),
        ("v0.1.2", ["feat!: b"], "1.0.0"),
        ("v0.1.2", ["fix: a\n\nBREAKING CHANGE: muda"], "1.0.0"),
        ("v1.2.3", ["docs: a"], "1.2.4"),
        (None, ["feat: a"], "0.1.0"),
        ("v1.0.0", ["mensagem livre"], "1.0.1"),
    ],
)
def test_proxima_versao(atual, mensagens, esperada):
    assert proxima_versao(atual, mensagens) == esperada
