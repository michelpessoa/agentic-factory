"""Camada de decisão atrás de uma interface trocável.

Regras em código primeiro. O que não couber em regra vai para um decisor, e confiança abaixo do
limiar vai para o humano, sem seguir sozinha. Contas não passam por aqui.
"""

from dataclasses import dataclass, replace
from typing import Protocol

from fabrica.roteamento import ORDEM_DE_RISCO, calcular_risco, piso_de_risco

LIMIAR_DE_CONFIANCA = 0.8


@dataclass(frozen=True)
class Decisao:
    risco: str
    confianca: float
    justificativa: str
    origem: str

    @property
    def segura(self) -> bool:
        return self.confianca >= LIMIAR_DE_CONFIANCA


class Decisor(Protocol):
    """Implementação trocável. A comparação da Fase 3 manteve a do MVP: ver ADR-0008."""

    def classificar_risco(self, entrada: dict) -> Decisao: ...


def decidir_risco(entrada: dict, decisor: Decisor) -> Decisao:
    risco = calcular_risco(entrada)
    if risco is not None:
        return Decisao(risco, 1.0, "regra em código", "regras")
    decisao = decisor.classificar_risco(entrada)
    piso = piso_de_risco(entrada)
    if ORDEM_DE_RISCO[decisao.risco] < ORDEM_DE_RISCO[piso]:
        return replace(decisao, risco=piso)
    return decisao
