"""Compila uma SDD do framework de rastreabilidade na entrada de um contrato.

Parsing derivado de `framework_lib.py` e `validate_state.py` do framework (MIT, mesmo
autor). SDD que não compila para na entrada, sem gastar tokens.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
RF_ID_RE = re.compile(r"\bRF-?\d+\b")
_PIPE_ESCAPADO = "\\|"
_SENTINELA = "\x00"
SEM_COMANDO = {"", "n/a", "-", "—"}
DIR_MOLDES = "docs/fabrica/moldes"
LEAN_COLUNAS = ["rf-id", "origem", "requisito (resumo)", "arquivos"]


class SddInvalida(Exception):
    """A SDD não vira contrato. É problema de especificação, não de implementação."""

    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


@dataclass(frozen=True)
class Tabela:
    cabecalho: list[str]
    linhas: list[list[str]]

    def indice(self, *termos: str) -> int | None:
        for i, coluna in enumerate(self.cabecalho):
            if any(termo in coluna for termo in termos):
                return i
        return None


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _celulas(linha: str) -> list[str]:
    mascarada = linha.strip().replace(_PIPE_ESCAPADO, _SENTINELA)
    return [c.strip().replace(_SENTINELA, "|") for c in mascarada.strip("|").split("|")]


def _sem_cercas_de_codigo(texto: str) -> str:
    return re.sub(r"^```.*?^```[ \t]*$", "", texto, flags=re.MULTILINE | re.DOTALL)


def secao(corpo: str, titulo: str) -> str | None:
    padrao = re.compile(
        rf"^##\s*{re.escape(titulo)}.*?$(.*?)(?=^##\s|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    achado = padrao.search(_sem_cercas_de_codigo(corpo))
    return achado.group(1).strip() if achado else None


def primeira_tabela(texto: str | None) -> Tabela | None:
    linhas = [li for li in (texto or "").splitlines() if li.strip().startswith("|")]
    if len(linhas) < 2:
        return None
    dados = [_celulas(li) for li in linhas[2:]]
    return Tabela([_normalizar(c) for c in _celulas(linhas[0])], [d for d in dados if any(d)])


def _celula(linha: list[str], indice: int | None) -> str:
    return linha[indice] if indice is not None and indice < len(linha) else ""


def _sem_crases(texto: str) -> str:
    texto = texto.strip()
    return texto[1:-1] if len(texto) > 1 and texto[0] == texto[-1] == "`" else texto


def _caminhos(celula: str) -> list[str]:
    entre_crases = re.findall(r"`([^`]+)`", celula)
    candidatos = entre_crases or re.split(r"[,;]", celula)
    return [c.strip() for c in candidatos if c.strip() and not re.search(r"\s", c.strip())]


def _criterios(corpo: str, problemas: list[str]) -> list[dict]:
    tabela = primeira_tabela(secao(corpo, "Critérios de aceite"))
    if tabela is None or not tabela.linhas:
        problemas.append("sem tabela de critérios de aceite")
        return []
    i_comando = tabela.indice("comando")
    if i_comando is None:
        problemas.append("tabela de critérios sem coluna de comando")
        return []
    i_numero = tabela.indice("#")
    i_criterio = tabela.indice("criterio")
    i_esperado = tabela.indice("resultado")
    i_perfil = tabela.indice("perfil")

    criterios = []
    for linha in tabela.linhas:
        numero = _celula(linha, i_numero)
        comando = _sem_crases(_celula(linha, i_comando))
        perfil = _normalizar(_celula(linha, i_perfil)) or "automatizado"
        if perfil == "automatizado" and comando.lower() in SEM_COMANDO:
            problemas.append(f"critério {numero} automatizado sem comando")
        criterios.append(
            {
                "numero": numero,
                "criterio": _celula(linha, i_criterio),
                "comando": comando,
                "esperado": _celula(linha, i_esperado),
                "perfil": perfil,
            }
        )
    if criterios and not any(c["perfil"] == "automatizado" for c in criterios):
        problemas.append("nenhum critério automatizado")
    return criterios


def _requisitos(corpo: str, problemas: list[str]) -> list[dict]:
    texto = secao(corpo, "Requisitos consolidados")
    tabela = primeira_tabela(texto)
    if tabela is not None and tabela.linhas:
        i_id = tabela.indice("rf-id", "rf")
        i_requisito = tabela.indice("requisito")
        i_aceite = tabela.indice("criterio")
        requisitos = [
            {
                "id": _celula(linha, i_id),
                "requisito": _celula(linha, i_requisito),
                "aceite": _celula(linha, i_aceite),
            }
            for linha in tabela.linhas
            if RF_ID_RE.search(_celula(linha, i_id))
        ]
        if requisitos:
            return requisitos
    ids = sorted(set(RF_ID_RE.findall(texto or "")))
    if not ids:
        problemas.append("sem requisitos com RF-ID")
    return [{"id": rf, "requisito": "", "aceite": ""} for rf in ids]


def _arquivos_permitidos(corpo: str) -> list[str]:
    arquivos: list[str] = []
    fontes = [
        (secao(corpo, "Decomposição em tasks"), ("arquivos tocados", "arquivos")),
        (secao(corpo, "Requisitos consolidados"), ("arquivos",)),
    ]
    for texto, colunas in fontes:
        tabela = primeira_tabela(texto)
        if tabela is None:
            continue
        indice = tabela.indice(*colunas)
        for linha in tabela.linhas:
            arquivos += _caminhos(_celula(linha, indice))
    return sorted(set(arquivos))


def _tarefas(corpo: str) -> list[dict]:
    tabela = primeira_tabela(secao(corpo, "Decomposição em tasks"))
    if tabela is None:
        return []
    i_numero = tabela.indice("#")
    i_tarefa = tabela.indice("task")
    i_arquivos = tabela.indice("arquivos")
    return [
        {
            "numero": _celula(linha, i_numero),
            "descricao": _celula(linha, i_tarefa),
            "arquivos": _caminhos(_celula(linha, i_arquivos)),
        }
        for linha in tabela.linhas
    ]


def _molde(raiz_projeto: Path | None, nome: str | None, problemas: list[str]) -> str | None:
    """SDD curta aponta um molde do projeto, em vez de repetir o padrão no próprio corpo."""
    if not nome:
        return None
    caminho = (raiz_projeto or Path(".")) / DIR_MOLDES / f"{nome}.md"
    if not caminho.is_file():
        problemas.append(f"molde {nome!r} não encontrado em {DIR_MOLDES}")
        return None
    return caminho.read_text(encoding="utf-8")


def _enxuta(frente: dict, corpo: str) -> bool:
    """SDD enxuta: tem origem e a tabela de requisitos por referência, como no kit 2.7.0."""
    tabela = primeira_tabela(secao(corpo, "Requisitos consolidados"))
    return (
        bool(frente.get("source_docs"))
        and tabela is not None
        and (tabela.cabecalho == LEAN_COLUNAS)
    )


def _fora_de_cercas(texto: str, padrao: str) -> list[re.Match]:
    """As linhas que casam `padrao` e não estão dentro de uma cerca de código."""
    cercas = [m.span() for m in re.finditer(r"^```.*?^```[ \t]*$", texto, re.MULTILINE | re.DOTALL)]
    return [
        m
        for m in re.finditer(padrao, texto, re.MULTILINE)
        if not any(inicio <= m.start() < fim for inicio, fim in cercas)
    ]


def _parte_2(texto: str) -> str | None:
    """Da linha `# Parte 2` até o fim, sem a seção de autorrevisão, com as cercas intactas."""
    achados = _fora_de_cercas(texto, r"^# Parte 2.*$")
    if not achados:
        return None
    parte = texto[achados[0].start() :]
    cabecalhos = _fora_de_cercas(parte, r"^#{1,2} .*$")
    trechos, inicio = [], 0
    for i, cabecalho in enumerate(cabecalhos):
        if cabecalho.group().startswith("## Autorrevis"):
            fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(parte)
            trechos.append(parte[inicio : cabecalho.start()])
            inicio = fim
    trechos.append(parte[inicio:])
    return "".join(trechos).strip()


def _decisao(texto: str) -> str | None:
    return secao(texto, "Decisão")


def _rf(rf: str) -> str:
    return rf.replace("-", "")


def _aceites(texto: str) -> dict[str, str]:
    tabela = primeira_tabela(secao(texto, "Requisitos funcionais"))
    if tabela is None:
        return {}
    i_id = tabela.indice("rf-id", "rf")
    i_criterio = tabela.indice("criterio")
    return {_rf(_celula(linha, i_id)): _celula(linha, i_criterio) for linha in tabela.linhas}


def _origem_da_linha(corpo: str) -> dict[str, str]:
    tabela = primeira_tabela(secao(corpo, "Requisitos consolidados"))
    if tabela is None:
        return {}
    i_id, i_origem = tabela.indice("rf-id"), tabela.indice("origem")
    return {_celula(linha, i_id): _celula(linha, i_origem) for linha in tabela.linhas}


def _resolver_referencia(
    frente: dict, corpo: str, requisitos: list[dict], origens: dict[str, str], problemas: list[str]
) -> str:
    """Monta `especificacao` e preenche o `aceite` de cada requisito com o texto do central."""
    ids = [str(d.get("id")) for d in frente.get("source_docs") or [] if isinstance(d, dict)]
    for doc_id in ids:
        if doc_id not in origens:
            problemas.append(f"origem {doc_id} não está no clone do central")
    blocos = []
    for doc_id in [i for i in ids if i.startswith("SPEC-") and i in origens]:
        bloco = _parte_2(origens[doc_id])
        if bloco is None:
            problemas.append(f"{doc_id} sem '# Parte 2'")
        else:
            blocos.append(f"# {doc_id}\n\n{bloco}")
    for doc_id in [i for i in ids if i.startswith("ADR-") and i in origens]:
        bloco = _decisao(origens[doc_id])
        if bloco is None:
            problemas.append(f"{doc_id} sem seção 'Decisão'")
        else:
            blocos.append(f"# {doc_id}\n\n{bloco}")
    origem_de = _origem_da_linha(corpo)
    for requisito in requisitos:
        rf, spec = requisito["id"], origem_de.get(requisito["id"], "")
        aceite = _aceites(origens[spec]).get(_rf(rf)) if spec in origens else None
        if aceite is None:
            if spec in origens:
                problemas.append(f"{rf} sem critério de aceite em {spec}")
            continue
        requisito["aceite"] = aceite
    return "\n\n".join(blocos)


def compilar_sdd(
    caminho: Path, raiz_projeto: Path | None = None, origens: dict[str, str] | None = None
) -> dict:
    """Devolve a entrada do contrato ou levanta SddInvalida com todos os problemas."""
    texto = caminho.read_text(encoding="utf-8")
    achado = FRONTMATTER_RE.match(texto)
    if not achado:
        raise SddInvalida(["sem front-matter"])
    try:
        frente = yaml.safe_load(achado.group(1)) or {}
    except yaml.YAMLError as exc:
        raise SddInvalida([f"front-matter inválido: {exc}"]) from exc
    corpo = texto[achado.end() :]

    problemas = []
    if frente.get("status") != "approved":
        problemas.append(f"status precisa ser approved, é {frente.get('status')!r}")
    criterios = _criterios(corpo, problemas)
    requisitos = _requisitos(corpo, problemas)
    arquivos = _arquivos_permitidos(corpo)
    molde = _molde(raiz_projeto, frente.get("molde"), problemas)
    if not arquivos:
        problemas.append("sem lista de arquivos: o gate de escopo não teria como conferir")
    especificacao = secao(corpo, "Especificação técnica consolidada") or ""
    if _enxuta(frente, corpo):
        especificacao = _resolver_referencia(frente, corpo, requisitos, origens or {}, problemas)
    if problemas:
        raise SddInvalida(problemas)

    return {
        "sdd_id": frente.get("id"),
        "titulo": frente.get("title"),
        "sizing": frente.get("sizing"),
        "source_docs": frente.get("source_docs") or [],
        "resumo": secao(corpo, "Resumo executivo") or "",
        "requisitos": requisitos,
        "criterios": criterios,
        "arquivos_permitidos": arquivos,
        "especificacao": especificacao,
        "instrucoes": secao(corpo, "Instruções específicas") or "",
        "tarefas": _tarefas(corpo),
        **({"molde": molde} if molde else {}),
    }
