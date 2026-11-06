"""Risco e modelo por regras em código. O sizing vem do documento; o risco é calculado."""

import re
import unicodedata

from fabrica.gates import CAMINHOS_PROTEGIDOS

# Procurado em texto sem acento e em minúsculas. Sinal só sobe o risco, então um falso alarme custa
# revisão a mais, e texto da SDD nunca consegue baixar o risco por aqui.
SINAIS_DE_ALTO_RISCO = re.compile(
    r"migra|schema\.prisma"
    r"|auth|autentic|autoriz|permiss|login|senha|token|segredo|credencia|sessao|perfil"
    r"|deploy|producao"
    r"|lgpd|dados? pessoa|cpf|cnpj|prontuario|paciente|titular"
    r"|pagamento|\bpagar|cobranc|estorno|reembolso|fatura|financeir|juros|comissao|cartao|boleto|\bpix\b"
)
MODELO_POR_RISCO = {
    "baixo": "claude-sonnet-5-5",
    "medio": "claude-sonnet-5-5",
    "alto": "claude-opus-5-5",
}
ORDEM_DE_RISCO = {"baixo": 0, "medio": 1, "alto": 2}
PISO_POR_SIZING = {"small": "baixo", "medium": "medio"}


def _normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _texto_da_entrada(entrada: dict) -> str:
    requisitos = [
        parte
        for requisito in entrada.get("requisitos") or []
        for parte in (requisito.get("requisito") or "", requisito.get("aceite") or "")
    ]
    return " ".join(
        [
            entrada.get("titulo") or "",
            entrada.get("resumo") or "",
            *requisitos,
            *(entrada.get("arquivos_permitidos") or []),
        ]
    )


def calcular_risco(entrada: dict) -> str | None:
    """Risco alto por regra, ou None quando a camada de decisão precisa entrar.

    Só o risco alto é decidido aqui. Nenhuma lista de palavras prova que uma tarefa é segura.
    """
    arquivos = entrada.get("arquivos_permitidos") or []
    if any(a.startswith(CAMINHOS_PROTEGIDOS) for a in arquivos):
        return "alto"
    if SINAIS_DE_ALTO_RISCO.search(_normalizar(_texto_da_entrada(entrada))):
        return "alto"
    if entrada.get("sizing") in {"large", "complex"}:
        return "alto"
    return None


def piso_de_risco(entrada: dict) -> str:
    """Menor risco aceito para o sizing declarado: o decisor pode subir, nunca descer."""
    return PISO_POR_SIZING.get(entrada.get("sizing"), "baixo")
