"""Gates determinísticos sobre o patch. Nada aqui confia no que o agente declarou."""

import fnmatch
import re
from dataclasses import dataclass

CAMINHOS_PROTEGIDOS = (".github/", ".claude/", ".husky/", "_framework/", "deploy/", ".git/")
DIFF_RE = re.compile(r"^diff --git (?P<resto>.+)$", re.MULTILINE)
CAMINHO_RE = re.compile(r"^a/(?P<a>.+) b/(?P<b>.+)$")
LINK_SIMBOLICO_RE = re.compile(r"^(?:new file mode|new mode) 120000$", re.MULTILINE)


PADROES_DE_TESTE = (
    "tests/*",
    "test/*",
    "*/tests/*",
    "*/test/*",
    "__tests__/*",
    "*/__tests__/*",
    "e2e/*",
    "*/e2e/*",
    "test_*.py",
    "*/test_*.py",
    "*_test.py",
    "*.test.*",
    "*.spec.*",
)
LIMITE_DE_ARQUIVOS_SMALL = 4


@dataclass(frozen=True)
class ResultadoGate:
    nome: str
    aprovado: bool
    detalhe: str = ""


class PatchInvalido(Exception):
    pass


def arquivos_do_patch(patch: str) -> list[str]:
    arquivos: set[str] = set()
    for achado in DIFF_RE.finditer(patch):
        resto = achado["resto"]
        if '"' in resto:
            raise PatchInvalido(f"caminho com caractere especial: {resto}")
        if resto.count(" b/") != 1:
            raise PatchInvalido(f"caminho ambíguo: {resto}")
        partes = CAMINHO_RE.match(resto)
        if not partes:
            raise PatchInvalido(f"cabeçalho de diff não reconhecido: {resto}")
        arquivos |= {partes["a"], partes["b"]}
    return sorted(arquivos)


def gate_patch(patch: str) -> ResultadoGate:
    if not patch.strip():
        return ResultadoGate("patch", False, "patch vazio: nada foi implementado")
    if LINK_SIMBOLICO_RE.search(patch):
        return ResultadoGate("patch", False, "patch cria link simbólico")
    try:
        arquivos_do_patch(patch)
    except PatchInvalido as erro:
        return ResultadoGate("patch", False, str(erro))
    return ResultadoGate("patch", True)


def _permitido(arquivo: str, padroes: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(arquivo, padrao) for padrao in padroes)


def gate_escopo(patch: str, arquivos_permitidos: list[str]) -> ResultadoGate:
    fora = [a for a in arquivos_do_patch(patch) if not _permitido(a, arquivos_permitidos)]
    if fora:
        return ResultadoGate("escopo", False, f"fora da lista da SDD: {', '.join(fora)}")
    return ResultadoGate("escopo", True)


def gate_caminhos_protegidos(
    patch: str, arquivos_permitidos: list[str], risco: str
) -> ResultadoGate:
    protegidos = [a for a in arquivos_do_patch(patch) if a.startswith(CAMINHOS_PROTEGIDOS)]
    if not protegidos:
        return ResultadoGate("caminhos protegidos", True)
    negados = [a for a in protegidos if risco != "alto" or not _permitido(a, arquivos_permitidos)]
    if negados:
        return ResultadoGate("caminhos protegidos", False, f"proibido: {', '.join(negados)}")
    return ResultadoGate(
        "caminhos protegidos", True, f"autorizado pela SDD: {', '.join(protegidos)}"
    )


def gate_so_testes(patch: str, padroes: tuple[str, ...] = PADROES_DE_TESTE) -> ResultadoGate:
    """O testador não altera produção. Patch dele fora dos padrões de teste é recusado inteiro."""
    if not patch.strip():
        return ResultadoGate("só testes", True, "nenhum teste novo")
    fora = [a for a in arquivos_do_patch(patch) if not _permitido(a, list(padroes))]
    if fora:
        return ResultadoGate("só testes", False, f"testador alterou produção: {', '.join(fora)}")
    return ResultadoGate("só testes", True)


def gate_sizing(patch: str, sizing: str | None) -> ResultadoGate:
    """O framework define `small` como cerca de 3 arquivos. O diff real confere a declaração."""
    total = len(arquivos_do_patch(patch))
    if sizing == "small" and total > LIMITE_DE_ARQUIVOS_SMALL:
        return ResultadoGate("sizing", False, f"declarada small, mas o diff toca {total} arquivos")
    return ResultadoGate("sizing", True)


def relatorio_de_reprovacao(gates: list[ResultadoGate], tentativa: int) -> dict:
    """Formato padrão de validação para devolver ao desenvolvedor."""
    reprovados = [g for g in gates if not g.aprovado]
    return {
        "status": "reprovado",
        "testes": {"passaram": len(gates) - len(reprovados), "falharam": len(reprovados)},
        "evidencias": [f"gate {g.nome}: {g.detalhe}" for g in reprovados],
        "causa": "implementacao",
        "tentativa": tentativa,
    }
