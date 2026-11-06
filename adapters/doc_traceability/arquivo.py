"""SDD efêmera: depois da entrega, a SDD sai do caminho dos agentes e fica uma linha no registry.

Nada se apaga. `validate`, `trace` e `audit` do framework continuam funcionando, porque a entrada
do registry fica, com `path` novo e o campo `entrega`.
"""

import re
from pathlib import Path

DIR_ARQUIVO = "docs/sdd/arquivo"


def arquivar_sdd(repo: Path, caminho_sdd: str, pr: int, data: str) -> bool:
    """Devolve False se a SDD já foi arquivada."""
    origem = repo / caminho_sdd
    if not origem.is_file():
        return False
    sdd_id = origem.stem
    pasta = origem.parent
    destino = repo / DIR_ARQUIVO
    destino.mkdir(parents=True, exist_ok=True)
    origem.rename(destino / origem.name)
    validacao = pasta / f"validation-{sdd_id}.md"
    if validacao.is_file():
        validacao.rename(destino / validacao.name)

    registro = pasta / "registry.yaml"
    texto = registro.read_text(encoding="utf-8")
    padrao = re.compile(rf'^(?P<recuo>\s*)path: "?{re.escape(caminho_sdd)}"?[ \t]*$', re.MULTILINE)
    novo = lambda m: (
        f'{m["recuo"]}path: "{DIR_ARQUIVO}/{origem.name}"\n'
        f'{m["recuo"]}entrega: {{pr: {pr}, data: "{data}", resultado: aprovado}}'
    )
    texto, trocas = padrao.subn(novo, texto, count=1)
    if trocas != 1:
        raise ValueError(f"{sdd_id} não encontrada em {registro}")
    registro.write_text(texto, encoding="utf-8")
    return True
