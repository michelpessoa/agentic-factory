"""Número da release a partir das mensagens de commit (Conventional Commits)."""

import re

VERSAO_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
ASSUNTO_RE = re.compile(r"^(?P<tipo>[a-z]+)(?:\([^)]*\))?(?P<quebra>!)?: ")


def proxima_versao(atual: str | None, assuntos_e_corpos: list[str]) -> str:
    """Sem tag anterior, parte de 0.0.0. Só commits convencionais contam."""
    achado = VERSAO_RE.match(atual or "0.0.0")
    if not achado:
        raise ValueError(f"versão inválida: {atual}")
    maior, menor, correcao = (int(g) for g in achado.groups())
    subir = None
    for mensagem in assuntos_e_corpos:
        assunto = ASSUNTO_RE.match(mensagem)
        if not assunto:
            continue
        if assunto["quebra"] or "BREAKING CHANGE:" in mensagem:
            subir = "maior"
            break
        if assunto["tipo"] == "feat":
            subir = "menor"
        elif subir is None:
            subir = "correcao"
    if subir == "maior":
        return f"{maior + 1}.0.0"
    if subir == "menor":
        return f"{maior}.{menor + 1}.0"
    return f"{maior}.{menor}.{correcao + 1}"
